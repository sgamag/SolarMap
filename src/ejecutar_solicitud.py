# src/ejecutar_solicitud.py
from pathlib import Path
from login import get_access_token             # ya lo tienes
from descargar_radiacion import buscar_s2_l2a, descargar_zip, descomprimir_safe
from procesar_radiacion import procesar_safe_a_geotiff
from solicitud_builder import solicitud_bbox_ultimos_dias

def main():
    token = get_access_token()

    # Ejemplo: Madrid aprox, últimos 30 días, ≤10% nubes
    req = solicitud_bbox_ultimos_dias(
        lon_min=-3.8, lat_min=40.2, lon_max=-3.2, lat_max=40.7,
        dias=30, max_cloud=10.0, top=3, nota="Madrid_30d_10cloud"
    )

    params = req.to_params()

    # Tus funciones existentes ya esperan estos parámetros
    productos = buscar_s2_l2a(
        token,
        params["wkt_aoi"],
        params["iso_start"],
        params["iso_end"],
        max_cloud=params["max_cloud"],
        top=params["top"]
    )
    if not productos:
        print("Sin resultados para la solicitud:", req)
        return

    p0 = productos[0]
    zip_path = descargar_zip(token, p0["Id"], out_dir="data")
    safe_dir = descomprimir_safe(zip_path, out_dir="data")

    out_tif = Path("out") / f"{p0['Name']}_subset_mask_10m.tif"
    procesar_safe_a_geotiff(Path(safe_dir), params["wkt_aoi"], out_tif)
    print("Listo:", out_tif)

if __name__ == "__main__":
    main()
