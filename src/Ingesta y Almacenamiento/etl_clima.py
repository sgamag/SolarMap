import csv
import io
import os
import re
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urlparse, urlunparse

import requests
import mysql.connector


# ============================================================
# CONFIGURACIÓN
# ============================================================

WEBHDFS_BASE = os.getenv(
    "WEBHDFS_BASE",
    "http://solarmap_namenode:9870/webhdfs/v1"
)

RUTA_CLIMA_SILVER = "/datalake/datos/silver/Clima"

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))

DB_HOST = os.getenv("DB_HOST", "10.151.30.2")
DB_USER = os.getenv("DB_USER", "bd_rvm_solar_map")
DB_PASS = os.getenv("DB_PASS", "Mar123Qz")
DB_NAME = os.getenv("DB_NAME", "bd_rvm_solar_map")

PATRON_CSV_POTENCIAL = re.compile(
    r"^/datalake/datos/silver/Clima/tile\d{2}/\d{4}/\d{4}_\d{2}_potencial\.csv$"
)


# ============================================================
# WEBHDFS
# ============================================================

def construir_url_hdfs(ruta: str, operacion: str) -> str:
    ruta_codificada = quote(ruta, safe="/")
    return f"{WEBHDFS_BASE}{ruta_codificada}?op={operacion}&user.name=root"


def adaptar_url_datanode(url: str) -> str:
    datanode_publico = os.getenv("HDFS_DATANODE_PUBLIC")

    if not datanode_publico:
        return url

    parsed = urlparse(url)
    return urlunparse(parsed._replace(netloc=datanode_publico))


def existe_hdfs(ruta: str) -> bool:
    r = requests.get(construir_url_hdfs(ruta, "GETFILESTATUS"))
    return r.status_code == 200


def listar_csv_hdfs(ruta_base: str) -> list[str]:
    encontrados = []

    def recorrer(ruta_actual: str):
        r = requests.get(construir_url_hdfs(ruta_actual, "LISTSTATUS"))

        if r.status_code != 200:
            return

        items = r.json()["FileStatuses"]["FileStatus"]

        for item in items:
            nombre = item["pathSuffix"]
            tipo = item["type"]
            ruta_item = f"{ruta_actual.rstrip('/')}/{nombre}"

            if tipo == "DIRECTORY":
                recorrer(ruta_item)
            elif tipo == "FILE" and ruta_item.endswith(".csv"):
                encontrados.append(ruta_item)

    recorrer(ruta_base)
    return encontrados


def leer_csv_hdfs(ruta_hdfs: str) -> str:
    session = requests.Session()

    r = session.get(
        construir_url_hdfs(ruta_hdfs, "OPEN"),
        allow_redirects=False
    )

    if r.status_code == 307:
        url_descarga = r.headers.get("Location")

        if not url_descarga:
            raise RuntimeError(f"No se recibió Location para descargar {ruta_hdfs}")

        url_descarga = adaptar_url_datanode(url_descarga)
        r2 = session.get(url_descarga)

        if r2.status_code != 200:
            raise RuntimeError(f"No se pudo leer {ruta_hdfs}\n{r2.text}")

        return r2.text

    if r.status_code == 200:
        return r.text

    raise RuntimeError(f"No se pudo abrir {ruta_hdfs}\n{r.text}")


# ============================================================
# PROCESADO DE CSV
# ============================================================

def extraer_tile_desde_ruta(ruta_hdfs: str) -> str:
    partes = ruta_hdfs.split("/")
    for parte in partes:
        if parte.startswith("tile"):
            return parte
    return ""


def procesar_csv_clima(ruta_hdfs: str):
    """
    Procesa un CSV de silver y devuelve acumulados parciales:
      - potencial por zona
      - clima mensual por zona/mes
    """
    texto_csv = leer_csv_hdfs(ruta_hdfs)

    lector = csv.DictReader(io.StringIO(texto_csv))

    potencial_global_zona = defaultdict(lambda: {
        "suma_potencial": 0.0,
        "contador": 0
    })

    clima_mensual_zona = {}

    tile_fallback = extraer_tile_desde_ruta(ruta_hdfs)

    filas_validas = 0

    for fila in lector:
        try:
            id_zona = fila.get("tile_id") or tile_fallback

            if not id_zona:
                continue

            valid_time = fila["valid_time"]
            mes = int(valid_time[5:7])

            radiacion = float(fila["ssrd_kWhm2"])
            nubosidad = float(fila["tcc"])
            temperatura = float(fila["t2m_C"])
            potencial = float(fila["potencial_0_1"])

        except Exception:
            continue

        potencial_global_zona[id_zona]["suma_potencial"] += potencial
        potencial_global_zona[id_zona]["contador"] += 1

        clave_mensual = (id_zona, mes)

        if clave_mensual not in clima_mensual_zona:
            clima_mensual_zona[clave_mensual] = {
                "suma_rad": 0.0,
                "suma_nub": 0.0,
                "suma_temp": 0.0,
                "max_temp": temperatura,
                "min_temp": temperatura,
                "contador": 0
            }

        grupo = clima_mensual_zona[clave_mensual]

        grupo["suma_rad"] += radiacion
        grupo["suma_nub"] += nubosidad
        grupo["suma_temp"] += temperatura
        grupo["contador"] += 1
        grupo["max_temp"] = max(grupo["max_temp"], temperatura)
        grupo["min_temp"] = min(grupo["min_temp"], temperatura)

        filas_validas += 1

    return potencial_global_zona, clima_mensual_zona, filas_validas


