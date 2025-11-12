"""
Descarga y muestra una ortofoto PNOA (IGN/CNIG) centrada en la UEM con "más zoom",
guardando en 'imagenes/'. Ahora detecta automáticamente la FECHA más reciente disponible
(vía WMS GetCapabilities -> Dimension/Extent 'time') y la usa en GetMap/GetFeatureInfo.

Requisitos:
    pip install requests pillow matplotlib
"""

import io
import re
import math
import json
from pathlib import Path

import requests
from PIL import Image
import matplotlib.pyplot as plt

from peticion_direcciones import geocode_osm

direccion = input("Introduce una dirección: ").strip()

CENTER_LAT, CENTER_LON = geocode_osm(direccion)

CUT_WIDTH_M  = 100        # <-- ANCHO IMAGEN (m)
CUT_HEIGHT_M = 100       # <-- ALTO RECORTE (m)

M_PER_PX = 0.15           # <-- resolucion -> m/pixeel

WMS_URL = "https://www.ign.es/wms-inspire/pnoa-ma"  # <--  WMS 
LAYER   = "OI.OrthoimageCoverage"                    # <--  capa 
FORMAT  = "image/jpeg"                               # "image/png" tmb
CRS     = "EPSG:4326"                                # tipo lat/ lon -> no tocar
TIMEOUT = 120                                        # segundos por petición

OUTPUT_DIR = Path("imagenes")                        # <-- carpeta de destino
FILENAME   = str(direccion)+"_imag"                     # nombre imagen


# ---- utilidades: metros -> grados en lat/lon ----
def meters_to_deg_lat(meters: float) -> float:
    """Convierte metros a grados de latitud (aprox)."""
    return meters / 111_320.0

def meters_to_deg_lon(meters: float, lat_deg: float) -> float:
    """Convierte metros a grados de longitud (aprox; depende de latitud)."""
    return meters / (111_320.0 * math.cos(math.radians(lat_deg)))


def build_bbox_4326(center_lat: float, center_lon: float, width_m: float, height_m: float):
    """
    Construye un BBOX (EPSG:4326) alrededor del punto central.
    IMPORTANTE (WMS 1.3.0 + EPSG:4326): BBOX = [minLat, minLon, maxLat, maxLon]
    """
    half_h_deg = meters_to_deg_lat(height_m / 2.0)
    half_w_deg = meters_to_deg_lon(width_m  / 2.0, center_lat)
    min_lat = center_lat - half_h_deg
    max_lat = center_lat + half_h_deg
    min_lon = center_lon - half_w_deg
    max_lon = center_lon + half_w_deg
    return (min_lat, min_lon, max_lat, max_lon)


def compute_dimensions_px(width_m: float, height_m: float, meters_per_px: float):
    """Calcula WIDTH/HEIGHT en píxeles a pedir al WMS."""
    width_px  = int(round(width_m  / meters_per_px))
    height_px = int(round(height_m / meters_per_px))
    return width_px, height_px


