# Script de creacion de dimensiones sinteticas

import csv
import math
import random
import uuid
from datetime import date, timedelta
from pathlib import Path
import numpy as np

# Configuracion base del generador
random.seed(24)
CARPETA_SALIDA = Path("data_ingesta/sinteticos/dimensiones")
CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
NUM_USUARIOS = 250
PORCENTAJE_ANONIMOS = 0.20

# Pesos estacionales para la adquisicion de usuarios 
PESOS_MESES = [0.3, 0.3, 0.7, 0.8, 0.9, 1.0, 0.9, 0.7, 0.5, 0.4, 0.3, 0.2]

def guardar_csv(nombre_tabla, filas, columnas):
    with open(CARPETA_SALIDA / f"{nombre_tabla}.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"Generado: {nombre_tabla}.csv ({len(filas)} filas)")

print("Iniciando generacion de dimensiones...")

# Dimension Zonas Geograficas
# Mapeo de la Comunidad de Madrid utilizando una cuadricula de tiles.
LAT0, LON0 = 40.415, -3.684
RADIO_KM, TILE_KM = 24.0, 8.0
def km_a_grados_lat(km): return km / 111.32
def km_a_grados_lon(km, lat): return km / (111.32 * math.cos(math.radians(lat)))

delta_lat = km_a_grados_lat(TILE_KM)
delta_lon = km_a_grados_lon(TILE_KM, LAT0)
lats = list(np.arange(LAT0 - km_a_grados_lat(RADIO_KM), LAT0 + km_a_grados_lat(RADIO_KM), delta_lat))[:6]
lons = list(np.arange(LON0 - km_a_grados_lon(RADIO_KM, LAT0), LON0 + km_a_grados_lon(RADIO_KM, LAT0), delta_lon))[:6]

MUNICIPIOS = {
    "tile_00_00": "Batres", "tile_00_01": "Humanes de Madrid", "tile_00_02": "Pinto",
    "tile_00_03": "San Martin de la Vega", "tile_00_04": "San Martin de la Vega", "tile_00_05": "Morata de Tajuna",
    "tile_01_00": "Mostoles", "tile_01_01": "Fuenlabrada", "tile_01_02": "Getafe",
    "tile_01_03": "Getafe", "tile_01_04": "Rivas-Vaciamadrid", "tile_01_05": "Arganda del Rey",
    "tile_02_00": "Villaviciosa de Odon", "tile_02_01": "Madrid", "tile_02_02": "Madrid",
    "tile_02_03": "Madrid", "tile_02_04": "Rivas-Vaciamadrid", "tile_02_05": "Loeches",
    "tile_03_00": "Majadahonda", "tile_03_01": "Pozuelo de Alarcon", "tile_03_02": "Madrid",
    "tile_03_03": "Madrid", "tile_03_04": "Madrid", "tile_03_05": "Torrejon de Ardoz",
    "tile_04_00": "Las Rozas de Madrid", "tile_04_01": "Madrid", "tile_04_02": "Madrid",
    "tile_04_03": "Alcobendas", "tile_04_04": "Paracuellos de Jarama", "tile_04_05": "Daganzo de Arriba",
    "tile_05_00": "La Berzosa", "tile_05_01": "Madrid", "tile_05_02": "Tres Cantos",
    "tile_05_03": "Madrid", "tile_05_04": "Algete", "tile_05_05": "Daganzo de Arriba"
}

filas_zona = []
for i, lat_c in enumerate(lats):
    for j, lon_c in enumerate(lons):
        id_z = f"tile_{i:02d}_{j:02d}"
        filas_zona.append({
            "id_zona": id_z, "municipio": MUNICIPIOS[id_z], "provincia": "Madrid",
            "comunidad_autonoma": "Comunidad de Madrid", "lat_center": round(lat_c, 6),
            "lon_center": round(lon_c, 6), "norte_lat_max": round(lat_c + delta_lat / 2, 6),
            "sur_lat_min": round(lat_c - delta_lat / 2, 6), "este_lon_max": round(lon_c + delta_lon / 2, 6),
            "oeste_lon_min": round(lon_c - delta_lon / 2, 6)
        })
guardar_csv("dim_zona", filas_zona, list(filas_zona[0].keys()))

# Dimension Fecha
# Generacion de calendario continuo para el periodo de analisis.
FESTIVOS_FIJOS = {(1, 1), (1, 6), (5, 1), (5, 2), (5, 15), (8, 15), (10, 12), (11, 1), (11, 9), (12, 6), (12, 8), (12, 25)}
FESTIVOS_VARIABLES = {date(2025, 4, 17), date(2025, 4, 18), date(2026, 4, 2), date(2026, 4, 3)}
filas_fecha = []
dia_actual = date(2024, 1, 1)

while dia_actual <= date(2030, 12, 31):
    mes, dia = dia_actual.month, dia_actual.day
    filas_fecha.append({
        "id_fecha": int(dia_actual.strftime("%Y%m%d")), "fecha_completa": dia_actual.isoformat(), "año": dia_actual.year,
        "trimestre": (mes - 1) // 3 + 1, "mes": mes, "nombre_mes": ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][mes],
        "dia": dia, "dia_semana": dia_actual.weekday() + 1, "nombre_dia": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][dia_actual.weekday()],
        "estacion": {1: "Invierno", 2: "Invierno", 3: "Primavera", 4: "Primavera", 5: "Primavera", 6: "Verano", 7: "Verano", 8: "Verano", 9: "Otoño", 10: "Otoño", 11: "Otoño", 12: "Invierno"}[mes],
        "es_fin_de_semana": 1 if dia_actual.weekday() >= 5 else 0, "es_festivo": 1 if (mes, dia) in FESTIVOS_FIJOS or dia_actual in FESTIVOS_VARIABLES else 0,
        "es_horario_verano": 1 if date(dia_actual.year, 3, 31) <= dia_actual < date(dia_actual.year, 10, 27) else 0
    })
    dia_actual += timedelta(days=1)
