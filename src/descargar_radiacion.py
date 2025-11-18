#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import math
import argparse
from pathlib import Path
from typing import List, Dict

import cdsapi
import numpy as np
import pandas as pd
import xarray as xr

# ------------------ utilidades geo ------------------
def km_to_deg_lat(km: float) -> float:
    return km / 111.32

def km_to_deg_lon(km: float, lat_deg: float) -> float:
    return km / (111.32 * math.cos(math.radians(lat_deg)))

def build_tiles_around(center_lat: float, center_lon: float,
                       radius_km: float, tile_km: float) -> List[Dict]:
    deg_lat_tile = km_to_deg_lat(tile_km)
    deg_lon_tile = km_to_deg_lon(tile_km, center_lat)
    dlat = km_to_deg_lat(radius_km)
    dlon = km_to_deg_lon(radius_km, center_lat)

    lat_min, lat_max = center_lat - dlat, center_lat + dlat
    lon_min, lon_max = center_lon - dlon, center_lon + dlon

    lats = np.arange(lat_min, lat_max, deg_lat_tile)
    lons = np.arange(lon_min, lon_max, deg_lon_tile)

    tiles = []
    for i, lat_c in enumerate(lats):
        for j, lon_c in enumerate(lons):
            north = lat_c + deg_lat_tile / 2
            south = lat_c - deg_lat_tile / 2
            west  = lon_c - deg_lon_tile / 2
            east  = lon_c + deg_lon_tile / 2
            tiles.append({
                "id": f"tile_{i:02d}_{j:02d}",
                "bbox": [float(north), float(west), float(south), float(east)],
                "center": (float(lat_c), float(lon_c)),
            })
    return tiles

# ------------------ lectura GRIB ------------------
def _open_grib_param(path: Path, shortname: str) -> xr.Dataset:
    # indexpath="" para no dejar .idx; filter_by_keys por shortName
    return xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"shortName": shortname}, "indexpath": ""},
    )

# ------------------ conversión a CSV ------------------
def convert_to_csv(nc_path: Path) -> None:
    try:
        if not nc_path.exists() or nc_path.stat().st_size == 0:
            print(f"Archivo no encontrado o vacío: {nc_path}")
            return

        # Cargar variables
        ds_ssrd = _open_grib_param(nc_path, "ssrd")
        ds_t2m  = _open_grib_param(nc_path, "2t")
        ds_tcc  = _open_grib_param(nc_path, "tcc")

        # Radiación: usar valor directo acumulado del último intervalo
        df_s = ds_ssrd[["ssrd"]].to_dataframe().reset_index()
        if "valid_time" not in df_s.columns:
            df_s["valid_time"] = pd.to_datetime(df_s["time"]) + pd.to_timedelta(df_s["step"])
        df_s = df_s.sort_values(["latitude", "longitude", "valid_time"])
        df_s["ssrd_kWhm2"] = pd.to_numeric(df_s["ssrd"], errors="coerce") / 3_600_000.0
        df_s = df_s[["valid_time", "latitude", "longitude", "ssrd_kWhm2"]]

        # Temperatura
        df_t = ds_t2m[["t2m"]].to_dataframe().reset_index()
        if "valid_time" not in df_t.columns:
            df_t = df_t.rename(columns={"time": "valid_time"})
        df_t["t2m_C"] = pd.to_numeric(df_t["t2m"], errors="coerce") - 273.15
        # Regla: si t2m_C > 50, dividir por 10000 y redondear a 2 decimales
        mask = df_t["t2m_C"] > 50
        df_t.loc[mask, "t2m_C"] = (df_t.loc[mask, "t2m_C"] / 10_000).round(2)
        df_t["t2m_C"] = df_t["t2m_C"].round(2)
        df_t = df_t[["valid_time", "latitude", "longitude", "t2m_C"]]

        # Nubosidad
        df_c = ds_tcc[["tcc"]].to_dataframe().reset_index()
        if "valid_time" not in df_c.columns:
            df_c = df_c.rename(columns={"time": "valid_time"})
        df_c["tcc"] = pd.to_numeric(df_c["tcc"], errors="coerce")
        if df_c["tcc"].max() > 1:
            df_c["tcc"] = df_c["tcc"] / 100.0
        df_c = df_c[["valid_time", "latitude", "longitude", "tcc"]]

        # Unión por lat/lon/valid_time
        df = df_s.merge(df_t, on=["latitude", "longitude", "valid_time"], how="inner") \
                 .merge(df_c, on=["latitude", "longitude", "valid_time"], how="inner")

        # Solo horas 12, 15, 18
        df["valid_time"] = pd.to_datetime(df["valid_time"])
        df = df[df["valid_time"].dt.hour.isin([12, 15, 18])]

        # Redondeos y orden
        df["latitude"]  = df["latitude"].round(4)
        df["longitude"] = df["longitude"].round(4)
        df["ssrd_kWhm2"] = df["ssrd_kWhm2"].round(3)
        df = df.sort_values(["valid_time", "latitude", "longitude"]).reset_index(drop=True)

        # Añadir tile_id y exportar CSV (coma, 2 decimales)
        tile_id = nc_path.parts[-3]
        df["tile_id"] = tile_id
        out_dir = Path("data/csv") / tile_id / nc_path.parent.name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_csv = out_dir / (nc_path.stem + ".csv")
        df[["valid_time", "latitude", "longitude", "ssrd_kWhm2", "t2m_C", "tcc", "tile_id"]] \
            .to_csv(out_csv, index=False, float_format="%.2f")
        print(f"CSV generado: {out_csv}")

    except Exception as e:
        print(f"Error al convertir {nc_path}: {e}")

