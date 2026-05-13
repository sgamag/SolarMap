import csv
import io
import os
from urllib.parse import quote

import requests
import mysql.connector

WEBHDFS_BASE = os.getenv(
    "WEBHDFS_BASE",
    "http://namenode:9870/webhdfs/v1"
)

RUTA_CSV_SILVER = "/datalake/datos/silver/luz/combinado/precios_luz_proyeccion.csv"

DB_HOST = os.getenv("DB_HOST", "10.151.30.2")
DB_USER = os.getenv("DB_USER", "bd_rvm_solar_map")
DB_PASS = os.getenv("DB_PASS", "Mar123Qz")
DB_NAME = os.getenv("DB_NAME", "bd_rvm_solar_map")

TABLA_DESTINO = "precio_luz"


def construir_url_hdfs(ruta: str, operacion: str) -> str:
    ruta_codificada = quote(ruta, safe="/")
    return f"{WEBHDFS_BASE}{ruta_codificada}?op={operacion}&user.name=root"


def existe_hdfs(ruta: str) -> bool:
    respuesta = requests.get(construir_url_hdfs(ruta, "GETFILESTATUS"))
    return respuesta.status_code == 200


def leer_texto_hdfs(ruta_hdfs: str) -> str:
    respuesta = requests.get(
        construir_url_hdfs(ruta_hdfs, "OPEN"),
        allow_redirects=True
    )

    if respuesta.status_code != 200:
        raise RuntimeError(
            f"No se pudo leer el archivo en HDFS: {ruta_hdfs}\n"
            f"Status: {respuesta.status_code}\n"
            f"Respuesta: {respuesta.text}"
        )

    return respuesta.text


def cargar_precios_desde_hdfs():
    if not existe_hdfs(RUTA_CSV_SILVER):
        raise FileNotFoundError(f"No existe el archivo en HDFS: {RUTA_CSV_SILVER}")

    print(f"Leyendo precios desde HDFS: {RUTA_CSV_SILVER}")

    contenido = leer_texto_hdfs(RUTA_CSV_SILVER)

    lector = csv.DictReader(io.StringIO(contenido), delimiter=";")

    columnas_obligatorias = {"anio", "mes", "precio_luz", "escenario"}
    columnas_csv = set(lector.fieldnames or [])

    if not columnas_obligatorias.issubset(columnas_csv):
        raise ValueError(
            f"CSV incompleto.\n"
            f"Columnas esperadas: {columnas_obligatorias}\n"
            f"Columnas encontradas: {columnas_csv}"
        )

    datos = []

    for fila in lector:
        try:
            anio = int(fila["anio"])
            mes = int(fila["mes"])
            precio_luz = float(fila["precio_luz"])
            escenario = fila["escenario"].strip()

            datos.append((anio, mes, precio_luz, escenario))

        except Exception as exc:
            print(f"[AVISO] Fila saltada por error: {fila} -> {exc}")

    return datos


def cargar_en_mysql(datos_a_insertar):
    print("Cargando precios de luz en SQL...")

    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

    cursor = conn.cursor()

    try:
        cursor.execute(f"TRUNCATE TABLE {TABLA_DESTINO};")

        sql = f"""
            INSERT INTO {TABLA_DESTINO}
            (año, mes, precio_luz, escenario)
            VALUES (%s, %s, %s, %s)
        """

        cursor.executemany(sql, datos_a_insertar)
        conn.commit()

        print(f"Listo, {cursor.rowcount} registros cargados en {TABLA_DESTINO}.")

    except Exception as e:
        conn.rollback()
        print(f"Error durante la carga en SQL: {e}")
        raise

    finally:
        cursor.close()
        conn.close()

def main():
    datos = cargar_precios_desde_hdfs()

    if not datos:
        print("No hay datos para insertar.")
        return

    print(f"Registros preparados: {len(datos)}")
    cargar_en_mysql(datos)


if __name__ == "__main__":
    main()