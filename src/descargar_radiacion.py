# src/descargar_cams.py
import cdsapi

def descargar_radiacion_csv(lat=40.4, lon=-3.7):
    """
    Descarga datos de radiación solar y nubosidad del servicio CAMS (Copernicus)
    en formato CSV, usando credenciales integradas en el código.
    """


    # Conexión a la API
    c = cdsapi.Client(
        url="https://ads.atmosphere.copernicus.eu/api",
        key=f"a78d8196-d488-49c5-8c73-615d85f31c61"
    )

    # Petición de datos (10 días, 8 observaciones diarias)
    c.retrieve(
        'cams-global-radiation-single-levels',
        {
            'date': '2025-10-01/2025-10-10',
            'time': [
                '00:00', '03:00', '06:00', '09:00',
                '12:00', '15:00', '18:00', '21:00'
            ],
            'variable': [
                'surface_solar_radiation_downwards',  # radiación global
                'direct_solar_radiation_at_surface',  # directa
                'diffuse_solar_radiation_at_surface', # difusa
                'total_cloud_cover',                   # nubosidad
            ],
            'format': 'csv',                           # formato cómodo para ML
            'area': [lat + 0.5, lon - 0.5, lat - 0.5, lon + 0.5],  # [N, W, S, E]
        },
        'radiacion.csv'                                # archivo resultante
    )

    print("✅ Archivo descargado: radiacion.csv")


if __name__ == "__main__":
    descargar_radiacion_csv()
