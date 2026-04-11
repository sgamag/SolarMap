"""
Módulo de utilidades geográficas y generación de Tiles.
Este archivo contiene las matemáticas para crear la cuadrícula del proyecto solar.
"""

import math
import time
from dataclasses import dataclass
from typing import List

# Importamos la herramienta mágica para leer mapas
from geopy.geocoders import Nominatim

# ------------------------------------------------------------
# PARÁMETROS ESPACIALES DEL PROYECTO
# ------------------------------------------------------------
CENTER_LAT = 40.415
CENTER_LON = -3.684
RADIUS_KM  = 24.0
TILE_KM    = 8.0

# ------------------------------------------------------------
# UTILIDADES GEOGRÁFICAS Y MAPAS
# ------------------------------------------------------------
def km_to_deg_lat(km: float) -> float:
    return km / 111.32

def km_to_deg_lon(km: float, lat: float) -> float:
    return km / (111.32 * math.cos(math.radians(lat)))

def obtener_municipio_provincia(lat: float, lon: float, max_intentos=3) -> tuple:
    """
    Se conecta a OpenStreetMap para traducir coordenadas a municipio y provincia.
    Incluye un sistema de reintentos y un timeout ampliado para evitar caídas.
    """
    # AÑADIDO: timeout=10 le da al servidor hasta 10 segundos para responder sin dar error
    geolocator = Nominatim(user_agent="proyecto_solar_tfg_analitica", timeout=10)
    
    for intento in range(max_intentos):
        try:
            time.sleep(1.2) # Pausa obligatoria para no saturar la API
            
            location = geolocator.reverse((lat, lon), exactly_one=True, language='es')
            
            if location and 'address' in location.raw:
                address = location.raw['address']
                
                # Buscamos la etiqueta correcta según el tamaño de la población
                municipio = address.get('city', address.get('town', address.get('village', address.get('municipality', 'Desconocido'))))
                provincia = address.get('province', address.get('state', 'Desconocido'))
                
                return municipio, provincia
                
            return "Desconocido", "Desconocido"
            
        except Exception as e:
            print(f"    [Aviso] El servidor tardó en responder. Reintento {intento + 1} de {max_intentos}...")
            if intento == max_intentos - 1:
                print(f"    [Error definitivo] No se pudo obtener la zona ({lat}, {lon}): {e}")
                return "Desconocido", "Desconocido"
            time.sleep(2) # Si falla, esperamos 2 segundos antes de volver a molestar al servidor
            

# ------------------------------------------------------------
# DEFINICIÓN DE UN TILE
# ------------------------------------------------------------
@dataclass
class Tile:
    id_zona: str
    municipio: str
    provincia: str
    lat_center: float
    lon_center: float
    sur_lat_min: float
    norte_lat_max: float
    oeste_lon_min: float
    este_lon_max: float

# ------------------------------------------------------------
# CONSTRUCCIÓN DE LOS TILES
# ------------------------------------------------------------
def build_tiles(lat0: float, lon0: float,
                radius_km: float, tile_km: float) -> List[Tile]:
    
    dlat = km_to_deg_lat(radius_km)
    dlon = km_to_deg_lon(radius_km, lat0)

    lat_min, lat_max = lat0 - dlat, lat0 + dlat
    lon_min, lon_max = lon0 - dlon, lon0 + dlon

    step_lat = km_to_deg_lat(tile_km)
    step_lon = km_to_deg_lon(tile_km, lat0)

    tiles = []
    lat = lat_min + step_lat / 2
    i = 0

    # Aviso para que no pienses que el programa se ha colgado
    print(f"Calculando cuadrículas y consultando municipios (esto tardará unos segundos por la pausa de seguridad)...")

    while lat < lat_max:
        lon = lon_min + step_lon / 2
        j = 0

        while lon < lon_max:
            lat_center = round(lat, 6)
            lon_center = round(lon, 6)
            
            # ¡Llamamos a nuestra nueva función!
            municipio_real, provincia_real = obtener_municipio_provincia(lat_center, lon_center)
            
            print(f"  -> Tile {i:02d}_{j:02d} detectado en: {municipio_real} ({provincia_real})")

            tiles.append(
                Tile(
                    id_zona=f"tile_{i:02d}_{j:02d}",
                    municipio=municipio_real,
                    provincia=provincia_real,
                    lat_center=lat_center,
                    lon_center=lon_center,
                    sur_lat_min=round(lat - step_lat / 2, 6),
                    norte_lat_max=round(lat + step_lat / 2, 6),
                    oeste_lon_min=round(lon - step_lon / 2, 6),
                    este_lon_max=round(lon + step_lon / 2, 6)
                )
            )
            lon += step_lon
            j += 1
            
        lat += step_lat
        i += 1

    return tiles

# ------------------------------------------------------------
# FUNCIÓN PUENTE PARA LA BASE DE DATOS LORCA
# ------------------------------------------------------------
def obtener_datos_tiles():
    """
    Ejecuta la construcción de tiles y convierte los objetos 
    en diccionarios listos para que poblar_dimensiones.py los inserte en MySQL.
    """
    # 1. Calculamos los tiles usando las variables de arriba
    tiles_objetos = build_tiles(CENTER_LAT, CENTER_LON, RADIUS_KM, TILE_KM)
    
    # 2. Los transformamos al formato que le gusta a tu Script 2
    lista_diccionarios = []
    for t in tiles_objetos:
        lista_diccionarios.append({
            'id_zona': t.id_zona,
            'municipio': t.municipio,
            'provincia': t.provincia,
            'altitud': 667.0, # Altitud media de Madrid por defecto para que no falle Lorca
            'lat_center': t.lat_center,
            'lon_center': t.lon_center,
            'norte_lat_max': t.norte_lat_max,
            'sur_lat_min': t.sur_lat_min,
            'este_lon_max': t.este_lon_max,
            'oeste_lon_min': t.oeste_lon_min
        })
        
    return lista_diccionarios

# ------------------------------------------------------------
# PRUEBA RÁPIDA
# ------------------------------------------------------------
if __name__ == "__main__":
    mis_tiles = build_tiles(CENTER_LAT, CENTER_LON, RADIUS_KM, TILE_KM)
    print("\n¡Proceso terminado!")
    print(f"Ejemplo del primer Tile: {mis_tiles[0]}")