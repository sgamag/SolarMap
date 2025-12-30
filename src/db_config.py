# ============================================================
# CONFIGURACIÓN Y CREACIÓN DE LA BASE DE DATOS MYSQL
#
# Este script crea:
# - Tabla 'zonas'        → definición espacial de cada tile
# - Tabla 'era5_data'    → datos climáticos horarios por zona
# - Tabla 'potencial_tile_resumen'
#       → resumen climático por tile (media)
#
# NOTA:
# - El esquema se inicializa UNA sola vez.
# - Los datos se cargan posteriormente desde el pipeline en Python.
# - El potencial real NO se almacena en la BD (se calcula al vuelo).
# ============================================================

import math
from dataclasses import dataclass, asdict
from typing import List
from sqlalchemy import create_engine, text

# ------------------------------------------------------------
# PARÁMETROS ESPACIALES DEL PROYECTO
# ------------------------------------------------------------

CENTER_LAT = 40.415
CENTER_LON = -3.684
RADIUS_KM  = 24.0
TILE_KM    = 8.0

# ------------------------------------------------------------
# CONFIGURACIÓN DE CONEXIÓN A MYSQL
# ------------------------------------------------------------
# Base de datos MySQL local que actúa como servidor central
# para todo el grupo.

DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "era5_madrid"
DB_USER = "era5_user"
DB_PASS = "SolarMap67"   

SQLALCHEMY_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ------------------------------------------------------------
# UTILIDADES GEOGRÁFICAS
# ------------------------------------------------------------

def km_to_deg_lat(km: float) -> float:
    """Convierte kilómetros a grados de latitud."""
    return km / 111.32

def km_to_deg_lon(km: float, lat: float) -> float:
    """Convierte kilómetros a grados de longitud (depende de latitud)."""
    return km / (111.32 * math.cos(math.radians(lat)))

# ------------------------------------------------------------
# DEFINICIÓN DE UN TILE
# ------------------------------------------------------------

@dataclass
class Tile:
    tile_id: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    lat_center: float
    lon_center: float

# ------------------------------------------------------------
# CONSTRUCCIÓN DE LOS TILES
# ------------------------------------------------------------

def build_tiles(lat0: float, lon0: float,
                radius_km: float, tile_km: float) -> List[Tile]:
    """
    Genera la cuadrícula de tiles alrededor de un centro geográfico.
    Cada tile representa una celda fija del área de estudio.
    """

    dlat = km_to_deg_lat(radius_km)
    dlon = km_to_deg_lon(radius_km, lat0)

    lat_min, lat_max = lat0 - dlat, lat0 + dlat
    lon_min, lon_max = lon0 - dlon, lon0 + dlon

    step_lat = km_to_deg_lat(tile_km)
    step_lon = km_to_deg_lon(tile_km, lat0)

    tiles = []
    lat = lat_min + step_lat / 2
    i = 0

    while lat < lat_max:
        lon = lon_min + step_lon / 2
        j = 0

        while lon < lon_max:
            tiles.append(
                Tile(
                    tile_id=f"tile_{i:02d}_{j:02d}",
                    lat_min=round(lat - step_lat / 2, 6),
                    lat_max=round(lat + step_lat / 2, 6),
                    lon_min=round(lon - step_lon / 2, 6),
                    lon_max=round(lon + step_lon / 2, 6),
                    lat_center=round(lat, 6),
                    lon_center=round(lon, 6),
                )
            )
            lon += step_lon
            j += 1

        lat += step_lat
        i += 1

    return tiles

# ------------------------------------------------------------
# INICIALIZACIÓN DE LA BASE DE DATOS
# ------------------------------------------------------------

def main():
    """
    Inicializa el esquema de la base de datos MySQL:
    - crea las tablas si no existen
    - inserta los tiles en la tabla 'zonas' (solo si está vacía)
    """

    engine = create_engine(SQLALCHEMY_URL, future=True)

    # --------------------------------------------------------
    # DEFINICIÓN DEL ESQUEMA (DDL)
    # --------------------------------------------------------

    DDL = """
    CREATE TABLE IF NOT EXISTS zonas (
        id VARCHAR(32) PRIMARY KEY,
        lat_min DOUBLE NOT NULL,
        lat_max DOUBLE NOT NULL,
        lon_min DOUBLE NOT NULL,
        lon_max DOUBLE NOT NULL,
        lat_center DOUBLE NOT NULL,
        lon_center DOUBLE NOT NULL
    ) ENGINE=InnoDB;

    CREATE TABLE IF NOT EXISTS era5_data (
        zona_id VARCHAR(32) NOT NULL,
        valid_time DATETIME NOT NULL,
        ssrd_kWhm2 DOUBLE,
        t2m_C DOUBLE,
        tcc DOUBLE,
        potencial_climatico DOUBLE,
        PRIMARY KEY (zona_id, valid_time),
        CONSTRAINT fk_era5_zona
            FOREIGN KEY (zona_id) REFERENCES zonas(id)
    ) ENGINE=InnoDB;

    CREATE TABLE IF NOT EXISTS potencial_tile_resumen (
        zona_id VARCHAR(32) PRIMARY KEY,
        potencial_medio DOUBLE,
        n_registros BIGINT,
        last_updated DATETIME,
        CONSTRAINT fk_resumen_zona
            FOREIGN KEY (zona_id) REFERENCES zonas(id)
    ) ENGINE=InnoDB;
    """

    # Ejecutar el DDL
    with engine.begin() as con:
        for stmt in DDL.split(";"):
            if stmt.strip():
                con.execute(text(stmt))

    # --------------------------------------------------------
    # INSERCIÓN DE ZONAS (solo si la tabla está vacía)
    # --------------------------------------------------------

    with engine.begin() as con:
        n = con.execute(text("SELECT COUNT(*) FROM zonas")).scalar_one()

        if n == 0:
            tiles = build_tiles(CENTER_LAT, CENTER_LON, RADIUS_KM, TILE_KM)

            con.execute(
                text("""
                    INSERT INTO zonas (
                        id, lat_min, lat_max,
                        lon_min, lon_max,
                        lat_center, lon_center
                    )
                    VALUES (
                        :tile_id, :lat_min, :lat_max,
                        :lon_min, :lon_max,
                        :lat_center, :lon_center
                    )
                """),
                [asdict(t) for t in tiles],
            )

            print(f"Insertadas {len(tiles)} zonas.")

        else:
            print("La tabla 'zonas' ya contiene datos. No se reinserta.")

    print("Inicialización de la base de datos MySQL completada correctamente.")

# ------------------------------------------------------------
# EJECUCIÓN
# ------------------------------------------------------------

if __name__ == "__main__":
    main()