def combinar_acumulados(destino_potencial, destino_mensual, parcial_potencial, parcial_mensual):
    for id_zona, valores in parcial_potencial.items():
        destino_potencial[id_zona]["suma_potencial"] += valores["suma_potencial"]
        destino_potencial[id_zona]["contador"] += valores["contador"]

    for clave, valores in parcial_mensual.items():
        if clave not in destino_mensual:
            destino_mensual[clave] = valores.copy()
        else:
            grupo = destino_mensual[clave]
            grupo["suma_rad"] += valores["suma_rad"]
            grupo["suma_nub"] += valores["suma_nub"]
            grupo["suma_temp"] += valores["suma_temp"]
            grupo["contador"] += valores["contador"]
            grupo["max_temp"] = max(grupo["max_temp"], valores["max_temp"])
            grupo["min_temp"] = min(grupo["min_temp"], valores["min_temp"])


# ============================================================
# CARGA SQL
# ============================================================

def generar_datos_insertar(potencial_global_zona, clima_mensual_zona):
    datos_a_insertar = []

    for (id_zona, mes), valores_mensuales in sorted(clima_mensual_zona.items()):
        cantidad = valores_mensuales["contador"]

        if cantidad == 0:
            continue

        datos_potencial = potencial_global_zona[id_zona]

        if datos_potencial["contador"] == 0:
            continue

        media_rad = valores_mensuales["suma_rad"] / cantidad
        media_nub = valores_mensuales["suma_nub"] / cantidad
        media_temp = valores_mensuales["suma_temp"] / cantidad
        media_potencial = datos_potencial["suma_potencial"] / datos_potencial["contador"]

        datos_a_insertar.append((
            id_zona,
            mes,
            media_rad,
            media_nub,
            media_temp,
            valores_mensuales["max_temp"],
            valores_mensuales["min_temp"],
            media_potencial
        ))

    return datos_a_insertar


def cargar_en_mysql(datos_a_insertar):
    print("\n2. Conectando a MySQL y cargando fact_clima_agregado_mensual...")

    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

    cursor = conn.cursor()

    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE fact_clima_agregado_mensual;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        sql = """
            INSERT INTO fact_clima_agregado_mensual 
            (id_zona, mes, radiacion_media_mes, nubosidad_media_mes, 
             temperatura_media_mes, temperatura_maxima_mes, temperatura_minima_mes, potencial_medio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.executemany(sql, datos_a_insertar)
        conn.commit()

        print(f"-> Éxito: {cursor.rowcount} registros insertados correctamente.")

    except Exception as e:
        conn.rollback()
        print(f"-> Error durante la inserción en base de datos: {e}")
        raise

    finally:
        cursor.close()
        conn.close()


# ============================================================
# MAIN
# ============================================================

def transformar_y_cargar_clima():
    print("1. Leyendo datos desde Silver en HDFS...")

    if not existe_hdfs(RUTA_CLIMA_SILVER):
        raise RuntimeError(f"No existe la ruta en HDFS: {RUTA_CLIMA_SILVER}")

    archivos = listar_csv_hdfs(RUTA_CLIMA_SILVER)

    archivos_validos = [
        ruta for ruta in archivos
        if PATRON_CSV_POTENCIAL.match(ruta)
    ]

    print(f"-> CSV encontrados en Silver: {len(archivos)}")
    print(f"-> CSV válidos de clima     : {len(archivos_validos)}")
    print(f"-> Workers                 : {MAX_WORKERS}")

    potencial_global_zona = defaultdict(lambda: {
        "suma_potencial": 0.0,
        "contador": 0
    })

    clima_mensual_zona = {}

    filas_totales = 0
    errores = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futuros = {
            executor.submit(procesar_csv_clima, ruta): ruta
            for ruta in archivos_validos
        }

        for i, futuro in enumerate(as_completed(futuros), start=1):
            ruta = futuros[futuro]

            try:
                parcial_potencial, parcial_mensual, filas_validas = futuro.result()

                combinar_acumulados(
                    potencial_global_zona,
                    clima_mensual_zona,
                    parcial_potencial,
                    parcial_mensual
                )

                filas_totales += filas_validas

            except Exception as exc:
                errores += 1
                print(f"[ERROR] {ruta}")
                print(exc)

            if i % 100 == 0:
                print(f"-> Procesados {i}/{len(archivos_validos)} CSV...")

    print("\n-> Lectura finalizada.")
    print(f"-> Filas válidas procesadas: {filas_totales}")
    print(f"-> Errores de fichero      : {errores}")

    datos_a_insertar = generar_datos_insertar(
        potencial_global_zona,
        clima_mensual_zona
    )

    print(f"-> Cálculos listos: {len(datos_a_insertar)} filas agregadas preparadas.")

    if not datos_a_insertar:
        print("No hay datos para insertar.")
        return

    cargar_en_mysql(datos_a_insertar)


if __name__ == "__main__":
    transformar_y_cargar_clima()