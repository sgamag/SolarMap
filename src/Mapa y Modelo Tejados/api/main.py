import os
import uuid
import requests

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from modelo_web.modelo_resumido import cargar_modelo, detectar_tejados


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


print("Cargando modelo...")
model = cargar_modelo()
print("Modelo cargado correctamente")


@app.get("/")
def root():
    return {"status": "API tejados funcionando"}


@app.get("/geocode")
def geocode_endpoint(direccion: str):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": direccion,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "SolarMap/1.0"
    }

    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()

    data = r.json()

    if not data:
        raise HTTPException(status_code=404, detail="Dirección no encontrada")

    return {
        "lat": float(data[0]["lat"]),
        "lon": float(data[0]["lon"]),
        "display_name": data[0]["display_name"]
    }


@app.post("/detect-roofs")
async def detect_roofs(
    image: UploadFile = File(...),
    metadata: str = Form(...)
):
    image_filename = f"{uuid.uuid4()}.png"
    metadata_filename = f"{uuid.uuid4()}.json"

    image_path = os.path.join(TEMP_DIR, image_filename)
    metadata_path = os.path.join(TEMP_DIR, metadata_filename)

    try:
        with open(image_path, "wb") as f:
            f.write(await image.read())

        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(metadata)

        geojson = detectar_tejados(
            model=model,
            image_path=image_path,
            metadata_path=metadata_path,
            threshold=0.70,
            area_minima_px=150
        )

        return geojson

    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

        if os.path.exists(metadata_path):
            os.remove(metadata_path)