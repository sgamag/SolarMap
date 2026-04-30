"""
ETL clima desde HDFS usando WebHDFS + Polars.

Entrada:
  /datalake/datos/bronze/csv/tile01/2013/2013_04.csv

Salida:
  /datalake/datos/silver/Clima/tile01/2013/2013_04_potencial.csv

Características:
- No usa docker exec.
- Pensado para ejecutarse dentro del contenedor etl_clima.
- Lista bronze una vez.
- Lista silver una vez.
- Procesa solo lo pendiente.
- Procesa por lotes tile/año.
- Usa 3 workers.
"""

from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
import tempfile
import shutil
import threading
import re
import requests
import polars as pl
import os


# ============================================================
# CONFIGURACIÓN
# ============================================================


WEBHDFS_BASE = os.getenv(
    "WEBHDFS_BASE",
    "http://namenode:9870/webhdfs/v1"
)
RUTA_BRONZE = "/datalake/datos/bronze/csv"
RUTA_SILVER = "/datalake/datos/silver/Clima"

NUM_WORKERS = 3

PATRON_TILE = re.compile(r"^tile\d{2}$")
PATRON_ANIO = re.compile(r"^\d{4}$")
PATRON_CSV = re.compile(r"^\d{4}_\d{2}\.csv$")

lock_print = threading.Lock()


# ============================================================
# PARÁMETROS DEL MODELO
# ============================================================

HORAS_SOL = {
    1: 9.3,  2: 10.0, 3: 11.9, 4: 13.3,
    5: 14.5, 6: 16.8, 7: 15.7, 8: 15.1,
    9: 13.0, 10: 12.4, 11: 10.8, 12: 9.0
}

ALFA_NUBES = 0.90
TEMP_BASE = 25.0
BETA_TEMP = 0.004
REF_RADIACION = 1.0


def log(*args):
    with lock_print:
        print(*args)


# ============================================================
# WEBHDFS
# ============================================================

def construir_url_hdfs(ruta: str, operacion: str) -> str:
    ruta_codificada = quote(ruta, safe="/")
    return f"{WEBHDFS_BASE}{ruta_codificada}?op={operacion}&user.name=root"


def existe_hdfs(ruta: str) -> bool:
    respuesta = requests.get(construir_url_hdfs(ruta, "GETFILESTATUS"))
    return respuesta.status_code == 200


def crear_directorio_hdfs(ruta: str) -> None:
    respuesta = requests.put(construir_url_hdfs(ruta, "MKDIRS"))

    if respuesta.status_code not in (200, 201):
        raise RuntimeError(f"No se pudo crear directorio HDFS: {ruta}\n{respuesta.text}")


def listar_csv_hdfs(ruta: str) -> list[str]:
    encontrados = []

    def recorrer(ruta_actual: str):
        respuesta = requests.get(construir_url_hdfs(ruta_actual, "LISTSTATUS"))

        if respuesta.status_code != 200:
            return

        estados = respuesta.json()["FileStatuses"]["FileStatus"]

        for item in estados:
            nombre = item["pathSuffix"]
            tipo = item["type"]
            ruta_item = f"{ruta_actual.rstrip('/')}/{nombre}"

            if tipo == "DIRECTORY":
                recorrer(ruta_item)
            elif tipo == "FILE" and ruta_item.endswith(".csv"):
                encontrados.append(ruta_item)

    recorrer(ruta)
    return encontrados


def descargar_hdfs(ruta_hdfs: str, ruta_local: Path) -> None:
    ruta_local.parent.mkdir(parents=True, exist_ok=True)

    respuesta = requests.get(
        construir_url_hdfs(ruta_hdfs, "OPEN"),
        allow_redirects=True
    )

    if respuesta.status_code != 200:
        raise RuntimeError(f"No se pudo descargar {ruta_hdfs}\n{respuesta.text}")

    ruta_local.write_bytes(respuesta.content)


def subir_hdfs(ruta_local: Path, ruta_hdfs: str) -> None:
    carpeta_hdfs = ruta_hdfs.rsplit("/", 1)[0]
    crear_directorio_hdfs(carpeta_hdfs)

    url_creacion = construir_url_hdfs(ruta_hdfs, "CREATE") + "&overwrite=false"

    respuesta = requests.put(url_creacion, allow_redirects=False)

    if respuesta.status_code not in (307, 201):
        raise RuntimeError(f"No se pudo iniciar subida HDFS: {ruta_hdfs}\n{respuesta.text}")

    url_subida = respuesta.headers.get("Location")

    if not url_subida:
        raise RuntimeError(f"No se recibió Location para subir {ruta_hdfs}")

    with open(ruta_local, "rb") as fichero:
        respuesta_subida = requests.put(url_subida, data=fichero)

    if respuesta_subida.status_code not in (200, 201):
        raise RuntimeError(f"No se pudo subir {ruta_hdfs}\n{respuesta_subida.text}")


