# src/db_setup.py
from pathlib import Path
import math
from dataclasses import dataclass, asdict
from typing import List
from datetime import datetime
from sqlalchemy import create_engine, text

# ---------- Parámetros de tu zona (Madrid, Parque del Retiro) ----------
CENTER_LAT = 40.415
CENTER_LON = -3.684
RADIUS_KM  = 24.0     # radio del cuadrado a cubrir en km
TILE_KM    = 8.0      # tamaño del tile en km (8x8 km → 64 km2)
DB_PATH    = Path("data/era5_madrid.db")


# ---------- Utilidades geo ----------
def km_to_deg_lat(km: float) -> float:
    return km / 111.32  # ~ km por grado latitud

def km_to_deg_lon(km: float, lat_deg: float) -> float:
    return km / (111.32 * math.cos(math.radians(lat_deg)))  # km por grado longitud (depende de lat)


@dataclass
class Tile:
    tile_id: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    lat_center: float
    lon_center: float


def build_tiles(center_lat: float, center_lon: float, radius_km: float, tile_km: float) -> List[Tile]:
    dlat = km_to_deg_lat(radius_km)
    dlon = km_to_deg_lon(radius_km, center_lat)
    lat_min, lat_max = center_lat - dlat, center_lat + dlat
    lon_min, lon_max = center_lon - dlon, center_lon + dlon

    step_lat = km_to_deg_lat(tile_km)
    step_lon = km_to_deg_lon(tile_km, center_lat)

    tiles = []
    i = 0
    lat = lat_min + step_lat/2
    while lat < lat_max + 1e-9:
        j = 0
        lon = lon_min + step_lon/2
        while lon < lon_max + 1e-9:
            tile = Tile(
                tile_id=f"tile_{i:02d}_{j:02d}",
                lat_min=round(lat - step_lat/2, 6),
                lat_max=round(lat + step_lat/2, 6),
                lon_min=round(lon - step_lon/2, 6),
                lon_max=round(lon + step_lon/2, 6),
                lat_center=round(lat, 6),
                lon_center=round(lon, 6),
            )
            tiles.append(tile)
            j += 1
            lon += step_lon
        i += 1
        lat += step_lat
    return tiles


def main():
    # 1) Crear carpeta y DB
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

    # 2) Crear tablas (zonas + era5_data)
    DDL = """
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous = NORMAL;

    CREATE TABLE IF NOT EXISTS zonas (
      id           TEXT PRIMARY KEY,
      lat_min      REAL NOT NULL,
      lat_max      REAL NOT NULL,
      lon_min      REAL NOT NULL,
      lon_max      REAL NOT NULL,
      lat_center   REAL NOT NULL,
      lon_center   REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS era5_data (
      -- 1 fila por zona y hora válida
      zona_id      TEXT NOT NULL,
      valid_time   TEXT NOT NULL,      -- 'YYYY-MM-DD HH:MM:SS' (UTC)
      latitude     REAL,               -- opcional: guardamos centro del tile para referencia
      longitude    REAL,
      ssrd_kWhm2   REAL,               -- energía del intervalo (kWh/m²)
      t2m_C        REAL,               -- temperatura (°C)
      tcc          REAL,               -- nubosidad (0–1)
      PRIMARY KEY (zona_id, valid_time),
      FOREIGN KEY (zona_id) REFERENCES zonas(id)
    );

    CREATE INDEX IF NOT EXISTS idx_era5_time ON era5_data(valid_time);
    """
    with engine.begin() as con:
        for stmt in DDL.strip().split(";"):
            if stmt.strip():
                con.execute(text(stmt))

    # 3) Insertar las 36 zonas (si la tabla está vacía)
    with engine.begin() as con:
        n = con.execute(text("SELECT COUNT(*) FROM zonas")).scalar_one()
        if n == 0:
            tiles = build_tiles(CENTER_LAT, CENTER_LON, RADIUS_KM, TILE_KM)
            insert_sql = text("""
                INSERT INTO zonas (id, lat_min, lat_max, lon_min, lon_max, lat_center, lon_center)
                VALUES (:tile_id, :lat_min, :lat_max, :lon_min, :lon_max, :lat_center, :lon_center)
            """)
            con.execute(insert_sql, [asdict(t) for t in tiles])
            print(f"✔ Insertadas {len(tiles)} zonas (tiles).")
        else:
            print(f"ℹ️  La tabla 'zonas' ya tiene {n} registros. No se insertan de nuevo.")

    print(f"✔ Base creada en {DB_PATH.resolve()}")
    print("Estructura:")
    print(" - Tabla 'zonas' con 36 tiles de 8x8 km alrededor del Retiro")
    print(" - Tabla 'era5_data' (1 fila por zona y hora: 06,09,12,15,18,21)")

if __name__ == "__main__":
    main()
