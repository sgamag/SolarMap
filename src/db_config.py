# src/db_setup.py
from pathlib import Path
import math
from dataclasses import dataclass, asdict
from typing import List
from sqlalchemy import create_engine, text

CENTER_LAT = 40.415
CENTER_LON = -3.684
RADIUS_KM  = 24.0
TILE_KM    = 8.0
DB_PATH    = Path("BaseDeDatos/era5_madrid.db")

def km_to_deg_lat(km): return km / 111.32
def km_to_deg_lon(km, lat): return km / (111.32 * math.cos(math.radians(lat)))

@dataclass
class Tile:
    tile_id: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    lat_center: float
    lon_center: float

def build_tiles(lat0, lon0, radius_km, tile_km):
    dlat = km_to_deg_lat(radius_km)
    dlon = km_to_deg_lon(radius_km, lat0)
    lat_min, lat_max = lat0 - dlat, lat0 + dlat
    lon_min, lon_max = lon0 - dlon, lon0 + dlon

    step_lat = km_to_deg_lat(tile_km)
    step_lon = km_to_deg_lon(tile_km, lat0)

    tiles = []
    lat = lat_min + step_lat/2
    i = 0
    while lat < lat_max:
        lon = lon_min + step_lon/2
        j = 0
        while lon < lon_max:
            tiles.append(Tile(
                tile_id=f"tile_{i:02d}_{j:02d}",
                lat_min=round(lat-step_lat/2,6),
                lat_max=round(lat+step_lat/2,6),
                lon_min=round(lon-step_lon/2,6),
                lon_max=round(lon+step_lon/2,6),
                lat_center=round(lat,6),
                lon_center=round(lon,6)
            ))
            lon += step_lon
            j += 1
        lat += step_lat
        i += 1
    return tiles

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

    DDL = """
    PRAGMA journal_mode=WAL;
    PRAGMA foreign_keys=ON;

    CREATE TABLE IF NOT EXISTS zonas (
        id TEXT PRIMARY KEY,
        lat_min REAL NOT NULL,
        lat_max REAL NOT NULL,
        lon_min REAL NOT NULL,
        lon_max REAL NOT NULL,
        lat_center REAL NOT NULL,
        lon_center REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS era5_data (
        zona_id TEXT NOT NULL,
        valid_time TEXT NOT NULL,
        ssrd_kWhm2 REAL,
        t2m_C REAL,
        tcc REAL,
        potencial_0_100 REAL,
        PRIMARY KEY (zona_id, valid_time),
        FOREIGN KEY (zona_id) REFERENCES zonas(id)
    );

    CREATE INDEX IF NOT EXISTS idx_time ON era5_data(valid_time);
    """

    with engine.begin() as con:
        for stmt in DDL.split(";"):
            if stmt.strip():
                con.execute(text(stmt))

    with engine.begin() as con:
        n = con.execute(text("SELECT COUNT(*) FROM zonas")).scalar_one()
        if n == 0:
            tiles = build_tiles(CENTER_LAT, CENTER_LON, RADIUS_KM, TILE_KM)
            insert_sql = text("""
                INSERT INTO zonas (id, lat_min, lat_max, lon_min, lon_max, lat_center, lon_center)
                VALUES (:tile_id, :lat_min, :lat_max, :lon_min, :lon_max, :lat_center, :lon_center)
            """)
            con.execute(insert_sql, [asdict(t) for t in tiles])
            print(f"Insertadas {len(tiles)} zonas.")

    print("Base creada en:", DB_PATH.resolve())

if __name__ == "__main__":
    main()
