"""
Procesamiento físico del potencial solar horario (0–1) desde HDFS.

Entrada:
  /datalake/datos/bronze/csv/tile01/2013/2013_04.csv

Salida:
  /datalake/datos/silver/Clima/tile01/2013/2013_04_potencial_v1.csv

Optimizado:
  - Lista bronze una sola vez
  - Lista silver una sola vez
  - Calcula pendientes en memoria
  - Procesa por lotes tile/año
  - 3 workers en paralelo
"""

import pandas as pd
from pathlib import Path
import subprocess
import tempfile
import shutil
import re
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# CONFIGURACIÓN
# ============================================================

CONTENEDOR = "solarmap_namenode"

RUTA_BRONZE = "/datalake/datos/bronze/csv"
RUTA_SILVER = "/datalake/datos/silver/Clima"

TMP_CONTENEDOR = "/tmp/etl_clima"

NUM_WORKERS = 3

VERSION_MODELO = "v1"


# ============================================================
# PATRONES
# ============================================================

PATRON_TILE = re.compile(r"^tile\d{2}$")
PATRON_ANIO = re.compile(r"^\d{4}$")
PATRON_CSV = re.compile(r"^\d{4}_\d{2}\.csv$")

lock_print = threading.Lock()


def log(*args):
    with lock_print:
        print(*args)


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


# ============================================================
# COMANDOS DOCKER
# ============================================================

