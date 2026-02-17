import os, json, time, requests
from pathlib import Path
from dotenv import load_dotenv

" URL oficial de login de Copernicus para pedir el token "
URL_Coper = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

" Ruta para guardar el token "
ruta_guard = Path(__file__).resolve().parent.parent / "token_cdse.json"

" Tiempo para que caduque el token "
tiempCad = 300  # segundos


def pedir_token(usuario: str, contr: str) -> dict:
    """
    Pide un token nuevo a Copernicus con usuario y contraseña.
    Devuelve el JSON con el access_token y tiempos de expiración.
    """
    resp = requests.post(
        URL_Coper,
        data={
            "client_id": "cdse-public",
            "grant_type": "password",
            "username": usuario,
            "password": contr,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    now = int(time.time())
    data["Pedido"] = now
    data["Caduca"] = now + int(data.get("expires_in", 3600))
    return data


def verif_token() -> dict | None:
    "Revisa si el token es válido o no"
    if ruta_guard.exists():
        try:
            return json.loads(ruta_guard.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def guard_token(data: dict) -> None:
    """Guarda el token en disco y muestra la ruta exacta."""
    ruta_guard.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Token almacenado en: {ruta_guard}")


def get_token(force_refresh: bool = False) -> str:

    "Si haces get_token(), devuelve tu token si valido o uno nuevo si no lo es"
    "Si haces get_token(True), fuerza a pedir uno nuevo"

    load_dotenv()
    usuar = os.getenv("CDSE_USER")
    contr = os.getenv("CDSE_PASSWORD")

    if not usuar or not contr:
        raise RuntimeError(" Faltan credenciales")

    " Intentamos usar token cacheado "

    if not force_refresh:
        cache = verif_token()
        now = int(time.time())
        if  "access_token" in cache:
            if cache.get("Caduca", 0) - tiempCad > now:
                print(f"Usando token previamente cacheado desde: {ruta_guard}")
                return cache["access_token"]

    " Si no hay token válido, pedimos uno nuevo "
    
    print("Solicitando nuevo token a Copernicus")
    data = pedir_token(usuar, contr)
    guard_token(data)
    print(f"Nuevo token obtenido. Expira en {data['Caduca'] // 60} minutos.")
    return data["access_token"]
