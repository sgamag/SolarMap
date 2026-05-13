from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse
import os
import requests


# ============================================================
# EDITA SOLO ESTO
# ============================================================

RUTA_LOCAL_ARCHIVO = Path(
    os.getenv("RUTA_DATALAKE", "")
) / "data" / "precios_luz_proyeccion.csv"

RUTA_HDFS_DESTINO = "/datalake/datos/silver/luz/combinado/precios_luz_proyeccion.csv"

SOBREESCRIBIR = False

# ============================================================

WEBHDFS_BASE = os.getenv(
    "WEBHDFS_BASE",
    "http://localhost:9870/webhdfs/v1"
)

HDFS_DATANODE_PUBLIC = os.getenv(
    "HDFS_DATANODE_PUBLIC",
    "localhost:9864"
)


def construir_url_hdfs(ruta: str, operacion: str) -> str:
    ruta_codificada = quote(ruta, safe="/")
    return f"{WEBHDFS_BASE}{ruta_codificada}?op={operacion}&user.name=root"


def adaptar_url_datanode(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(netloc=HDFS_DATANODE_PUBLIC))


def existe_hdfs(ruta: str) -> bool:
    r = requests.get(construir_url_hdfs(ruta, "GETFILESTATUS"))
    return r.status_code == 200


def crear_directorio_hdfs(ruta: str) -> None:
    r = requests.put(construir_url_hdfs(ruta, "MKDIRS"))

    if r.status_code not in (200, 201):
        raise RuntimeError(f"No se pudo crear directorio HDFS: {ruta}\n{r.text}")


def subir_archivo_hdfs(ruta_local: Path, ruta_hdfs: str) -> None:
    if not ruta_local.exists():
        raise FileNotFoundError(f"No existe el archivo local: {ruta_local}")

    if existe_hdfs(ruta_hdfs):
        if not SOBREESCRIBIR:
            print(f"[SKIP] Ya existe en HDFS: {ruta_hdfs}")
            return

    carpeta_hdfs = ruta_hdfs.rsplit("/", 1)[0]
    crear_directorio_hdfs(carpeta_hdfs)

    overwrite = "true" if SOBREESCRIBIR else "false"
    url_create = construir_url_hdfs(ruta_hdfs, "CREATE") + f"&overwrite={overwrite}"

    respuesta = requests.put(url_create, allow_redirects=False)

    if respuesta.status_code != 307:
        raise RuntimeError(f"No se pudo iniciar subida a HDFS:\n{respuesta.text}")

    url_subida = respuesta.headers.get("Location")

    if not url_subida:
        raise RuntimeError("No se recibió Location del DataNode.")

    url_subida = adaptar_url_datanode(url_subida)

    with open(ruta_local, "rb") as archivo:
        respuesta_subida = requests.put(url_subida, data=archivo)

    if respuesta_subida.status_code not in (200, 201):
        raise RuntimeError(f"No se pudo subir el archivo:\n{respuesta_subida.text}")

    print(f"[OK] Subido a HDFS: {ruta_hdfs}")


def main():
    print("Subiendo archivo final de luz al Data Lake...")
    print(f"Local: {RUTA_LOCAL_ARCHIVO}")
    print(f"HDFS : {RUTA_HDFS_DESTINO}")

    subir_archivo_hdfs(RUTA_LOCAL_ARCHIVO, RUTA_HDFS_DESTINO)

    print("FIN")


if __name__ == "__main__":
    main()