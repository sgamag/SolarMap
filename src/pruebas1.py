import os
import requests
from dotenv import load_dotenv

# 1) Credenciales (usa .env)
load_dotenv()
USER = os.getenv("CDSE_USER")
PASSWORD = os.getenv("CDSE_PASSWORD")

# 2) Obtener token (FORM, no JSON)
AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
auth_form = {
    "client_id": "cdse-public",
    "grant_type": "password",
    "username": USER,
    "password": PASSWORD,
}
auth_resp = requests.post(AUTH_URL, data=auth_form)
auth_resp.raise_for_status()
token = auth_resp.json()["access_token"]

# 3) Búsqueda STAC (endpoint correcto)
STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

# ⚠️ Ejemplo con Sentinel-2 L2A (óptico). Para Sentinel-1 usa "sentinel-1-grd".
payload = {
    "collections": ["sentinel-2-l2a"],
    "bbox": [-3.8, 40.3, -3.6, 40.5],  # [west, south, east, north]
    "datetime": "2023-06-01T00:00:00Z/2023-06-30T23:59:59Z",
    "limit": 5
}

resp = requests.post(STAC_URL, json=payload, headers=headers)

# 4) Manejo robusto de errores para ver qué pasa si es 400
try:
    resp.raise_for_status()
except requests.HTTPError:
    print("❌ Error:", resp.status_code)
    print(resp.text)  # mensaje exacto del servidor (muy útil)
    raise

data = resp.json()
features = data.get("features", [])
print(f"🔎 Resultados: {len(features)}")

for f in features:
    props = f.get("properties", {})
    assets = f.get("assets", {})
    print("🛰️  ID:", f.get("id"))
    print("📅  Fecha:", props.get("datetime"))
    # Solo S2 tiene 'eo:cloud_cover'
    print("☁️  Nubosidad:", props.get("eo:cloud_cover", "N/A"))
    # 'thumbnail' suele existir, pero comprueba
    thumb = assets.get("thumbnail", {}).get("href", "sin miniatura")
    print("🔗 Miniatura:", thumb)
    print()
