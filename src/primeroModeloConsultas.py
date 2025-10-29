# cams_point_daily.py
import cdsapi

c = cdsapi.Client(quiet=False)

# Madrid centro (ejemplo)
lat, lon = 40.4168, -3.7038

c.retrieve(
    "cams-solar-radiation-timeseries",
    {
        "format": "csv",                # <<--- CSV
        "time_aggregation": "daily",    # "daily" o "hourly"
        "year": "2024",
        "month": "06",                  # "01"..."12" o lista ["06","07",...]
        "latitude": lat,
        "longitude": lon,
        # variables: GHI, DNI, DHI (y versiones clear-sky si quieres)
        "variable": [
            "surface_solar_radiation_downwards",                 # GHI
            "surface_direct_downwelling_shortwave_flux_in_air",  # DNI
            "surface_diffuse_downwelling_shortwave_flux_in_air", # DHI
        ],
        # "altitude": 650,             # opcional (m)
    },
    "cams_madrid_2024_06_daily.csv"
)
