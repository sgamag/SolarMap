# peticion_direcciones.py

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def _geocode_osm_raw(direccion: str):
    """
    Función interna: devuelve la respuesta JSON de Nominatim.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": direccion,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "GeoApp/1.0u"
    }

    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data


def geocode_osm(direccion: str):
 
    data = _geocode_osm_raw(direccion)

    if not data:
        print("No se encontró la dirección.")
        return None

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    print(f" Dirección: {data[0]['display_name']}")
    print(f"Latitud: {lat}")
    print(f"Longitud: {lon}")
    return lat, lon



@app.get("/geocode")
def geocode_endpoint(direccion: str):
  
    data = _geocode_osm_raw(direccion)

    if not data:
        raise HTTPException(status_code=404, detail="Dirección no encontrada")

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    display_name = data[0]["display_name"]

    return {
        "lat": lat,
        "lon": lon,
        "display_name": display_name
    }


if __name__ == "__main__":
    direccion = input("Introduce una dirección: ").strip()
    geocode_osm(direccion)
