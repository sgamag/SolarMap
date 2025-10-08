import os
import json
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

#Endpoint de obtencion de credenciales
AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"


CACHE_PATH = Path(__file__).resolve().parent.parent / "token_cdse.json"

# Tiempo en segundos para renovar el token
SAFETY_MARGIN = 300

#Funcion para pedir el token usando el usuario y la contraseña
def _request_new_token(username: str, password: str) -> dict:
    
    #Devuelve el JSON de respuesta con campos: access_token, expires_in, etc.
    
    resp = requests.post(
        AUTH_URL,
        data={
            "client_id": "cdse-public",
            "grant_type": "password",
            "username": username,
            "password": password,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

# Guardamos timestamps para gestionar expiración
    now = int(time.time())
    data["obtained_at"] = now
    data["expires_at"] = now + int(data.get("expires_in", 3600))
    return data

def _load_cache() -> dict | None:
    """Lee el token cacheado si existe (si no, None)."""
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def _save_cache(data: dict) -> None:
    """Guarda el token y metadatos en disco."""
    CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def get_token(force_refresh: bool = False) -> str:
    """
    Devuelve un access token válido.
    - Lee CDSE_USER y CDSE_PASSWORD desde .env/variables de entorno.
    - Reutiliza el token cacheado mientras no esté a punto de expirar.
    - Si force_refresh=True, pide uno nuevo siempre.
    """
    load_dotenv()  # permite leer de .env
    user = os.getenv("CDSE_USER")
    password = os.getenv("CDSE_PASSWORD")
    if not user or not password:
        raise RuntimeError(
            "Faltan credenciales: define CDSE_USER y CDSE_PASSWORD en tu .env o variables de entorno."
        )

    if not force_refresh:
        cache = _load_cache()
        now = int(time.time())
        if cache and "access_token" in cache:
            # ¿Sigue siendo seguro usarlo?
            if cache.get("expires_at", 0) - SAFETY_MARGIN > now:
                return cache["access_token"]

    # No hay token válido → pedimos uno nuevo
    data = _request_new_token(user, password)
    _save_cache(data)
    return data["access_token"]