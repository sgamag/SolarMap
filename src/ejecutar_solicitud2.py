# src/ejecutar_solicitud2.py
from pathlib import Path
import logging
from pathlib import Path
from login import get_access_token
from login import get_token
from descargar_radiacion import buscar_s2_l2a, descargar_zip, descomprimir_safe
from procesar_radiacion import procesar_safe_a_geotiff
from solicitud_builder import solicitud_bbox_ultimos_dias

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def main():
    token = get_token() # ESTA DE AQUI NO SE SI VA AQUI O EN OTRO LADO
    token = get_access_token()
    out_dir_data = Path("data")
    out_dir_tif = Path("out")
    out_dir_data.mkdir(exist_ok=True)
    out_dir_tif.mkdir(exist_ok=True)

    # Ejemplo: Madrid aprox, últimos 30 días, ≤10% nubes
    req = solicitud_bbox_ultimos_dias(
        lon_min=-3.8, lat_min=40.2, lon_max=-3.2, lat_max=40.7,
        dias=30, max_cloud=10.0, top=3, nota="Madrid_30d_10cloud"
    )

    params = req.to_params()

    try:
        productos = buscar_s2_l2a(
            token,
            params["wkt_aoi"],
            params["iso_start"],
            params["iso_end"],
            max_cloud=params["max_cloud"],
            top=params["top"]
        )
        if not productos:
            logging.warning("Sin resultados para la solicitud: %s", req)
            return

        p0 = productos[0]
        zip_path = descargar_zip(token, p0["Id"], out_dir=out_dir_data)
        safe_dir = descomprimir_safe(zip_path, out_dir=out_dir_data)

        out_tif = out_dir_tif / f"{p0['Name']}_subset_mask_10m.tif"
        procesar_safe_a_geotiff(Path(safe_dir), params["wkt_aoi"], out_tif)
        logging.info("Listo: %s", out_tif)

    except Exception as e:
        logging.error("Error durante la descarga o procesamiento: %s", e)

if __name__ == "__main__":
    main()
    

