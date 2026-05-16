import csv
import io
import os
from urllib.parse import quote, urlparse, urlunparse

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


def construir_url_hdfs(ruta: str, operacion: str) -> str:
    ruta_codificada = quote(ruta, safe="/")
    return f"{WEBHDFS_BASE}{ruta_codificada}?op={operacion}&user.name=root"


def adaptar_url_datanode(url: str) -> str:
    """
    Si ejecutas dentro de Docker, no hace falta cambiar nada.
    Si ejecutas desde Windows, puedes definir:
      HDFS_DATANODE_PUBLIC=localhost:9864
    """
    datanode_publico = os.getenv("HDFS_DATANODE_PUBLIC")

    if not datanode_publico:
        return url

    parsed = urlparse(url)
    return urlunparse(parsed._replace(netloc=datanode_publico))


def existe_hdfs(ruta: str) -> bool:
    respuesta = requests.get(construir_url_hdfs(ruta, "GETFILESTATUS"))
    return respuesta.status_code == 200


def leer_texto_hdfs(ruta_hdfs: str) -> str:
    respuesta = requests.get(
        construir_url_hdfs(ruta_hdfs, "OPEN"),
        allow_redirects=False
    )

    if respuesta.status_code == 307:
        url_descarga = respuesta.headers.get("Location")

        if not url_descarga:
            raise RuntimeError(f"No se recibió Location para descargar {ruta_hdfs}")

        url_descarga = adaptar_url_datanode(url_descarga)

        respuesta_archivo = requests.get(url_descarga)

        if respuesta_archivo.status_code != 200:
            raise RuntimeError(
                f"No se pudo leer {ruta_hdfs}\n{respuesta_archivo.text}"
            )

        return respuesta_archivo.text

    if respuesta.status_code == 200:
        return respuesta.text

    raise RuntimeError(f"No se pudo abrir {ruta_hdfs}\n{respuesta.text}")

def cargar_precios_desde_hdfs():
    if not existe_hdfs(RUTA_CSV_SILVER):
        raise RuntimeError(f"No existe el CSV en HDFS: {RUTA_CSV_SILVER}")

    print(f"Leyendo CSV desde HDFS: {RUTA_CSV_SILVER}")

    contenido = leer_texto_hdfs(RUTA_CSV_SILVER)

    datos = []
    lector = csv.DictReader(io.StringIO(contenido))

    columnas_necesarias = {
        "anyo",
        "precio_neutro",
        "precio_optimista",
        "precio_pesimista"
    }

    if not columnas_necesarias.issubset(set(lector.fieldnames or [])):
        raise RuntimeError(
            f"CSV incompleto. Columnas encontradas: {lector.fieldnames}"
        )

    for fila in lector:
        anyo = int(fila["anyo"])
        precio_neutro = float(fila["precio_neutro"])
        precio_optimista = float(fila["precio_optimista"])
        precio_pesimista = float(fila["precio_pesimista"])

        datos.append((
            anyo,
            precio_neutro,
            precio_optimista,
            precio_pesimista
        ))

    return datos


def insertar_en_mysql(datos_a_insertar):
    print("Cargando precios de luz en MySQL...")

    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

    cursor = conn.cursor()

    try:
        cursor.execute("TRUNCATE TABLE dim_precio_luz;")

        sql = """
            INSERT INTO dim_precio_luz 
            (anyo, precio_estimado_neutro, precio_estimado_optimista, precio_estimado_pesimista)
            VALUES (%s, %s, %s, %s)
        """

        cursor.executemany(sql, datos_a_insertar)
        conn.commit()

        print(f"Listo, {cursor.rowcount} años de proyecciones cargados.")

    except Exception as e:
        conn.rollback()
        print(f"Error durante la carga en MySQL: {e}")
        raise

    finally:
        cursor.close()
        conn.close()


def main():
    datos_a_insertar = cargar_precios_desde_hdfs()

    if not datos_a_insertar:
        print("No hay datos para insertar.")
        return

    insertar_en_mysql(datos_a_insertar)


if __name__ == "__main__":
    main() 