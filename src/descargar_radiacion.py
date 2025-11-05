# ======================================================
# ☀️ COPERNICUS ERA5 - Descarga y extracción flexible (time o step)
# ======================================================

import cdsapi
import xarray as xr
import pandas as pd
import numpy as np
import eccodes
from datetime import datetime

def descargar_era5(lat=40.4, lon=-3.7):
    """
    Descarga variables de ERA5 (ssrd, tcc, 2t) y extrae todas
    las variables posibles por 'step' o 'time' según corresponda.
    """

    print("🔄 Conectando al Climate Data Store (ERA5)...")

    c = cdsapi.Client(
        url="https://cds.climate.copernicus.eu/api",
        key="a78d8196-d488-49c5-8c73-615d85f31c61"
    )

    horas = [f"{h:02d}:00" for h in [6,8,10,12,14,16,18,20,22]]

    # ======================================================
    # 📡 DESCARGA
    # ======================================================
    c.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": "reanalysis",
            "variable": [
                "surface_solar_radiation_downwards",  # ☀️ radiación solar acumulada
                "total_cloud_cover",                  # ☁️ nubosidad
                "2m_temperature",                     # 🌡️ temperatura
                "10u", "10v"                          # 💨 viento
            ],
            "year": ["2024"],
            "month": [f"{m:02d}" for m in range(1, 13)],
            "day": [f"{i:02d}" for i in range(1, 32)],
            "time": horas,
            "area": [lat + 0.5, lon - 0.5, lat - 0.5, lon + 0.5],
            "format": "grib",
        },
        "era5_completo.grib",
    )

    print("✅ Archivo descargado: era5_completo.grib")

    # ======================================================
    # 📗 LECTURA DE VARIABLES
    # ======================================================
    datos = {}

    # --- Lectura especial para acumuladas (como ssrd)
    acumuladas = ["ssrd", "tp", "fdir", "strd"]

    # --- Intentar abrir todas las variables presentes
    try:
        print("📥 Detectando shortNames disponibles...")
        short_names = set()
        with open("era5_completo.grib", "rb") as f:
            while True:
                gid = eccodes.codes_grib_new_from_file(f)
                if gid is None:
                    break
                try:
                    short_names.add(eccodes.codes_get(gid, "shortName"))
                except Exception:
                    pass
                eccodes.codes_release(gid)
        print(f"Variables detectadas en el archivo: {short_names}")
    except Exception as e:
        print(f"⚠️ No se pudieron listar variables: {e}")
        short_names = {"ssrd", "tcc", "2t", "10u", "10v"}

    # --- Leer variable por variable
    for var in short_names:
        try:
            print(f"📥 Abriendo {var}...")
            if var in acumuladas:
                # método ECCODES: reconstruir con time + step
                times, values = [], []
                with open("era5_completo.grib", "rb") as f:
                    while True:
                        gid = eccodes.codes_grib_new_from_file(f)
                        if gid is None:
                            break
                        if eccodes.codes_get(gid, "shortName") == var:
                            base_date = str(eccodes.codes_get(gid, "dataDate"))
                            base_time = eccodes.codes_get(gid, "dataTime")
                            step = eccodes.codes_get(gid, "step")
                            val = np.mean(eccodes.codes_get_values(gid))
                            hora_base = base_time // 100
                            fecha_base = pd.Timestamp(f"{base_date[:4]}-{base_date[4:6]}-{base_date[6:]} {hora_base:02d}:00")
                            fecha_real = fecha_base + pd.to_timedelta(step, unit="h")
                            times.append(fecha_real)
                            values.append(val)
                        eccodes.codes_release(gid)
                df_var = pd.DataFrame({"time": times, var: values}).sort_values("time").reset_index(drop=True)
                datos[var] = df_var
                print(f"✅ {var} cargada ({len(df_var)} registros, usando step).")

            else:
                # método CFGRIB normal (instantáneas por time)
                ds = xr.open_dataset(
                    "era5_completo.grib",
                    engine="cfgrib",
                    backend_kwargs={"filter_by_keys": {"shortName": var}}
                )
                if {"latitude", "longitude"} <= set(ds.dims):
                    ds = ds.mean(dim=["latitude", "longitude"])
                real_name = list(ds.data_vars.keys())[0]
                times = pd.to_datetime(ds["time"].values)
                values = ds[real_name].values
                df_var = pd.DataFrame({"time": times, var: values})
                datos[var] = df_var
                print(f"✅ {var} cargada ({len(values)} registros, usando time).")

        except Exception as e:
            print(f"⚠️ No se pudo abrir {var}: {e}")

    # ======================================================
    # 🧮 COMBINAR TODO
    # ======================================================
    print("🧩 Combinando todas las variables...")
    variables = list(datos.keys())
    if not variables:
        raise ValueError("❌ No se cargó ninguna variable correctamente.")
    df = datos[variables[0]]
    for v in variables[1:]:
        df = pd.merge(df, datos[v], on="time", how="outer")

    df = df.sort_values("time").reset_index(drop=True)

    # ======================================================
    # 💾 GUARDAR CSV
    # ======================================================
    output_path = "era5_completo.csv"
    try:
        df.to_csv(output_path, index=False, float_format="%.2f")
        print(f"\n📁 CSV guardado correctamente: {output_path}")
    except PermissionError:
        backup = f"era5_completo_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(backup, index=False, float_format="%.2f")
        print(f"\n⚠️ Archivo abierto, se guardó como {backup}")

    print("\n=== Vista previa del CSV ===")
    print(df.head(10))

    return df


# ======================================================
# 🚀 EJECUCIÓN DIRECTA
# ======================================================
if __name__ == "__main__":
    try:
        descargar_era5()
        print("\n✅ Descarga y extracción completadas con éxito.")
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
