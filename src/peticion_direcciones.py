import requests

def geocode_osm(direccion: str):
    
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

    if not data:
        print("⚠️ No se encontró la dirección.")
        return None

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    print(f"📍 Dirección: {data[0]['display_name']}")
    print(f"   → Latitud: {lat}")
    print(f"   → Longitud: {lon}")
    return lat, lon


# Ejemplo de uso
if __name__ == "__main__":
    direccion = input("Introduce una dirección: ").strip() or "Universidad Europea de Madrid, Villaviciosa de Odón"
    geocode_osm(direccion)