guardar_csv("dim_fecha", filas_fecha, list(filas_fecha[0].keys()))

# Dimension Hora
# Agrupacion en tramos horarios para simplificacion de dashboards.
filas_hora = [{"id_hora": h, "hora_formato_24h": f"{h:02d}:00", "tramo_horario": {**{h: "Madrugada" for h in range(0, 6)}, **{h: "Mañana" for h in range(6, 12)}, **{h: "Tarde" for h in range(12, 20)}, **{h: "Noche" for h in range(20, 24)}}[h]} for h in range(24)]
guardar_csv("dim_hora", filas_hora, list(filas_hora[0].keys()))

# Dimension Usuario y Tabla Transaccional de Credenciales
CPS_MADRID = [28460, 28970, 28320, 28540, 28510, 28935, 28940, 28901, 28521, 28500, 28670, 28001, 28002, 28020, 28220, 28223, 28850, 28230, 28100, 28860, 28760]
NOMBRES = ["Carlos", "Maria", "Javier", "Ana", "Luis", "Laura", "Sergio", "Elena", "Pablo", "Marta"]
APELLIDOS = ["Garcia", "Martinez", "Lopez", "Sanchez", "Gonzalez", "Perez", "Rodriguez", "Fernandez"]

filas_usuario, filas_credenciales = [], []
num_anonimos = int(NUM_USUARIOS * PORCENTAJE_ANONIMOS)

for i in range(NUM_USUARIOS):
    es_anonimo = i < num_anonimos
    id_usr = f"USR_{uuid.uuid4().hex[:12].upper()}"
    
    # Generacion de fecha de alta alineada con la estacionalidad del trafico
    mes_acceso = random.choices(range(1, 13), weights=PESOS_MESES)[0]
    año_acceso = 2025 if mes_acceso > 4 else random.choice([2025, 2026])
    dia_acceso = random.randint(1, 28)
    fecha_primer_acceso = date(año_acceso, mes_acceso, dia_acceso)
    
    if es_anonimo:
        filas_usuario.append({
            "id_usuario": id_usr, "fecha_nacimiento": "", "cp_usuario": "", 
            "grupo_usuario": "", "fecha_primer_acceso": fecha_primer_acceso.isoformat()
        })
    else:
        cp = random.choice(CPS_MADRID)
        if str(cp).startswith("280"):
            grupo = random.choices(["Joven", "Adulto", "Senior"], weights=[0.6, 0.3, 0.1])[0]
        else:
            grupo = random.choices(["Joven", "Adulto", "Senior"], weights=[0.2, 0.5, 0.3])[0]
        
        año_nac = random.randint(1991, 2005) if grupo == "Joven" else (random.randint(1971, 1990) if grupo == "Adulto" else random.randint(1950, 1970))
        
        filas_usuario.append({
            "id_usuario": id_usr, "fecha_nacimiento": date(año_nac, random.randint(1, 12), random.randint(1, 28)).isoformat(),
            "cp_usuario": cp, "grupo_usuario": grupo, "fecha_primer_acceso": fecha_primer_acceso.isoformat()
        })
        
        nombre, apellido = random.choice(NOMBRES), random.choice(APELLIDOS)
        filas_credenciales.append({
            "id_usuario": id_usr, "nombre": nombre, "apellidos": apellido,
            "email": f"{nombre.lower()}.{apellido.lower()}{random.randint(10,999)}@solarmap.demo",
            "password_hash": "hash_simulado_bcrypt_12345"
        })