def ejecutar(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def docker_exec(cmd):
    r = ejecutar(["docker", "exec", CONTENEDOR, "bash", "-c", cmd])
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout


def copiar_desde_contenedor(origen, destino: Path):
    destino.parent.mkdir(parents=True, exist_ok=True)
    ejecutar(["docker", "cp", f"{CONTENEDOR}:{origen}", str(destino)])


def copiar_a_contenedor(origen: Path, destino):
    ejecutar(["docker", "cp", str(origen), f"{CONTENEDOR}:{destino}"])


# ============================================================
# HDFS
# ============================================================

def listar_hdfs(path):
    r = ejecutar(["docker", "exec", CONTENEDOR, "bash", "-c", f'hdfs dfs -find "{path}" -name "*.csv"'])
    if r.returncode != 0:
        return []
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def existe_hdfs(path):
    r = ejecutar(["docker", "exec", CONTENEDOR, "bash", "-c", f'hdfs dfs -test -e "{path}"'])
    return r.returncode == 0


def mkdir_hdfs(path):
    docker_exec(f'hdfs dfs -mkdir -p "{path}"')


def descargar_hdfs(hdfs_path, local_path, tmp_dir):
    nombre = local_path.name
    tmp = f"{tmp_dir}/{nombre}"

    docker_exec(f'mkdir -p "{tmp_dir}"')
    docker_exec(f'hdfs dfs -get "{hdfs_path}" "{tmp}"')

    copiar_desde_contenedor(tmp, local_path)
    docker_exec(f'rm -f "{tmp}"')


def subir_hdfs(local_path, hdfs_path, tmp_dir):
    nombre = local_path.name
    tmp = f"{tmp_dir}/{nombre}"

    mkdir_hdfs(hdfs_path.rsplit("/", 1)[0])

    copiar_a_contenedor(local_path, tmp)
    docker_exec(f'hdfs dfs -put "{tmp}" "{hdfs_path}"')
    docker_exec(f'rm -f "{tmp}"')


# ============================================================
# FILTROS
# ============================================================

def es_valido(path):
    if "potencial" in path.lower():
        return False

    partes = path.replace(RUTA_BRONZE + "/", "").split("/")
    if len(partes) != 3:
        return False

    tile, anio, fichero = partes

    return (
        PATRON_TILE.match(tile)
        and PATRON_ANIO.match(anio)
        and PATRON_CSV.match(fichero)
    )


def salida_hdfs(path):
    tile, anio, fichero = path.replace(RUTA_BRONZE + "/", "").split("/")
    base = fichero.replace(".csv", "")
    return f"{RUTA_SILVER}/{tile}/{anio}/{base}_potencial_{VERSION_MODELO}.csv"


# ============================================================
# PREPARAR TRABAJOS
# ============================================================

def obtener_trabajos():
    log("Leyendo bronze...")
    bronze = listar_hdfs(RUTA_BRONZE)

    validos = [p for p in bronze if es_valido(p)]

    log("Leyendo silver...")
    silver = set(listar_hdfs(RUTA_SILVER))

    trabajos = defaultdict(list)

    for entrada in validos:
        salida = salida_hdfs(entrada)

        if salida in silver:
            continue

        tile, anio, _ = entrada.replace(RUTA_BRONZE + "/", "").split("/")
        trabajos[(tile, anio)].append((entrada, salida))

    return trabajos


# ============================================================
# PROCESAMIENTO
# ============================================================

def procesar_csv(entrada: Path, salida: Path):
    df = pd.read_csv(entrada)
    df.columns = [c.strip() for c in df.columns]

    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce")
    df = df.dropna(subset=["valid_time"])

    df["ssrd_kWhm2"] = pd.to_numeric(df["ssrd_kWhm2"], errors="coerce").clip(lower=0)
    df["t2m_C"] = pd.to_numeric(df["t2m_C"], errors="coerce")
    df["tcc"] = pd.to_numeric(df["tcc"], errors="coerce").clip(0, 1)

    df["month"] = df["valid_time"].dt.month

    df["rad_norm"] = (df["ssrd_kWhm2"] / REF_RADIACION).clip(0, 1)
    df["pen_nube"] = (1 - df["tcc"]) ** ALFA_NUBES

    exceso = (df["t2m_C"] - TEMP_BASE).clip(lower=0)
    df["pen_temp"] = (1 - BETA_TEMP * exceso).clip(lower=0)

    max_horas = max(HORAS_SOL.values())
    df["horas_norm"] = df["month"].map(lambda m: HORAS_SOL[int(m)] / max_horas)

    df["potencial_0_1"] = (
        df["rad_norm"] *
        df["pen_nube"] *
        df["pen_temp"] *
        df["horas_norm"]
    ).clip(0, 1)

    salida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(salida, index=False)


# ============================================================
# LOTES
# ============================================================

def procesar_lote(tile, anio, lista):
    log(f"Procesando lote {tile}/{anio}")

    tmp_local = Path(tempfile.mkdtemp())
    tmp_cont = f"{TMP_CONTENEDOR}/{tile}_{anio}_{VERSION_MODELO}"

    procesados = 0

    try:
        for entrada, salida in lista:
            nombre = entrada.split("/")[-1]

            local_in = tmp_local / nombre
            local_out = tmp_local / nombre.replace(".csv", f"_potencial_{VERSION_MODELO}.csv")

            descargar_hdfs(entrada, local_in, tmp_cont)
            procesar_csv(local_in, local_out)
            subir_hdfs(local_out, salida, tmp_cont)

            procesados += 1

        return procesados

    finally:
        shutil.rmtree(tmp_local, ignore_errors=True)
        docker_exec(f'rm -rf "{tmp_cont}"')


# ============================================================
# MAIN
# ============================================================

def main():
    trabajos = obtener_trabajos()

    if not trabajos:
        print("Nada que procesar")
        return

    total = 0

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futuros = {
            executor.submit(procesar_lote, tile, anio, lista): (tile, anio)
            for (tile, anio), lista in trabajos.items()
        }

        for i, futuro in enumerate(as_completed(futuros), 1):
            tile, anio = futuros[futuro]
            res = futuro.result()

            print(f"[{i}/{len(futuros)}] {tile}/{anio} -> {res} archivos")
            total += res

    print("\nTOTAL PROCESADOS:", total)


if __name__ == "__main__":
    main()