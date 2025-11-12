#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Descarga ERA5 (single levels hourly) y genera CSV limpios y uniformes.
- Variables: ssrd (radiación acumulada), t2m (temperatura instantánea), tcc (nubosidad instantánea)
- Horas: 06, 09, 12, 15, 18, 21 (UTC)
- Corrige duplicados de valid_time, unidades y huecos horarios
- Rellena horas faltantes con ssrd=0 y mantiene consistencia temporal
"""

import time
import math
import argparse
from pathlib import Path
from typing import List, Dict

import cdsapi
import numpy as np
import pandas as pd
import xarray as xr


# ------------------ Conversión km ↔ grados ------------------
def km_to_deg_lat(km: float) -> float:
    return km / 111.32


def km_to_deg_lon(km: float, lat_deg: float) -> float:
    return km / (111.32 * math.cos(math.radians(lat_deg)))


# ------------------ Crear malla de tiles ------------------
def build_tiles_around(center_lat: float, center_lon: float,
                       radius_km: float, tile_km: float) -> List[Dict]:
    deg_lat_tile = km_to_deg_lat(tile_km)
    deg_lon_tile = km_to_deg_lon(tile_km, center_lat)

    dlat = km_to_deg_lat(radius_km)
    dlon = km_to_deg_lon(radius_km, center_lat)

    lat_min = center_lat - dlat
    lat_max = center_lat + dlat
    lon_min = center_lon - dlon
    lon_max = center_lon + dlon

    lats = np.arange(lat_min, lat_max, deg_lat_tile)
    lons = np.arange(lon_min, lon_max, deg_lon_tile)

    tiles = []
    for i, lat_c in enumerate(lats):
        for j, lon_c in enumerate(lons):
            north = lat_c + deg_lat_tile / 2
            south = lat_c - deg_lat_tile / 2
            west = lon_c - deg_lon_tile / 2
            east = lon_c + deg_lon_tile / 2
            tiles.append({
                "id": f"tile_{i:02d}_{j:02d}",
                "bbox": [float(north), float(west), float(south), float(east)],
                "center": (float(lat_c), float(lon_c))
            })
    return tiles


# ------------------ Apertura GRIB segura ------------------
def _open_grib_param(path: Path, shortname: str) -> xr.Dataset:
    """Abre un parámetro GRIB evitando duplicados de valid_time."""
    ds = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"shortName": shortname}},
    )
    # Si valid_time está duplicado (como coord y variable), eliminar la variable
    if "valid_time" in ds.variables and "valid_time" in ds.coords:
        ds = ds.drop_vars("valid_time")
    return ds


# ------------------ Conversión de cada archivo ------------------
def convert_to_csv(nc_path: Path):
    """
    Convierte un archivo ERA5 (GRIB/NetCDF) a CSV limpio y uniforme.
    - Calcula radiación del intervalo (kWh/m²)
    - Convierte temperatura a °C y nubosidad a 0–1
    - Incluye todas las horas 06,09,12,15,18,21 por día (rellenando con 0 si faltan)
    """
    try:
        # --- Detectar formato ---
        try:
            ds_nc = xr.open_dataset(nc_path, engine="netcdf4")
            is_grib = False
        except Exception:
            is_grib = True

        if is_grib:
            # --- Cargar datasets ---
            ds_ssrd = _open_grib_param(nc_path, "ssrd")
            ds_t2m = _open_grib_param(nc_path, "2t")
            ds_tcc = _open_grib_param(nc_path, "tcc")

            # --- SSRD: calcular diferencia por step dentro de cada time ---
            df_s = ds_ssrd[["ssrd"]].to_dataframe().reset_index()
            if "valid_time" not in df_s.columns:
                df_s["valid_time"] = pd.to_datetime(df_s["time"]) + pd.to_timedelta(df_s["step"])
            df_s = df_s.sort_values(["latitude", "longitude", "time", "step"])
            df_s["ssrd_Jm2"] = (
                df_s.groupby(["latitude", "longitude", "time"])["ssrd"]
                .diff()
                .clip(lower=0)
            )
            df_s = df_s.dropna(subset=["ssrd_Jm2"])[["valid_time", "latitude", "longitude", "ssrd_Jm2"]]

            # --- T2M / TCC ---
            df_t2m = ds_t2m[["t2m"]].to_dataframe().reset_index()
            if "valid_time" not in df_t2m.columns:
                df_t2m = df_t2m.rename(columns={"time": "valid_time"})

            df_tcc = ds_tcc[["tcc"]].to_dataframe().reset_index()
            if "valid_time" not in df_tcc.columns:
                df_tcc = df_tcc.rename(columns={"time": "valid_time"})

            # --- Unión alineada ---
            df = df_s.merge(df_t2m, on=["latitude", "longitude", "valid_time"], how="inner") \
                     .merge(df_tcc, on=["latitude", "longitude", "valid_time"], how="inner")

        else:
            # --- NETCDF ---
            ds = ds_nc
            if "valid_time" in ds.variables and "valid_time" in ds.coords:
                ds = ds.drop_vars("valid_time")

            df = ds[["ssrd", "t2m", "tcc"]].to_dataframe().reset_index()
            if "valid_time" not in df.columns:
                df = df.rename(columns={"time": "valid_time"})
            df = df.sort_values(["latitude", "longitude", "valid_time"])
            df["ssrd_Jm2"] = df.groupby(["latitude", "longitude"])["ssrd"].diff().clip(lower=0)
            df = df.dropna(subset=["ssrd_Jm2"])

        # --- Unidades ---
        df["ssrd_kWhm2"] = df["ssrd_Jm2"] / 3_600_000.0
        if "t2m" in df.columns:
            df["t2m_C"] = df["t2m"] - 273.15
        if "tcc" in df.columns and df["tcc"].max() > 1:
            df["tcc"] = df["tcc"] / 100.0

        # --- Filtrar y reindexar horas ---
        df["valid_time"] = pd.to_datetime(df["valid_time"])
        valid_hours = [6, 9, 12, 15, 18, 21]
        df = df[df["valid_time"].dt.hour.isin(valid_hours)]

        # Crear rango completo de horas (06→21 cada 3h)
        full_times = (
            pd.date_range(df["valid_time"].min().floor("D"),
                          df["valid_time"].max().ceil("D"),
                          freq="3H")
            .to_frame(index=False, name="valid_time")
        )
        full_times = full_times[full_times["valid_time"].dt.hour.isin(valid_hours)]
        df = pd.merge(full_times, df, on="valid_time", how="left")

        # Rellenar huecos con 0 o forward-fill
        df["ssrd_kWhm2"] = df["ssrd_kWhm2"].fillna(0)
        if "t2m_C" in df.columns:
            df["t2m_C"] = df["t2m_C"].fillna(method="ffill")
        if "tcc" in df.columns:
            df["tcc"] = df["tcc"].fillna(method="ffill")

        # --- Limpiar columnas ---
        for c in ["ssrd", "ssrd_Jm2", "t2m", "step", "number", "surface", "time"]:
            if c in df.columns:
                df.drop(columns=c, inplace=True, errors="ignore")

        # --- Añadir tile_id ---
        tile_id = nc_path.parts[-3]
        df["tile_id"] = tile_id
        df = df[["valid_time", "latitude", "longitude", "ssrd_kWhm2", "t2m_C", "tcc", "tile_id"]]
        df = df.sort_values(["valid_time", "latitude", "longitude"]).reset_index(drop=True)

        # --- Guardar CSV ---
        out_dir = Path("data/csv") / tile_id / nc_path.parent.name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_csv = out_dir / (nc_path.stem + ".csv")
        df.to_csv(out_csv, index=False, float_format="%.5f")
        print(f"💾 CSV limpio generado: {out_csv}")

    except Exception as e:
        print(f"❌ Error al convertir {nc_path} a CSV: {e}")


# ------------------ Descarga robusta ------------------
def cds_retrieve_with_retry(client: cdsapi.Client, dataset: str, request: Dict,
                            target_path: Path, max_retries: int = 5, base_sleep: float = 10.0) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and target_path.stat().st_size > 0:
        print(f"📦 Ya existe {target_path.name}, no se descarga de nuevo.")
        convert_to_csv(target_path)
        return

    for attempt in range(1, max_retries + 1):
        try:
            print(f"📥 [{attempt}/{max_retries}] Descargando => {target_path.name}")
            client.retrieve(dataset, request, str(target_path))
            print(f"✅ Descargado correctamente: {target_path}")
            break
        except Exception as e:
            wait = base_sleep * (2 ** (attempt - 1))
            print(f"⚠️  Error: {e}\n   Reintentando en {int(wait)}s...")
            time.sleep(wait)
    else:
        print(f"❌ Fallo tras {max_retries} intentos: {target_path}")
        return

    convert_to_csv(target_path)


# ------------------ Payload ERA5 ------------------
def make_request_payload(year: int, month: int,
                         variables: List[str], bbox: List[float]) -> Dict:
    days = [f"{d:02d}" for d in range(1, 32)]
    hours = [f"{h:02d}:00" for h in range(6, 22, 3)]
    return {
        "product_type": "reanalysis",
        "format": "grib",
        "variable": variables,
        "year": str(year),
        "month": f"{month:02d}",
        "day": days,
        "time": hours,
        "area": bbox,  # [N, W, S, E]
    }


# ------------------ Main CLI ------------------
def main():
    parser = argparse.ArgumentParser(description="Descarga ERA5 y genera CSV limpios y alineados.")
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
    print(f"🗺️ Tiles generados: {len(tiles)} (8x8 km cada uno)")
    print("⏰ Horas seleccionadas: 06, 09, 12, 15, 18, 21 (UTC)")

    c = cdsapi.Client()

    for year in range(args.start_year, args.end_year + 1):
        for month in range(1, 13):
            for tile in tiles:
                out_dir  = args.outdir / tile["id"] / f"{year}"
                out_path = out_dir / f"{year}_{month:02d}.nc"
                req = make_request_payload(year, month, variables, tile["bbox"])
                cds_retrieve_with_retry(c, args.dataset, req, out_path, args.max_retries)

    print("🎉 Descarga y conversión completadas correctamente.")


if __name__ == "__main__":
    main()
