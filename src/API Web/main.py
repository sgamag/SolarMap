"""
API Web - Endpoints de SolarMap.

Se ejecuta en el puerto 8002 y gestiona:
  - Autenticacion (registro/login)
  - Guardado de tejados detectados en fact_tejados_detectados
  - Generacion de informes PDF por tejado

Endpoints:
  - POST /api/auth/register    : crea un usuario nuevo
  - POST /api/auth/login       : verifica credenciales
  - GET  /api/auth/check-email : comprueba si un email ya existe
  - POST /api/tejados/guardar  : guarda un tejado seleccionado en BD
  - GET  /api/informe/{id}     : genera y descarga el informe PDF del tejado
  - GET  /api/health           : healthcheck
"""

import io
import os
import uuid
import bcrypt
import mysql.connector
from datetime import date, datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
)

# ----------------------------------------------------------------------------
# Configuracion
# ----------------------------------------------------------------------------

DB_HOST = os.getenv("DB_HOST", "10.151.30.2")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "bd_rvm_solar_map")
DB_PASS = os.getenv("DB_PASS", "Mar123Qz")
DB_NAME = os.getenv("DB_NAME", "bd_rvm_solar_map")

# Ruta al logo — ponlo en la misma carpeta que main.py
LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo_solarmap.png")

# Colores corporativos SolarMap
SOLAR_ORANGE = colors.HexColor("#F5A623")
SOLAR_DARK   = colors.HexColor("#1a1a2e")
SOLAR_GREY   = colors.HexColor("#f5f5f5")
SOLAR_BORDER = colors.HexColor("#e0e0e0")

# Factor multiplicador por id_caracteristica (mismo que DAX)
FACTOR_MULTIPLICADOR = {
    1: 0.95, 2: 0.85, 3: 0.85, 4: 0.75, 5: 0.75, 6: 0.60,
    7: 1.10, 8: 1.05, 9: 1.05, 10: 0.90, 11: 0.90, 12: 0.70,
    13: 1.20, 14: 1.15, 15: 1.15, 16: 1.00, 17: 1.00, 18: 0.80,
}

# Factor de eficiencia por escenario (mismo que DAX)
FACTOR_ESCENARIO = {
    "Pesimista": 0.65,
    "Neutro":    0.70,
    "Optimista": 0.75,
}

# ----------------------------------------------------------------------------
# Helpers BD
# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------
# Orientaciones
# ----------------------------------------------------------------------------

ORIENTACIONES_SIMPLES = {"Sur", "Sureste", "Suroeste", "Este", "Oeste", "Norte"}
ORIENTACIONES_COMBINADAS_VALIDAS = {"Norte-Sur", "Este-Oeste"}
ORIENTACIONES_VALIDAS_FACT = ORIENTACIONES_SIMPLES | ORIENTACIONES_COMBINADAS_VALIDAS


def normalizar_orientacion_label(orientacion: str | None, angulo: float | None) -> str:
    if not orientacion:
        orientacion = ""
    orientacion = orientacion.strip()

    if orientacion in ORIENTACIONES_VALIDAS_FACT:
        return orientacion

    mapeo_combinadas = {
        "Sur-Norte": "Norte-Sur", "Oeste-Este": "Este-Oeste",
        "Sureste-Noroeste": "Sureste", "Noroeste-Sureste": "Sureste",
        "Suroeste-Noreste": "Suroeste", "Noreste-Suroeste": "Suroeste",
        "Norte-Este": "Este", "Este-Norte": "Este",
        "Norte-Oeste": "Oeste", "Oeste-Norte": "Oeste",
        "Norte-Sureste": "Sureste", "Norte-Suroeste": "Suroeste",
        "Sur-Este": "Sureste", "Este-Sur": "Sureste",
        "Sur-Oeste": "Suroeste", "Oeste-Sur": "Suroeste",
        "Sur-Sureste": "Sur", "Sur-Suroeste": "Sur",
    }
    if orientacion in mapeo_combinadas:
        return mapeo_combinadas[orientacion]

    if angulo is not None:
        a = angulo % 360
        if a < 22.5 or a >= 337.5: return "Norte"
        if a < 67.5:  return "Sureste"
        if a < 112.5: return "Este"
        if a < 157.5: return "Sureste"
        if a < 202.5: return "Sur"
        if a < 247.5: return "Suroeste"
        if a < 292.5: return "Oeste"
        return "Suroeste"

    s = orientacion.lower()
    if "sur"   in s: return "Sur"
    if "este"  in s: return "Este"
    if "oeste" in s: return "Oeste"
    if "norte" in s: return "Norte"
    return "Sur"