# ============================================================
# RUTAS Y TRABAJOS
# ============================================================

def es_csv_bronze_valido(ruta_csv: str) -> bool:
    if "potencial" in ruta_csv.lower():
        return False

    relativo = ruta_csv.replace(RUTA_BRONZE + "/", "")
    partes = relativo.split("/")

    if len(partes) != 3:
        return False

    tile, anio, fichero = partes

    return bool(
        PATRON_TILE.match(tile)
        and PATRON_ANIO.match(anio)
        and PATRON_CSV.match(fichero)
    )


def ruta_salida_para_entrada(ruta_entrada: str) -> str:
    relativo = ruta_entrada.replace(RUTA_BRONZE + "/", "")
    tile, anio, fichero = relativo.split("/")

    base = fichero.replace(".csv", "")
    fichero_salida = f"{base}_potencial.csv"

    return f"{RUTA_SILVER}/{tile}/{anio}/{fichero_salida}"


def obtener_tile_anio(ruta_entrada: str) -> tuple[str, str]:
    relativo = ruta_entrada.replace(RUTA_BRONZE + "/", "")
    tile, anio, _ = relativo.split("/")
    return tile, anio


def cargar_trabajos_pendientes() -> dict[tuple[str, str], list[tuple[str, str]]]:
    log("Listando CSV de bronze...")
    csv_bronze = listar_csv_hdfs(RUTA_BRONZE)
    csv_validos = [ruta for ruta in csv_bronze if es_csv_bronze_valido(ruta)]

    log(f"CSV encontrados en bronze: {len(csv_bronze)}")
    log(f"CSV válidos en bronze    : {len(csv_validos)}")

    log("Listando CSV existentes en silver...")
    csv_silver = set(listar_csv_hdfs(RUTA_SILVER))

    log(f"CSV existentes en silver : {len(csv_silver)}")

    trabajos = defaultdict(list)
    saltados = 0

    for entrada in csv_validos:
        salida = ruta_salida_para_entrada(entrada)

        if salida in csv_silver:
            saltados += 1
            continue

        tile, anio = obtener_tile_anio(entrada)
        trabajos[(tile, anio)].append((entrada, salida))

    pendientes = sum(len(v) for v in trabajos.values())

    log(f"CSV ya procesados / skip : {saltados}")
    log(f"CSV pendientes          : {pendientes}")
    log(f"Lotes pendientes        : {len(trabajos)}")

    return dict(trabajos)


# ============================================================
# PROCESAMIENTO CON POLARS
# ============================================================

def expresion_horas_norm():
    horas_max = max(HORAS_SOL.values())

    expresion = None

    for mes, horas in HORAS_SOL.items():
        valor = horas / horas_max

        if expresion is None:
            expresion = pl.when(pl.col("month") == mes).then(pl.lit(valor))
        else:
            expresion = expresion.when(pl.col("month") == mes).then(pl.lit(valor))

    return expresion.otherwise(None).alias("horas_norm")


