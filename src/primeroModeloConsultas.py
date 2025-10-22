# era5_bbox_to_netcdf.py
import cdsapi

c = cdsapi.Client()

c.retrieve(
    "reanalysis-era5-single-levels",
    {
        "product_type": "reanalysis",
        "format": "netcdf",                     # << para trabajar con xarray
        "variable": [
            "surface_solar_radiation_downwards",
            "sunshine_duration",
            "total_cloud_cover",
            "2m_temperature",
        ],
        "year": "2024",
        "month": "06",
        "day": [f"{d:02d}" for d in range(1, 31)],
        "time": [f"{h:02d}:00" for h in range(24)],
        "area": [40.6, -3.9, 40.3, -3.5],      # [N, W, S, E] (ojo al orden)
    },
    "era5_madrid_202406_bbox.nc"
)
