import cdsapi
import xarray as xr
import pandas as pd

def descargar_radiacion(lat=40.4, lon=-3.7):
    """
    Descarga datos de radiación solar y nubosidad desde ERA5 (CDS),
    guarda NetCDF y CSV, y devuelve la ruta del CSV.
    """
    print("🔄 Conectando al Climate Data Store (ERA5)...")

    c = cdsapi.Client(
        url="https://cds.climate.copernicus.eu/api",
        key="a78d8196-d488-49c5-8c73-615d85f31c61"
    )

    c.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": "reanalysis",
            "variable": [
                "surface_solar_radiation_downwards",
                "total_cloud_cover",
                "2m_temperature",
            ],
            "year": ["2024"],
            "month": ["10"],
            "day": [f"{i:02d}" for i in range(1, 11)],
            "time": ["00:00", "06:00", "12:00", "18:00"],
            "area": [lat + 0.5, lon - 0.5, lat - 0.5, lon + 0.5],
            "format": "netcdf",
        },
        "radiacion.nc",
    )

    print("✅ Archivo NetCDF descargado: radiacion.nc")

    # Convertir a DataFrame promedio espacial
    ds = xr.open_dataset("radiacion.nc")
    df = ds.mean(dim=["latitude", "longitude"]).to_dataframe().reset_index()

    col_ssrd = next((v for v in df.columns if "ssrd" in v or "radiation" in v or "solar" in v), None)
    col_tcc  = next((v for v in df.columns if "tcc" in v or "cloud" in v), None)

    if not col_ssrd or not col_tcc:
        raise ValueError(f"No se encontraron columnas esperadas. Variables: {list(df.columns)}")

    df.to_csv("radiacion.csv", index=False)
    print("📁 CSV guardado: radiacion.csv")
    return "radiacion.csv"


if __name__ == "__main__":
    descargar_radiacion()
