# src/ver_imagen_stac.py
"""
Busca escenas Sentinel-2 (CDSE STAC), descarga un thumbnail y lo muestra.

Requisitos (ya los tienes en requirements):
- requests
- matplotlib

Ejecución:
    python ver_imagen_stac.py
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from login import get_token
import requests
import matplotlib.pyplot as plt

# ------------------------
#  OPCIÓN DE TOKEN MANUAL
#  (si no quieres usar login.get_token, pega aquí tu token y listo)
# ------------------------
ACCESS_TOKEN: Optional[str] = None  # p. ej: "eyJhbGciOiJIUzI1..."

# ------------------------
#  INTENTO DE IMPORTAR TU login.get_token()
# ------------------------
def obtener_token() -> str:
    """
    Intenta usar login.get_token(); si falla, usa ACCESS_TOKEN.
    Imprime además qué 'login.py' ha cargado Python.
    """
    if ACCESS_TOKEN:
        print("🔐 Usando ACCESS_TOKEN pegado en ver_imagen_stac.py")
        return ACCESS_TOKEN

    try:
        import login  # tu archivo src/login.py
        print(f"ℹ️ login.py cargado desde: {getattr(login, '__file__', 'desconocido')}")
        if hasattr(login, "get_token"):
            token = login.get_token()  # usa tu cache/renovación
            print("✅ Token obtenido desde login.get_token()")
            return token
        else:
            raise ImportError("El módulo 'login' no tiene función get_token()")
    except Exception as e:
        raise SystemExit(
            f"❌ No pude obtener token automáticamente.\n"
            f"Detalle: {e}\n\n"
            f"Soluciones rápidas:\n"
            f"  1) Asegúrate de que 'login.py' tiene una función get_token() (exacto ese nombre).\n"
            f"  2) O pega tu token en ACCESS_TOKEN arriba de este archivo y vuelve a ejecutar."
        )


# ------------------------
#  ENDPOINT STAC
# ------------------------
STAC_SEARCH_URL = "https://stac.dataspace.copernicus.eu/v1/search"

PREVIEWS_DIR = Path("data/previews")
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------
#  TOMAMOS PARÁMETROS DE TU MODELO
# ------------------------
from modelo_peticion_imagen import madrid_demo_request, ImageRequest


# ---- utilidades de formato ----
def wkt_polygon_to_geojson_intersects(wkt: str) -> Dict[str, Any]:
    """Convierte POLYGON WKT (lon lat) a GeoJSON para 'intersects'."""
    wkt_up = wkt.strip().upper()
    if not wkt_up.startswith("POLYGON"):
        raise ValueError("Se esperaba un POLYGON WKT.")

    inner = wkt[wkt.find("((") + 2 : wkt.rfind("))")]
    pairs = inner.split(",")

    coords: List[List[float]] = []
    for p in pairs:
        p = p.strip()
        parts = p.split()
        if len(parts) != 2:
            raise ValueError(f"Par de coordenadas inválido en WKT: {p}")
        lon, lat = float(parts[0]), float(parts[1])
        coords.append([lon, lat])

    return {"type": "Polygon", "coordinates": [coords]}


def build_stac_payload_from_request(req: ImageRequest) -> Dict[str, Any]:
    """
    Crea el payload de /v1/search a partir de tu ImageRequest.
    Usa 'sentinel-2-l2a' cuando product_type es S2MSI2A, si no 'sentinel-2-l1c'.
    """
    p = req.to_params()
    collections = ["sentinel-2-l2a"] if p["product_type"] == "S2MSI2A" else ["sentinel-2-l1c"]

    payload = {
        "collections": collections,
        "datetime": f"{p['iso_start']}/{p['iso_end']}",
        "limit": int(p["top"]),
        "query": {"eo:cloud_cover": {"lt": float(p["max_cloud"])}},
        "intersects": wkt_polygon_to_geojson_intersects(p["wkt_aoi"]),
    }
    return payload


# ---- llamadas HTTP ----
def stac_search(token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(STAC_SEARCH_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def pick_best_feature(features: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Elige la mejor por menos nubes y fecha más reciente."""
    if not features:
        return None
    # Primero ordena por fecha desc, luego por nubes asc
    features_sorted = sorted(features, key=lambda f: (f.get("properties", {}).get("datetime") or ""), reverse=True)
    features_sorted = sorted(features_sorted, key=lambda f: (f.get("properties", {}).get("eo:cloud_cover") or 9999.0))
    return features_sorted[0]


def get_thumbnail_href(feature: Dict[str, Any]) -> Optional[str]:
    assets = feature.get("assets", {}) or {}
    for key in ("thumbnail", "overview", "quicklook", "visual"):
        if key in assets and isinstance(assets[key], dict):
            href = assets[key].get("href")
            if href:
                return href
    return None


def download_binary(url: str, token: Optional[str], out_path: Path) -> bool:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, timeout=60, stream=True)
    if resp.status_code == 401:
        resp = requests.get(url, timeout=60, stream=True)
    if resp.status_code != 200:
        print(f"⚠️ No se pudo descargar thumbnail (HTTP {resp.status_code})")
        return False
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return True


def show_image(path: Path) -> None:
    img = plt.imread(str(path))
    plt.figure()
    plt.title(path.name)
    plt.imshow(img)
    plt.axis("off")
    plt.show()


# ---- main ----
def main():
    # 0) token
    token = obtener_token()

    # 1) parámetros
    req = madrid_demo_request()
    payload = build_stac_payload_from_request(req)
    print("📤 Payload STAC listo:\n", json.dumps(payload, indent=2))

    # 2) búsqueda
    print("\n🔎 Buscando imágenes...")
    result = stac_search(token, payload)
    features = result.get("features", [])
    print(f"✅ Resultados: {len(features)}")
    if not features:
        print("⚠️ Sin resultados. Ajusta fechas, AOI o CLOUD_MAX en modelo_peticion_imagen.py")
        return

    # 3) mejor imagen
    best = pick_best_feature(features)
    props = best.get("properties", {})
    print(f"\n🏆 Seleccionada: id={best.get('id')} | fecha={props.get('datetime')} | nubes={props.get('eo:cloud_cover')}")

    # 4) thumbnail
    thumb_url = get_thumbnail_href(best)
    if not thumb_url:
        print("⚠️ Esta imagen no tiene thumbnail/quicklook disponible.")
        return
    out_path = PREVIEWS_DIR / f"thumbnail_{best.get('id')}.jpg"
    if download_binary(thumb_url, token, out_path):
        print(f"💾 Thumbnail guardado en: {out_path.resolve()}")
        print("🖼️ Mostrando imagen...")
        show_image(out_path)
    else:
        print("⚠️ No se pudo descargar la miniatura.")


if __name__ == "__main__":
    main()
