import csv
import io
import os
import re
from collections import defaultdict
from urllib.parse import quote, urlparse, urlunparse
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def procesar_csv_potencial(ruta_hdfs: str):
    """
    Procesa un CSV y devuelve el acumulado de potencial por tile.
    """
    texto_csv = leer_csv_hdfs(ruta_hdfs)
    lector = csv.DictReader(io.StringIO(texto_csv))

    potencial_por_zona = defaultdict(lambda: {
        "suma_potencial": 0.0,
        "contador": 0
    })

    tile_fallback = extraer_tile_desde_ruta(ruta_hdfs)
    filas_validas = 0

    for fila in lector:
        try:
            id_zona = fila.get("tile_id") or tile_fallback

            if not id_zona:
                continue

            potencial = float(fila["potencial_0_1"])

        except Exception:
            continue

        potencial_por_zona[id_zona]["suma_potencial"] += potencial
        potencial_por_zona[id_zona]["contador"] += 1

        filas_validas += 1

    return potencial_por_zona, filas_validas


def combinar_potenciales(destino, parcial):
    for id_zona, valores in parcial.items():
        destino[id_zona]["suma_potencial"] += valores["suma_potencial"]
        destino[id_zona]["contador"] += valores["contador"]


def generar_datos_update(potencial_global_zona):
    datos_update = []

    for id_zona, valores in sorted(potencial_global_zona.items()):
        contador = valores["contador"]

        if contador == 0:
            continue

        potencial_medio = valores["suma_potencial"] / contador

        datos_update.append((
            potencial_medio,
            id_zona
        ))

    return datos_update


# ============================================================
# CARGA SQL
# ============================================================

def actualizar_potencial_en_dim_zona(datos_update):
    print("\n2. Conectando a MySQL y actualizando dim_zona.potencial_medio...")

    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

    cursor = conn.cursor()

    try:
        sql = """
            UPDATE dim_zona
            SET potencial_medio = %s
            WHERE id_zona = %s
        """

        cursor.executemany(sql, datos_update)
        conn.commit()

        print(f"-> Éxito: {cursor.rowcount} zonas actualizadas correctamente.")

    except Exception as e:
        conn.rollback()
        print(f"-> Error durante la actualización en base de datos: {e}")
        raise

    finally:
        cursor.close()
        conn.close()


# ============================================================
# MAIN
# ============================================================

def transformar_y_cargar_potencial_zona():
    print("1. Leyendo potencial desde Silver en HDFS...")

    if not existe_hdfs(RUTA_CLIMA_SILVER):
        raise RuntimeError(f"No existe la ruta en HDFS: {RUTA_CLIMA_SILVER}")

    archivos = listar_csv_hdfs(RUTA_CLIMA_SILVER)

    archivos_validos = [
        ruta for ruta in archivos
        if PATRON_CSV_POTENCIAL.match(ruta)
    ]

    print(f"-> CSV encontrados en Silver: {len(archivos)}")
    print(f"-> CSV válidos de potencial : {len(archivos_validos)}")
    print(f"-> Workers                 : {MAX_WORKERS}")

    potencial_global_zona = defaultdict(lambda: {
        "suma_potencial": 0.0,
        "contador": 0
    })

    filas_totales = 0
    errores = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futuros = {
            executor.submit(procesar_csv_potencial, ruta): ruta
            for ruta in archivos_validos
        }

        for i, futuro in enumerate(as_completed(futuros), start=1):
            ruta = futuros[futuro]

            try:
                parcial_potencial, filas_validas = futuro.result()

                combinar_potenciales(
                    potencial_global_zona,
                    parcial_potencial
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

    datos_update = generar_datos_update(potencial_global_zona)

    print(f"-> Cálculos listos: {len(datos_update)} zonas preparadas para actualizar.")

    if not datos_update:
        print("No hay datos para actualizar.")
        return

    actualizar_potencial_en_dim_zona(datos_update)


if __name__ == "__main__":
    transformar_y_cargar_potencial_zona()