guardar_csv("dim_usuario", filas_usuario, ["id_usuario", "fecha_nacimiento", "cp_usuario", "grupo_usuario", "fecha_primer_acceso"])
guardar_csv("app_credenciales_usuario", filas_credenciales, ["id_usuario", "nombre", "apellidos", "email", "password_hash"])

# Dimension Tipo de Evento
EVENTOS = [
    ("EVT_ACCESO_WEB", None, "inicio", "Acceso inicio", 0), 
    ("EVT_LOGIN", "inicio", "inicio", "Login", 1), 
    ("EVT_REGISTRO", "inicio", "inicio", "Registro", 1), 
    ("EVT_ABRIR_MAPA", "inicio", "mapa", "Apertura mapa", 0), 
    ("EVT_BUSCAR_DIR", "mapa", "mapa", "Búsqueda dirección", 0), 
    ("EVT_CAPTURAR_ZONA", "mapa", "mapa", "Captura zona", 1), 
    ("EVT_SELEC_TEJADO", "mapa", "detalle", "Selección tejado", 1), 
    ("EVT_VER_POTENCIAL", "detalle", "detalle", "Ver potencial", 0), 
    ("EVT_ABRIR_SIM", "detalle", "simulador", "Abrir simulador", 0), 
    ("EVT_CALCULAR_ROI", "simulador", "resultado", "Calcular ROI", 1), 
    ("EVT_DESCARGAR_INF", "resultado", "resultado", "Descarga PDF", 1), 
    ("EVT_CONTACTO_PROV", "resultado", "proveedor", "Contacto instalador", 1)
]
guardar_csv("dim_tipo_evento", [{"id_tipo_evento": e[0], "pantalla_origen": e[1], "pantalla_actual": e[2], "nombre_evento": e[3], "es_hito_importante": e[4]} for e in EVENTOS], ["id_tipo_evento", "pantalla_origen", "pantalla_actual", "nombre_evento", "es_hito_importante"])

# Dimensiones Adicionales
guardar_csv("dim_caracteristicas_tejado", [{"id_caracteristica": i + 1, "tamaño_categoria": tam, "orientacion_principal": ori} for i, (tam, ori) in enumerate([(t, o) for t in ["Pequeño", "Mediano", "Grande"] for o in ["Sur", "Sureste", "Suroeste", "Este", "Oeste", "Norte"]])], ["id_caracteristica", "tamaño_categoria", "orientacion_principal"])
guardar_csv("dim_escenario_economico", [{"id_escenario": 1, "nombre_escenario": "pesimista", "banda_prediccion": "Inferior", "descripcion_tendencia": "Proyeccion basada en alta volatilidad y subida constante de precios."}, {"id_escenario": 2, "nombre_escenario": "plano", "banda_prediccion": "Media", "descripcion_tendencia": "Proyeccion estandar asumiendo crecimiento sostenido e inflacion estable."}, {"id_escenario": 3, "nombre_escenario": "verde", "banda_prediccion": "Superior", "descripcion_tendencia": "Proyeccion favorable con estabilizacion a la baja del mercado."}], ["id_escenario", "nombre_escenario", "banda_prediccion", "descripcion_tendencia"])
guardar_csv("dim_panel", [{"id_panel": 1, "modelo_panel": "Panel Compacto 350W", "potencia_w": 350, "precio_unitario_euros": 110.0, "area_panel_m2": 1.62, "coste_instalacion_fijo_euros": 1500.0, "nombre_proveedor": "SolarMap Installer"}, {"id_panel": 2, "modelo_panel": "Panel Estandar 400W", "potencia_w": 400, "precio_unitario_euros": 150.0, "area_panel_m2": 1.72, "coste_instalacion_fijo_euros": 1700.0, "nombre_proveedor": "SolarMap Installer"}, {"id_panel": 3, "modelo_panel": "Panel Premium 450W", "potencia_w": 450, "precio_unitario_euros": 195.0, "area_panel_m2": 1.90, "coste_instalacion_fijo_euros": 1900.0, "nombre_proveedor": "SolarMap Installer"}, {"id_panel": 4, "modelo_panel": "Panel Alta Eficiencia 500W", "potencia_w": 500, "precio_unitario_euros": 260.0, "area_panel_m2": 2.10, "coste_instalacion_fijo_euros": 2200.0, "nombre_proveedor": "SolarMap Installer"}], ["id_panel", "modelo_panel", "potencia_w", "precio_unitario_euros", "area_panel_m2", "coste_instalacion_fijo_euros", "nombre_proveedor"])

print("Se ha creado con exito.")