import os, requests
from dotenv import load_dotenv

# 1) Credenciales (en .env)
load_dotenv()
USER = os.getenv("CDSE_USER")
PASSWORD = os.getenv("CDSE_PASSWORD")

# 2) Obtener token (form-data, no JSON)
AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
auth_form = {
    "client_id": "cdse-public",
    "grant_type": "password",
    "username": USER,
    "password": PASSWORD,
}
tok = requests.post(AUTH_URL, data=auth_form)
tok.raise_for_status()
token = tok.json()["access_token"]

# 3) STAC Item Search (endpoint correcto)
STAC_URL = "https://stac.dataspace.copernicus.eu/v1/search"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

payload = {
    "collections": ["sentinel-2-l2a"],
    "bbox": [-3.8, 40.3, -3.6, 40.5],             # [west, south, east, north]
    "datetime": "2024-06-01T00:00:00Z/2024-06-30T23:59:59Z",
    "limit": 5
}

resp = requests.post(STAC_URL, json=payload, headers=headers)
resp.raise_for_status()

data = resp.json()
print("Resultados:", len(data.get("features", [])))
for f in data.get("features", []):
    p = f["properties"]
    print(f["id"], p.get("datetime"), p.get("eo:cloud_cover"))


import requests
from PIL import Image
from io import BytesIO

token = tok  # usa el mismo token que usaste en la búsqueda

thumbnail_url = "https://zipper.dataspace.copernicus.eu/api/v1/collections/SENTINEL-2-L2A/items/S2A_MSIL2A_20240624T110641_N0510_R137_T30TVK_20240624T153247/assets/thumbnail"

headers = {"Authorization": f"Bearer {token}"}

response = requests.get(thumbnail_url, headers=headers)
response.raise_for_status()  # ❌ aquí daba el 404 sin token

img = Image.open(BytesIO(response.content))
img.show()