# ---------- NUEVO: detectar la TIME más reciente del WMS ----------
def get_latest_time_from_capabilities(wms_url: str, layer_name: str) -> str | None:
    """
    Llama a GetCapabilities y busca la dimensión/extent 'time' de la capa dada.
    Devuelve un string ISO (ej. '2023-07-15' o '2023-07-15/2024-05-01') o None si no hay tiempo.
    Estrategia:
      - Buscar el bloque <Layer>...<Name>layer_name</Name> ... </Layer>
      - Dentro, buscar <Dimension name="time"> o <Extent name="time"> y recoger su contenido.
      - Si viene una lista separada por comas, coger el último valor.
      - Si viene un rango 'start/end/period', coger 'end'.
    """
    params = {"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.3.0"}
    r = requests.get(wms_url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    xml = r.text

    # Localizar el bloque de la capa
    # OJO: regex sobre XML es heurístico; suficiente para uso práctico
    layer_pattern = re.compile(
        rf"<Layer[^>]*>\s*<Name>\s*{re.escape(layer_name)}\s*</Name>(.*?)</Layer>",
        re.DOTALL | re.IGNORECASE,
    )
    m_layer = layer_pattern.search(xml)
    if not m_layer:
        return None
    layer_block = m_layer.group(1)

    # Buscar Dimension o Extent de 'time'
    m_dim = re.search(r'<Dimension[^>]*name=["\']time["\'][^>]*>(.*?)</Dimension>',
                      layer_block, re.DOTALL | re.IGNORECASE)
    if not m_dim:
        m_dim = re.search(r'<Extent[^>]*name=["\']time["\'][^>]*>(.*?)</Extent>',
                          layer_block, re.DOTALL | re.IGNORECASE)
    if not m_dim:
        return None

    time_text = m_dim.group(1).strip()

    # Casos:
    # 1) lista separada por comas: "2018-01-01,2019-06-01,2022-07-15,2024-06-10"
    if "," in time_text:
        parts = [p.strip() for p in time_text.split(",") if p.strip()]
        return parts[-1] if parts else None

    # 2) rango: "2018-01-01/2024-06-10/P1Y" -> devolvemos el 'end' (2º elemento)
    if "/" in time_text:
        parts = [p.strip() for p in time_text.split("/") if p.strip()]
        if len(parts) >= 2:
            return parts[1]  # end
        return parts[0] if parts else None

    # 3) un único valor
    return time_text or None


def request_wms_image(bbox_4326, width_px: int, height_px: int, time_value: str | None) -> tuple[bytes, str | None]:
    """
    Lanza un WMS GetMap y devuelve los bytes de la imagen y la TIME usada (si aplica).
    Si time_value es None, no se envía el parámetro TIME.
    """
    params = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": "1.3.0",
        "LAYERS": LAYER,
        "STYLES": "",
        "FORMAT": FORMAT,
        "CRS": CRS,
        # EPSG:4326 (WMS 1.3.0): BBOX = minLat,minLon,maxLat,maxLon
        "BBOX": f"{bbox_4326[0]},{bbox_4326[1]},{bbox_4326[2]},{bbox_4326[3]}",
        "WIDTH": str(width_px),
        "HEIGHT": str(height_px),
        "TRANSPARENT": "FALSE",
    }
    # NUEVO: pasar TIME si lo tenemos
    if time_value:
        params["TIME"] = time_value  # algunos servidores aceptan 'time' en minúsculas también

    print("📡 GetMap params clave:")
    print(f"  LAYERS={LAYER}  FORMAT={FORMAT}  CRS={CRS}")
    if time_value:
        print(f"  TIME={time_value}")
    print(f"  BBOX={params['BBOX']}")
    print(f"  SIZE={width_px}x{height_px} px  ({M_PER_PX} m/px)")

    resp = requests.get(WMS_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()

    ctype = resp.headers.get("Content-Type", "")
    if "image" not in ctype:
        print("⚠️ Respuesta no es una imagen. Content-Type:", ctype)
        print(resp.text[:500])
        raise RuntimeError("El WMS no devolvió una imagen. Revisa parámetros o reduce tamaño.")

    return resp.content, params.get("TIME")


def save_and_show(img_bytes: bytes, output_dir: Path, base_name: str, possible_date: str | None):
    """
    Guarda la imagen en 'output_dir' con nombre base 'base_name' + fecha (si hay),
    y la muestra en pantalla.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # Usa fecha detectada o, si no, la TIME usada (puede ser un año/rango)
    tag = possible_date
    suffix = f"_{tag}" if tag else ""
    out_path = output_dir / f"{base_name}{suffix}.jpg"

    out_path.write_bytes(img_bytes)
    print(f"✅ Imagen guardada en: {out_path.resolve()}")

    with Image.open(io.BytesIO(img_bytes)) as im:
        im = im.convert("RGB")
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        arr = plt.imread(buf)

    plt.figure(figsize=(7, 7))
    ttl = str(direccion)+" — PNOA (~{:.0f} cm/px)".format(M_PER_PX * 100)
    plt.title(ttl)
    plt.imshow(arr)
    plt.axis("off")
    plt.show()


def main():
    # 0) BBOX y dimensiones
    bbox = build_bbox_4326(CENTER_LAT, CENTER_LON, CUT_WIDTH_M, CUT_HEIGHT_M)
    width_px, height_px = compute_dimensions_px(CUT_WIDTH_M, CUT_HEIGHT_M, M_PER_PX)

    # 1) Detectar la última TIME disponible del WMS (si existe)
    print("🕒 Buscando TIME más reciente en GetCapabilities…")
    latest_time = None
    try:
        latest_time = get_latest_time_from_capabilities(WMS_URL, LAYER)
        if latest_time:
            print("   TIME detectada:", latest_time)
        else:
            print("   Sin dimensión temporal detectable; se pedirá sin TIME.")
    except Exception as e:
        print("   No se pudo leer GetCapabilities:", e)

    # 2) Pedir la imagen (con TIME si la hay)
    img_bytes, time_used = request_wms_image(bbox, width_px, height_px, latest_time)

    

    # 4) Guardar en carpeta 'imagenes/' y mostrar
    save_and_show(img_bytes, OUTPUT_DIR, FILENAME, time_used)


if __name__ == "__main__":
    main()
