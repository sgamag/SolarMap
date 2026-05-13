import os
import uuid
import requests
import hashlib
import mysql.connector
from datetime import date

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# ==========================================
# ENDPOINTS ORIGINALES (MAPA E IA)
# ==========================================

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

# ==========================================
# NUEVOS ENDPOINTS (CONEXIÓN LORCA BD)
# ==========================================

# --- 1. Endpoint para guardar el tejado seleccionado ---

class DatosTejadoUsuario(BaseModel):
    id_usuario: str
    lat: float
    lon: float
    area_m2: float
    orientacion: str

@app.post("/seleccionar-tejado")
async def seleccionar_tejado(datos: DatosTejadoUsuario):
    area_util = round(datos.area_m2 * 0.85, 2)
    
    try:
        conn = mysql.connector.connect(
            host="10.151.30.2", user="bd_rvm_solar_map",
            password="Mar123Qz", database="bd_rvm_solar_map"
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id_zona FROM dim_zona 
            WHERE %s BETWEEN sur_lat_min AND norte_lat_max 
            AND %s BETWEEN oeste_lon_min AND este_lon_max
        """, (datos.lat, datos.lon))
        res_zona = cursor.fetchone()
        id_zona = res_zona[0] if res_zona else "tile_generico"

        query = """
            INSERT INTO fact_tejados_detectados 
            (id_usuario, id_zona, latitud, longitud, area_util_m2, orientacion_principal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (datos.id_usuario, id_zona, datos.lat, datos.lon, area_util, datos.orientacion))
        
        conn.commit()
        return {"status": "success", "usuario": datos.id_usuario}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# --- 2. Endpoint para el registro de usuarios web ---

class FormularioRegistro(BaseModel):
    id_usuario: str
    nombre: str
    apellidos: str
    email: str
    password: str
    cp_usuario: int
    fecha_nacimiento: str
    grupo_usuario: str = "Residencial"

@app.post("/registro-usuario")
async def registrar_usuario(datos: FormularioRegistro):
    password_hash = hashlib.sha256(datos.password.encode()).hexdigest()
    fecha_hoy = date.today().strftime('%Y-%m-%d')

    try:
        conn = mysql.connector.connect(
            host="10.151.30.2", user="bd_rvm_solar_map",
            password="Mar123Qz", database="bd_rvm_solar_map"
        )
        cursor = conn.cursor()
        
        conn.start_transaction()

        sql_app = """
            INSERT INTO app_credenciales_usuario 
            (id_usuario, nombre, apellidos, email, password_hash)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql_app, (datos.id_usuario, datos.nombre, datos.apellidos, datos.email, password_hash))

        sql_dw = """
            INSERT INTO dim_usuario 
            (id_usuario, fecha_nacimiento, cp_usuario, grupo_usuario, fecha_primer_acceso)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql_dw, (datos.id_usuario, datos.fecha_nacimiento, datos.cp_usuario, datos.grupo_usuario, fecha_hoy))

        conn.commit()
        return {"status": "success", "mensaje": "Usuario registrado correctamente."}

    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en el registro: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()