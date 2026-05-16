"""
API Web - Endpoints de SolarMap.

Se ejecuta en el puerto 8002 y gestiona:
  - Autenticacion (registro/login)
  - Guardado de tejados detectados en fact_tejados_detectados

Endpoints:
  - POST /api/auth/register    : crea un usuario nuevo
  - POST /api/auth/login       : verifica credenciales
  - GET  /api/auth/check-email : comprueba si un email ya existe
  - POST /api/tejados/guardar  : guarda un tejado seleccionado en BD
  - GET  /api/health           : healthcheck
"""

import os
import uuid
import bcrypt
import mysql.connector
from datetime import date, datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# ----------------------------------------------------------------------------
# Configuracion
# ----------------------------------------------------------------------------

DB_HOST = os.getenv("DB_HOST", "10.151.30.2")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "bd_rvm_solar_map")
DB_PASS = os.getenv("DB_PASS", "Mar123Qz")
DB_NAME = os.getenv("DB_NAME", "bd_rvm_solar_map")


def get_db():
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME,
        ssl_disabled=True, autocommit=False,
    )


def calcular_grupo_usuario(fecha_nacimiento: date) -> str:
    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year - (
        (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )
    if edad < 35:
        return "Joven"
    if edad <= 55:
        return "Adulto"
    return "Senior"


def generar_id_usuario() -> str:
    return f"USR_{uuid.uuid4().hex[:12].upper()}"


def clasificar_tamano(area_util_m2: float) -> str:
    if area_util_m2 < 30:
        return "Pequeño"
    if area_util_m2 > 70:
        return "Grande"
    return "Mediano"


# Orientaciones simples (las unicas que existen en dim_caracteristicas_tejado)
ORIENTACIONES_SIMPLES = {
    "Sur", "Sureste", "Suroeste", "Este", "Oeste", "Norte"
}

# Orientaciones combinadas que vienen en fact_tejados_detectados ya
ORIENTACIONES_COMBINADAS_VALIDAS = {
    "Norte-Sur", "Este-Oeste"
}

# Conjunto completo de orientaciones aceptadas para guardar en fact_tejados_detectados
ORIENTACIONES_VALIDAS_FACT = ORIENTACIONES_SIMPLES | ORIENTACIONES_COMBINADAS_VALIDAS


def normalizar_orientacion_label(orientacion: str | None, angulo: float | None) -> str:
    """
    Devuelve la orientacion tal cual se guardara en fact_tejados_detectados.orientacion_principal.

    Acepta como validas las 6 simples + Norte-Sur + Este-Oeste (las 8 que ya existen
    en fact_tejados_detectados segun los datos sinteticos).

    Si viene algo raro, la mapea a la mejor orientacion simple por aproximacion al angulo.
    """
    if not orientacion:
        orientacion = ""
    orientacion = orientacion.strip()

    # Si ya es valida (simple o combinada conocida), la dejamos tal cual
    if orientacion in ORIENTACIONES_VALIDAS_FACT:
        return orientacion

    # Mapeo de combinadas raras a una valida
    mapeo_combinadas = {
        "Sur-Norte":          "Norte-Sur",
        "Oeste-Este":         "Este-Oeste",
        "Sureste-Noroeste":   "Sureste",
        "Noroeste-Sureste":   "Sureste",
        "Suroeste-Noreste":   "Suroeste",
        "Noreste-Suroeste":   "Suroeste",
        "Norte-Este":         "Este",
        "Este-Norte":         "Este",
        "Norte-Oeste":        "Oeste",
        "Oeste-Norte":        "Oeste",
        "Norte-Sureste":      "Sureste",
        "Norte-Suroeste":     "Suroeste",
        "Sur-Este":           "Sureste",
        "Este-Sur":           "Sureste",
        "Sur-Oeste":          "Suroeste",
        "Oeste-Sur":          "Suroeste",
        "Sur-Sureste":        "Sur",
        "Sur-Suroeste":       "Sur",
    }
    if orientacion in mapeo_combinadas:
        return mapeo_combinadas[orientacion]

    # Fallback por angulo
    if angulo is not None:
        a = angulo % 360
        if a < 22.5 or a >= 337.5:
            return "Norte"
        if a < 67.5:
            return "Sureste"
        if a < 112.5:
            return "Este"
        if a < 157.5:
            return "Sureste"
        if a < 202.5:
            return "Sur"
        if a < 247.5:
            return "Suroeste"
        if a < 292.5:
            return "Oeste"
        return "Suroeste"

    # Ultimo recurso
    s = orientacion.lower()
    if "sur" in s:
        return "Sur"
    if "este" in s:
        return "Este"
    if "oeste" in s:
        return "Oeste"
    if "norte" in s:
        return "Norte"

    return "Sur"


def orientacion_para_caracteristica(orientacion_label: str) -> str:
    """
    Dada la orientacion final (que puede ser combinada como Norte-Sur),
    devuelve la orientacion simple que se usa para buscar id_caracteristica
    en dim_caracteristicas_tejado.

    Las combinadas se mapean a la mejor vertiente solar:
      Norte-Sur  -> Sur   (priorizamos sur, mas radiacion)
      Este-Oeste -> Este  (equivalentes; elegimos Este consistentemente)
    """
    if orientacion_label == "Norte-Sur":
        return "Sur"
    if orientacion_label == "Este-Oeste":
        return "Este"
    return orientacion_label


# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------

app = FastAPI(title="SolarMap API Web", version="1.4")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------------
# Modelos Pydantic
# ----------------------------------------------------------------------------

class RegistroIn(BaseModel):
    nombre: str
    apellidos: str
    email: EmailStr
    password: str
    fechaNacimiento: str
    codigoPostal: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UsuarioOut(BaseModel):
    id_usuario: str
    nombre: str
    apellidos: str
    email: str
    fechaNacimiento: str
    codigoPostal: str


class TejadoIn(BaseModel):
    id_usuario: str
    lat: float
    lon: float
    area_m2: float
    orientation_angle_degrees: float | None = None
    orientation_label: str | None = None


class TejadoOut(BaseModel):
    id_tejado: int
    id_zona: str
    id_caracteristica: int
    area_total_bruta_m2: float
    area_util_m2: float
    orientacion_principal: str
    potencial_final: float | None


# ----------------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------------

@app.get("/api/health")
def health():
    try:
        conn = get_db()
        conn.close()
        return {"status": "ok", "db": "connected"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=503, detail=f"DB no disponible: {err}")


@app.get("/api/auth/check-email")
def check_email(email: str):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM app_credenciales_usuario WHERE email = %s LIMIT 1", (email,))
        return {"exists": cursor.fetchone() is not None}
    finally:
        cursor.close()
        conn.close()


@app.post("/api/auth/register", response_model=UsuarioOut)
def register(datos: RegistroIn):
    try:
        fecha_nac = datetime.strptime(datos.fechaNacimiento, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha de nacimiento invalida (formato yyyy-mm-dd)")

    if not datos.codigoPostal.isdigit() or len(datos.codigoPostal) != 5:
        raise HTTPException(status_code=400, detail="Codigo postal invalido (5 digitos)")

    password_hash = bcrypt.hashpw(datos.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    id_usuario = generar_id_usuario()
    grupo = calcular_grupo_usuario(fecha_nac)
    fecha_hoy = date.today()

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM app_credenciales_usuario WHERE email = %s LIMIT 1", (datos.email,))
        if cursor.fetchone() is not None:
            raise HTTPException(status_code=409, detail="El email ya esta registrado")

        cursor.execute(
            """INSERT INTO dim_usuario
               (id_usuario, fecha_nacimiento, cp_usuario, grupo_usuario, fecha_primer_acceso)
               VALUES (%s, %s, %s, %s, %s)""",
            (id_usuario, fecha_nac, int(datos.codigoPostal), grupo, fecha_hoy),
        )
        cursor.execute(
            """INSERT INTO app_credenciales_usuario
               (id_usuario, nombre, apellidos, email, password_hash)
               VALUES (%s, %s, %s, %s, %s)""",
            (id_usuario, datos.nombre, datos.apellidos, datos.email, password_hash),
        )
        conn.commit()

        return UsuarioOut(
            id_usuario=id_usuario,
            nombre=datos.nombre,
            apellidos=datos.apellidos,
            email=datos.email,
            fechaNacimiento=datos.fechaNacimiento,
            codigoPostal=datos.codigoPostal,
        )
    except HTTPException:
        conn.rollback()
        raise
    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en BD: {err}")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/auth/login", response_model=UsuarioOut)
def login(datos: LoginIn):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT c.id_usuario, c.nombre, c.apellidos, c.email, c.password_hash,
                      u.fecha_nacimiento, u.cp_usuario
               FROM app_credenciales_usuario c
               LEFT JOIN dim_usuario u ON u.id_usuario = c.id_usuario
               WHERE c.email = %s LIMIT 1""",
            (datos.email,),
        )
        fila = cursor.fetchone()

        if fila is None:
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

        hash_guardado = fila["password_hash"].encode("utf-8")
        try:
            ok = bcrypt.checkpw(datos.password.encode("utf-8"), hash_guardado)
        except ValueError:
            ok = False

        if not ok:
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

        return UsuarioOut(
            id_usuario=fila["id_usuario"],
            nombre=fila["nombre"],
            apellidos=fila["apellidos"],
            email=fila["email"],
            fechaNacimiento=fila["fecha_nacimiento"].isoformat() if fila["fecha_nacimiento"] else "",
            codigoPostal=str(fila["cp_usuario"]) if fila["cp_usuario"] else "",
        )
    except HTTPException:
        raise
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error en BD: {err}")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/tejados/guardar", response_model=TejadoOut)
def guardar_tejado(datos: TejadoIn):
    """
    Guarda un tejado seleccionado en fact_tejados_detectados.
    
    - orientacion_principal: se guarda tal cual viene del modelo (puede ser Norte-Sur, Este-Oeste, etc.)
    - id_caracteristica:    busca con la version simple de la orientacion (porque
                            dim_caracteristicas_tejado solo tiene 6 simples)
    """
    if datos.area_m2 <= 0:
        raise HTTPException(status_code=400, detail="area_m2 debe ser positivo")

    area_bruta = round(datos.area_m2, 2)
    area_util = round(area_bruta * 0.40, 2)
    tamano = clasificar_tamano(area_util)

    # Orientacion que se guarda en fact (puede ser Norte-Sur, Este-Oeste, etc.)
    orientacion_guardar = normalizar_orientacion_label(datos.orientation_label, datos.orientation_angle_degrees)
    # Orientacion simple para buscar id_caracteristica
    orientacion_caracteristica = orientacion_para_caracteristica(orientacion_guardar)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Validar usuario
        cursor.execute("SELECT 1 FROM dim_usuario WHERE id_usuario = %s LIMIT 1", (datos.id_usuario,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # 2. Buscar zona
        cursor.execute(
            """SELECT id_zona, potencial_medio
               FROM dim_zona
               WHERE %s BETWEEN sur_lat_min  AND norte_lat_max
                 AND %s BETWEEN oeste_lon_min AND este_lon_max
               LIMIT 1""",
            (datos.lat, datos.lon),
        )
        zona = cursor.fetchone()
        if zona is None:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontro una zona para las coordenadas ({datos.lat}, {datos.lon})"
            )
        id_zona = zona["id_zona"]
        potencial_zona = zona["potencial_medio"]

        # 3. Buscar id_caracteristica con la orientacion simple
        cursor.execute(
            """SELECT id_caracteristica
               FROM dim_caracteristicas_tejado
               WHERE tamaño_categoria = %s AND orientacion_principal = %s
               LIMIT 1""",
            (tamano, orientacion_caracteristica),
        )
        carac = cursor.fetchone()
        if carac is None:
            raise HTTPException(
                status_code=500,
                detail=f"No se encontro caracteristica para tamaño={tamano} orientacion={orientacion_caracteristica}"
            )
        id_caracteristica = carac["id_caracteristica"]

        # 4. Insertar - guardamos la orientacion ORIGINAL (Norte-Sur, Este-Oeste, etc.)
        cursor.execute(
            """INSERT INTO fact_tejados_detectados
               (id_zona, id_caracteristica, latitud, longitud,
                area_total_bruta_m2, area_util_m2,
                orientacion_grados, orientacion_principal, potencial_final)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                id_zona, id_caracteristica, datos.lat, datos.lon,
                area_bruta, area_util,
                datos.orientation_angle_degrees,
                orientacion_guardar,            # <-- aqui guardamos la real
                potencial_zona,
            ),
        )
        id_tejado = cursor.lastrowid
        conn.commit()

        return TejadoOut(
            id_tejado=id_tejado,
            id_zona=id_zona,
            id_caracteristica=id_caracteristica,
            area_total_bruta_m2=area_bruta,
            area_util_m2=area_util,
            orientacion_principal=orientacion_guardar,
            potencial_final=potencial_zona,
        )

    except HTTPException:
        conn.rollback()
        raise
    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error en BD: {err}")
    finally:
        cursor.close()
        conn.close()