def orientacion_para_caracteristica(orientacion_label: str) -> str:
    if orientacion_label == "Norte-Sur":  return "Sur"
    if orientacion_label == "Este-Oeste": return "Este"
    return orientacion_label


# ----------------------------------------------------------------------------
# Helpers PDF
# ----------------------------------------------------------------------------

def _calcular_fila(panel, escenario, area_util, horas_sol, id_caracteristica, potencial_medio):
    """Calcula todos los KPIs para una combinación panel × escenario."""
    factor_tejado  = FACTOR_MULTIPLICADOR.get(id_caracteristica, 1.0)
    potencial      = round(10 * potencial_medio + 5 * factor_tejado, 2)
    paneles        = int(area_util / panel["area_panel_m2"]) if panel["area_panel_m2"] else 0
    factor_esc     = FACTOR_ESCENARIO.get(escenario["nombre_escenario"], 0.70)
    produccion_kwh = round(paneles * panel["potencia_w"] * horas_sol * factor_esc / 1000, 2)
    inversion      = round(panel["precio_unitario_euros"] * paneles + panel["coste_instalacion_fijo_euros"], 2)
    ahorro_anyo    = round(produccion_kwh * escenario["precio_medio_luz"], 2)
    roi            = round(ahorro_anyo / inversion * 100, 2) if inversion else 0
    amortizacion   = round(inversion / ahorro_anyo, 1) if ahorro_anyo else 0
    return {
        "panel": panel["modelo_panel"], "escenario": escenario["nombre_escenario"],
        "paneles": paneles, "kwh": produccion_kwh, "inversion": inversion,
        "ahorro": ahorro_anyo, "roi": roi, "amortizacion": amortizacion,
        "potencial": potencial,
    }


