import os
import json
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

# 🔐 URL oficial de login de Copernicus
AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

# 📁 Ruta donde se guarda el token (sube dos niveles desde src/)
CACHE_PATH = Path(__file__).resolve().parent.parent / "token_cdse.json"

# 🕒 Margen de seguridad antes de que el token caduque (5 minutos)
SAFETY_MARGIN = 300  # segundos


def _request_new_token(username: str, password: str) -> dict:
    """
    Pide un token nuevo a Copernicus con usuario y contraseña.
    Devuelve el JSON con el access_token y tiempos de expiración.
    """
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

    now = int(time.time())
    data["obtained_at"] = now
    data["expires_at"] = now + int(data.get("expires_in", 3600))
    return data


def _load_cache() -> dict | None:
    """Lee el token cacheado si existe (si no, devuelve None)."""
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _save_cache(data: dict) -> None:
    """Guarda el token en disco y muestra la ruta exacta."""
    CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"💾 Token guardado en: {CACHE_PATH}")


def get_token(force_refresh: bool = False) -> str:
    """
    Devuelve un access token válido.
    - Carga CDSE_USER y CDSE_PASSWORD desde .env.
    - Usa el cache si sigue siendo válido.
    - Si force_refresh=True, pide uno nuevo siempre.
    """
    load_dotenv()
    user = os.getenv("CDSE_USER")
    password = os.getenv("CDSE_PASSWORD")
    if not user or not password:
        raise RuntimeError("⚠️ Faltan CDSE_USER y CDSE_PASSWORD en el archivo .env")

    # Intentamos usar token cacheado
    if not force_refresh:
        cache = _load_cache()
        now = int(time.time())
        if cache and "access_token" in cache:
            if cache.get("expires_at", 0) - SAFETY_MARGIN > now:
                print(f"✅ Usando token cacheado desde: {CACHE_PATH}")
                return cache["access_token"]

    # Si no hay token válido → pedimos uno nuevo
    print("🔄 Solicitando nuevo token a Copernicus...")
    data = _request_new_token(user, password)
    _save_cache(data)
    print(f"✅ Nuevo token obtenido. Expira en {data['expires_in'] // 60} minutos.")
    return data["access_token"]
