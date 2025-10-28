# ======================================================
# ☀ COPERNICUS ERA5 - Descarga y conversión GRIB → CSV (versión final)
# ======================================================

import cdsapi
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime

def descargar_radiacion(lat=40.4, lon=-3.7):
    """
    Descarga datos de radiación solar (ssrd), nubosidad (tcc)
    y temperatura (2t/t2m) desde Copernicus ERA5, los combina y guarda CSV.
    """

    print("🔄 Conectando al Climate Data Store (ERA5)...")

    # Cliente Copernicus autenticado
    c = cdsapi.Client(
        url="https://cds.climate.copernicus.eu/api",
        key="a78d8196-d488-49c5-8c73-615d85f31c61"
    )

    # ======================================================
    # 📡 Descarga del archivo GRIB
    # ======================================================
    c.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": "reanalysis",
            "variable": [
                "surface_solar_radiation_downwards",  # ☀ radiación solar
                "total_cloud_cover",                  # ☁ nubosidad
                "2m_temperature",                     # 🌡 temperatura
            ],
            "year": ["2024"],
            "month": ["10"],
            "day": [f"{i:02d}" for i in range(1, 11)],
            "time": [f"{h:02d}:00" for h in range(0, 24)],
            "area": [lat + 0.5, lon - 0.5, lat - 0.5, lon + 0.5],
            "format": "grib",
        },
        "radiacion.grib",
    )

    print("✅ Archivo descargado: radiacion.grib")

    # ======================================================
    # 📗 Lectura del GRIB y procesamiento de variables
    # ======================================================
    datos = {}

    for var in ["ssrd", "tcc", "2t", "t2m"]:
        try:
            print(f"📥 Abriendo {var}...")
            ds = xr.open_dataset(
                "radiacion.grib",
                engine="cfgrib",
                backend_kwargs={"filter_by_keys": {"shortName": var}}
            )

            # Promediar dimensiones extra (lat, lon, step)
            dims_a_promediar = [d for d in ["step", "latitude", "longitude"] if d in ds.dims]
            if dims_a_promediar:
                ds = ds.mean(dim=dims_a_promediar)

            # Detectar nombre real dentro del dataset
            real_var_name = list(ds.data_vars.keys())[0]

            # Extraer datos
            times = pd.to_datetime(ds["time"].values)
            values = ds[real_var_name].values
            datos[var] = pd.DataFrame({"time": times, var: values})

            print(f"✅ {var} cargada correctamente ({len(values)} registros).")

        except Exception as e:
            print(f"⚠ No se pudo abrir {var}: {e}")

    # ======================================================
    # 🧮 Combinar variables por 'time'
    # ======================================================
    if "ssrd" not in datos:
        raise ValueError("❌ No se encontró la variable de radiación (ssrd).")

    df = datos["ssrd"]

    if "tcc" in datos:
        df = pd.merge(df, datos["tcc"], on="time", how="left")
    else:
        df["tcc"] = 0
        print("⚠ Nubosidad no encontrada: se asigna 0.")

    # Buscar temperatura (2t o t2m)
    temp_var = "2t" if "2t" in datos else "t2m" if "t2m" in datos else None
    if temp_var:
        df = pd.merge(df, datos[temp_var], on="time", how="left")
    else:
        df["t2m"] = np.nan
        print("⚠ Temperatura no encontrada: se asigna NaN.")

    # ======================================================
    # 💾 Guardar CSV con manejo de errores
    # ======================================================
    output_path = "radiacion.csv"

    try:
        df.to_csv(output_path, index=False)
        print(f"\n📁 CSV guardado correctamente: {output_path}")
    except PermissionError:
        # Si el archivo está abierto, guarda con un nombre nuevo
        backup_name = f"radiacion_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(backup_name, index=False)
        print(f"\n⚠ radiacion.csv estaba abierto. Se ha guardado como: {backup_name}")

    # Mostrar vista previa
    print("\n=== Vista previa del CSV ===")
    print(df.head())

    return df


# ======================================================
# 🚀 EJECUCIÓN DIRECTA
# ======================================================
if _name_ == "_main_":
    try:
        descargar_radiacion()
        print("\n✅ Descarga y conversión completadas con éxito.")
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")