def _build_pdf(tejado, paneles, escenarios):
    """Construye el PDF y devuelve un BytesIO listo para streamear."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
    )
    styles = getSampleStyleSheet()
    story  = []

    # ── Cabecera ──────────────────────────────────────────────────────────────
    logo = Image(LOGO_PATH, width=2*cm, height=2*cm) if os.path.exists(LOGO_PATH) else Spacer(2*cm, 2*cm)

    titulo_style = ParagraphStyle(
        "Titulo", fontSize=20, fontName="Helvetica-Bold",
        textColor=SOLAR_DARK, leading=24, alignment=TA_LEFT,
    )
    subtitulo_style = ParagraphStyle(
        "Subtitulo", fontSize=10, fontName="Helvetica",
        textColor=colors.HexColor("#666666"), leading=14,
    )
    header_table = Table(
        [[logo, [
            Paragraph("Informe de Análisis Solar", titulo_style),
            Paragraph(f"Tejado #{tejado['id_tejado']} · {tejado['id_zona']}", subtitulo_style),
        ]]],
        colWidths=[2.5*cm, 14*cm]
    )
    header_table.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, 0),   8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=SOLAR_ORANGE, spaceAfter=12))

    # ── Datos del tejado ──────────────────────────────────────────────────────
    seccion_style = ParagraphStyle(
        "Seccion", fontSize=12, fontName="Helvetica-Bold",
        textColor=SOLAR_DARK, spaceBefore=8, spaceAfter=6,
    )
    story.append(Paragraph("Datos del Tejado", seccion_style))

    datos_tejado = [
        ["Campo", "Valor"],
        ["ID Tejado",             str(tejado["id_tejado"])],
        ["Zona",                  tejado["id_zona"]],
        ["Orientación principal", tejado["orientacion_principal"]],
        ["Área útil",             f"{tejado['area_util_m2']} m2"],
        ["Área total bruta",      f"{tejado['area_total_bruta_m2']} m2"],
        ["Horas de sol",          f"{tejado['horas_sol']} h/año"],
        ["Potencial de la zona",  str(tejado["potencial_medio"])],
    ]
    t_datos = Table(datos_tejado, colWidths=[6*cm, 10*cm])
    t_datos.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  SOLAR_ORANGE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, SOLAR_GREY]),
        ("GRID",          (0, 0), (-1, -1), 0.5, SOLAR_BORDER),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_datos)
    story.append(Spacer(1, 14))

    # ── Tabla resultados panel × escenario ────────────────────────────────────
    story.append(Paragraph("Resultados por Panel y Escenario Económico", seccion_style))
    story.append(Paragraph(
        "Cálculos con el número máximo de paneles instalables según el área útil disponible.",
        ParagraphStyle("nota", fontSize=8, textColor=colors.HexColor("#888888"), spaceAfter=6),
    ))

    cabecera = [
        "Panel", "Escenario", "Paneles", "Producción\n(kWh/año)",
        "Inversión\n(€)", "Ahorro\n1er año (€)", "ROI (%)", "Amortiz.\n(años)"
    ]
    tabla_filas = [cabecera]
    for f in [_calcular_fila(p, e, tejado["area_util_m2"], tejado["horas_sol"],
                              tejado["id_caracteristica"], tejado["potencial_medio"])
              for p in paneles for e in escenarios]:
        tabla_filas.append([
            f["panel"], f["escenario"], str(f["paneles"]),
            f"{f['kwh']:,.0f}", f"{f['inversion']:,.0f} €",
            f"{f['ahorro']:,.0f} €", f"{f['roi']} %", f"{f['amortizacion']} años",
        ])

    col_widths = [3.5*cm, 2.2*cm, 1.6*cm, 2.4*cm, 2.4*cm, 2.6*cm, 1.8*cm, 2.0*cm]
    t_res = Table(tabla_filas, colWidths=col_widths, repeatRows=1)
    n_esc = len(escenarios)
    row_styles = [
        ("BACKGROUND",    (0, 0), (-1, 0),  SOLAR_ORANGE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, SOLAR_BORDER),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (2, 1), (-1, -1), "CENTER"),
        ("FONTNAME",      (0, 1), (1, -1),  "Helvetica-Bold"),
    ]
    for i in range(len(paneles)):
        row_start = 1 + i * n_esc
        row_end   = row_start + n_esc - 1
        bg = SOLAR_GREY if i % 2 == 0 else colors.white
        row_styles.append(("BACKGROUND", (0, row_start), (-1, row_end), bg))
    t_res.setStyle(TableStyle(row_styles))
    story.append(t_res)

    # ── Pie ───────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=SOLAR_BORDER))
    story.append(Paragraph(
        "Informe generado automáticamente por SolarMap · Universidad Europea de Madrid · Datos provisionales",
        ParagraphStyle("pie", fontSize=7, textColor=colors.HexColor("#aaaaaa"),
                       alignment=TA_CENTER, spaceBefore=6),
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------

app = FastAPI(title="SolarMap API Web", version="1.5")

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
# Endpoints — Auth
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
            id_usuario=id_usuario, nombre=datos.nombre, apellidos=datos.apellidos,
            email=datos.email, fechaNacimiento=datos.fechaNacimiento, codigoPostal=datos.codigoPostal,
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
            id_usuario=fila["id_usuario"], nombre=fila["nombre"], apellidos=fila["apellidos"],
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


# ----------------------------------------------------------------------------
# Endpoints — Tejados
# ----------------------------------------------------------------------------

@app.post("/api/tejados/guardar", response_model=TejadoOut)
def guardar_tejado(datos: TejadoIn):
    if datos.area_m2 <= 0:
        raise HTTPException(status_code=400, detail="area_m2 debe ser positivo")

    area_bruta = round(datos.area_m2, 2)
    area_util  = round(area_bruta * 0.40, 2)
    tamano     = clasificar_tamano(area_util)

    orientacion_guardar       = normalizar_orientacion_label(datos.orientation_label, datos.orientation_angle_degrees)
    orientacion_caracteristica = orientacion_para_caracteristica(orientacion_guardar)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT 1 FROM dim_usuario WHERE id_usuario = %s LIMIT 1", (datos.id_usuario,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        cursor.execute(
            """SELECT id_zona, potencial_medio FROM dim_zona
               WHERE %s BETWEEN sur_lat_min AND norte_lat_max
                 AND %s BETWEEN oeste_lon_min AND este_lon_max
               LIMIT 1""",
            (datos.lat, datos.lon),
        )
        zona = cursor.fetchone()
        if zona is None:
            raise HTTPException(status_code=404,
                detail=f"No se encontro una zona para las coordenadas ({datos.lat}, {datos.lon})")
        id_zona       = zona["id_zona"]
        potencial_zona = zona["potencial_medio"]

        cursor.execute(
            """SELECT id_caracteristica FROM dim_caracteristicas_tejado
               WHERE tamaño_categoria = %s AND orientacion_principal = %s LIMIT 1""",
            (tamano, orientacion_caracteristica),
        )
        carac = cursor.fetchone()
        if carac is None:
            raise HTTPException(status_code=500,
                detail=f"No se encontro caracteristica para tamaño={tamano} orientacion={orientacion_caracteristica}")
        id_caracteristica = carac["id_caracteristica"]

        cursor.execute(
            """INSERT INTO fact_tejados_detectados
               (id_zona, id_caracteristica, latitud, longitud,
                area_total_bruta_m2, area_util_m2,
                orientacion_grados, orientacion_principal, potencial_final)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (id_zona, id_caracteristica, datos.lat, datos.lon,
             area_bruta, area_util, datos.orientation_angle_degrees,
             orientacion_guardar, potencial_zona),
        )
        id_tejado = cursor.lastrowid
        conn.commit()

        return TejadoOut(
            id_tejado=id_tejado, id_zona=id_zona, id_caracteristica=id_caracteristica,
            area_total_bruta_m2=area_bruta, area_util_m2=area_util,
            orientacion_principal=orientacion_guardar, potencial_final=potencial_zona,
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


# ----------------------------------------------------------------------------
# Endpoints — Informe PDF
# ----------------------------------------------------------------------------

@app.get("/api/informe/{id_tejado}")
def generar_informe(id_tejado: int):
    """Genera y descarga el informe PDF completo de un tejado."""
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT f.id_tejado, f.orientacion_principal, f.area_util_m2,
                      f.area_total_bruta_m2, f.id_zona, f.id_caracteristica,
                      f.potencial_final, z.potencial_medio, c.horas_sol
               FROM fact_tejados_detectados f
               JOIN dim_zona z                 ON z.id_zona = f.id_zona
               JOIN dim_caracteristicas_tejado c ON c.id_caracteristica = f.id_caracteristica
               WHERE f.id_tejado = %s LIMIT 1""",
            (id_tejado,),
        )
        tejado = cursor.fetchone()
        if not tejado:
            raise HTTPException(status_code=404, detail="Tejado no encontrado")

        cursor.execute(
            """SELECT modelo_panel, area_panel_m2, potencia_w,
                      precio_unitario_euros, coste_instalacion_fijo_euros
               FROM dim_panel"""
        )
        paneles = cursor.fetchall()

        cursor.execute(
            "SELECT nombre_escenario, precio_medio_luz FROM dim_escenario_economico"
        )
        escenarios = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    buffer = _build_pdf(tejado, paneles, escenarios)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="informe_tejado_{id_tejado}.pdf"'},
    )