def procesar_csv(entrada: Path, salida: Path) -> None:
    df = pl.read_csv(entrada)

    columnas_renombradas = {
        columna: columna.strip()
        for columna in df.columns
        if columna != columna.strip()
    }

    if columnas_renombradas:
        df = df.rename(columnas_renombradas)

    requeridas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}

    if not requeridas.issubset(set(df.columns)):
        raise ValueError(f"CSV incompleto: {entrada}")

    df = df.with_columns([
        pl.col("valid_time").str.to_datetime(strict=False).alias("valid_time"),
        pl.col("ssrd_kWhm2").cast(pl.Float64, strict=False).clip(0, None).alias("ssrd_kWhm2"),
        pl.col("t2m_C").cast(pl.Float64, strict=False).alias("t2m_C"),
        pl.col("tcc").cast(pl.Float64, strict=False).clip(0, 1).alias("tcc"),
    ])

    df = df.drop_nulls(["valid_time"])

    df = df.with_columns(
        pl.col("valid_time").dt.month().alias("month")
    ).sort("valid_time")

    df = df.with_columns([
        (pl.col("ssrd_kWhm2") / REF_RADIACION).clip(0, 1).alias("rad_norm"),
        ((1 - pl.col("tcc")).clip(0, None).pow(ALFA_NUBES)).alias("pen_nube"),
        (
            pl.lit(1) -
            BETA_TEMP * ((pl.col("t2m_C") - TEMP_BASE).clip(0, None))
        ).clip(0, None).alias("pen_temp"),
        expresion_horas_norm(),
    ])

    df = df.with_columns(
        (
            pl.col("rad_norm")
            * pl.col("pen_nube")
            * pl.col("pen_temp")
            * pl.col("horas_norm")
        ).clip(0, 1).alias("potencial_0_1")
    )

    for columna in ["rad_norm", "pen_nube", "pen_temp", "horas_norm", "potencial_0_1"]:
        df = df.with_columns(pl.col(columna).round(4).alias(columna))

    columnas_salida = ["valid_time"]

    for columna in ["tile_id", "latitude", "longitude"]:
        if columna in df.columns:
            columnas_salida.append(columna)

    columnas_salida += [
        "ssrd_kWhm2", "t2m_C", "tcc",
        "rad_norm", "pen_nube", "pen_temp",
        "horas_norm", "potencial_0_1",
    ]

    df_salida = df.select(columnas_salida)

    df_salida = df_salida.with_columns(
        pl.col("valid_time").dt.strftime("%Y-%m-%d %H:%M:%S").alias("valid_time")
    )

    salida.parent.mkdir(parents=True, exist_ok=True)
    df_salida.write_csv(salida)


# ============================================================
# LOTES
# ============================================================

def procesar_lote(tile: str, anio: str, trabajos_lote: list[tuple[str, str]]) -> tuple[int, int]:
    log(f"\n===== LOTE {tile}/{anio} | pendientes={len(trabajos_lote)} =====")

    carpeta_temporal = Path(tempfile.mkdtemp(prefix=f"etl_{tile}_{anio}_"))

    procesados = 0
    errores = 0

    try:
        for ruta_entrada_hdfs, ruta_salida_hdfs in trabajos_lote:
            nombre_entrada = ruta_entrada_hdfs.rsplit("/", 1)[-1]
            nombre_salida = nombre_entrada.replace(".csv", "_potencial.csv")

            entrada_local = carpeta_temporal / nombre_entrada
            salida_local = carpeta_temporal / nombre_salida

            try:
                descargar_hdfs(ruta_entrada_hdfs, entrada_local)
                procesar_csv(entrada_local, salida_local)
                subir_hdfs(salida_local, ruta_salida_hdfs)

                log("[SUBIDO]", ruta_salida_hdfs)
                procesados += 1

            except Exception as exc:
                log(f"[ERROR] {tile}/{anio} -> {ruta_entrada_hdfs}")
                log(exc)
                errores += 1

        return procesados, errores

    finally:
        shutil.rmtree(carpeta_temporal, ignore_errors=True)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    if not existe_hdfs(RUTA_BRONZE):
        print(f"No existe la ruta de entrada en HDFS: {RUTA_BRONZE}")
        return

    crear_directorio_hdfs(RUTA_SILVER)

    trabajos = cargar_trabajos_pendientes()

    if not trabajos:
        print("No hay trabajos pendientes.")
        return

    lotes = sorted(trabajos.keys())

    print("==============================================")
    print(f"Entrada HDFS : {RUTA_BRONZE}")
    print(f"Salida HDFS  : {RUTA_SILVER}")
    print(f"Lotes        : {len(lotes)}")
    print(f"Workers      : {NUM_WORKERS}")
    print("==============================================")

    total_procesados = 0
    total_errores = 0

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futuros = {
            executor.submit(
                procesar_lote,
                tile,
                anio,
                trabajos[(tile, anio)]
            ): (tile, anio)
            for tile, anio in lotes
        }

        for i, futuro in enumerate(as_completed(futuros), start=1):
            tile, anio = futuros[futuro]

            procesados, errores = futuro.result()

            total_procesados += procesados
            total_errores += errores

            print(
                f"[{i}/{len(lotes)}] Terminado {tile}/{anio} "
                f"-> procesados={procesados}, errores={errores}"
            )

    print("\n============== RESUMEN FINAL ==============")
    print(f"Procesados nuevos: {total_procesados}")
    print(f"Errores          : {total_errores}")
    print("FIN")


if __name__ == "__main__":
    main()