# ------------------ descarga con reintentos ------------------
def cds_retrieve_with_retry(client: cdsapi.Client, dataset: str, request: Dict,
                            target_path: Path, max_retries: int = 5, base_sleep: float = 10.0) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tile_id = target_path.parts[-3]
    out_csv = Path("data/csv") / tile_id / target_path.parent.name / (target_path.stem + ".csv")

    # si el CSV ya existe, omitir
    if out_csv.exists() and out_csv.stat().st_size > 0:
        print(f"{out_csv} ya existe, se omite")
        return

    # si el GRIB ya está, convertir directamente
    if target_path.exists() and target_path.stat().st_size > 0:
        convert_to_csv(target_path)
        return

    # descargar con reintentos
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[{attempt}/{max_retries}] descargando => {target_path}")
            client.retrieve(dataset, request, str(target_path))
            print(f"Descargado: {target_path}")
            break
        except Exception as e:
            wait = base_sleep * (2 ** (attempt - 1))
            print(f"Error: {e}  Reintentando en {int(wait)}s...")
            time.sleep(wait)
    else:
        print(f"Fallo tras {max_retries} intentos: {target_path}")
        return

    convert_to_csv(target_path)

# ------------------ payload ERA5 ------------------
def make_request_payload(year: int, month: int,
                         variables: List[str], bbox: List[float]) -> Dict:
    days = [f"{d:02d}" for d in range(1, 32)]
    hours = [f"{h:02d}:00" for h in range(12, 19, 3)]  # 12, 15, 18
    return {
        "product_type": "reanalysis",
        "format": "grib",
        "variable": variables,
        "year": str(year),
        "month": f"{month:02d}",
        "day": days,
        "time": hours,
        "area": bbox,
    }

# ------------------ main ------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year",   type=int, required=True)
    parser.add_argument("--radius-km",  type=float, default=24.0)
    parser.add_argument("--tile-km",    type=float, default=8.0)
    parser.add_argument("--outdir",     type=Path, default=Path("data/raw/era5"))
    parser.add_argument("--dataset",    default="reanalysis-era5-single-levels")
    parser.add_argument("--lat0",       type=float, default=40.415)
    parser.add_argument("--lon0",       type=float, default=-3.684)
    parser.add_argument("--max-retries",type=int, default=5)
    args = parser.parse_args()

    variables = [
        "surface_solar_radiation_downwards",
        "2m_temperature",
        "total_cloud_cover",
    ]

    tiles = build_tiles_around(args.lat0, args.lon0, args.radius_km, args.tile_km)
    print("Tiles generados:", len(tiles))
    print("Horas seleccionadas: 12, 15, 18")

    c = cdsapi.Client()

    for year in range(args.start_year, args.end_year + 1):
        for month in range(1, 13):
            for tile in tiles:
                out_dir = args.outdir / tile["id"] / f"{year}"
                out_path = out_dir / f"{year}_{month:02d}.nc"  # extensión .nc, pero contiene GRIB (tu convención)
                req = make_request_payload(year, month, variables, tile["bbox"])
                cds_retrieve_with_retry(c, args.dataset, req, out_path, args.max_retries)

if __name__ == "__main__":
    main()
