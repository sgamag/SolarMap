"""
Procesamiento físico del potencial solar horario (0–1) desde HDFS.

Entrada:
  /datalake/datos/bronze/csv/tile01/2013/2013_04.csv

Salida:
  /datalake/datos/silver/Clima/tile01/2013/2013_04_potencial.csv

Optimizado:
  - Procesamiento por lotes tile/año
  - 3 workers en paralelo
  - Skip rápido usando listado inicial de silver
  - Temporales únicos por lote
"""

import pandas as pd
from pathlib import Path
import subprocess
import tempfile
import shutil
import sys
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


# =======================================================================
# CONFIGURACIÓN
# =======================================================================

NOMBRE_CONTENEDOR = "solarmap_namenode"

HDFS_BRONZE_CSV = "/datalake/datos/bronze/csv"
HDFS_SILVER_CLIMA = "/datalake/datos/silver/Clima"

RUTA_TMP_CONTENEDOR = "/tmp/etl_clima"

MAX_WORKERS = 3

TILE_PATTERN = re.compile(r"^tile\d{2}$")
YEAR_PATTERN = re.compile(r"^\d{4}$")
CSV_PATTERN = re.compile(r"^\d{4}_\d{2}\.csv$")

print_lock = threading.Lock()


# =======================================================================
# PARÁMETROS FÍSICOS DEL MODELO
# =======================================================================

HORAS_SOL_POR_MES = {
    1: 9.3,  2: 10.0, 3: 11.9, 4: 13.3,
    5: 14.5, 6: 16.8, 7: 15.7, 8: 15.1,
    9: 13.0, 10: 12.4, 11: 10.8, 12: 9.0
}

ALFA_NUBES = 0.90
TEMP_BASE = 25.0
BETA_TEMP = 0.004
REF_RADIACION = 1.0


# =======================================================================
# LOG SEGURO PARA VARIOS WORKERS
# =======================================================================

def log(*args):
    with print_lock:
        print(*args)


# =======================================================================
# UTILIDADES DOCKER / HDFS
# =======================================================================

def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def docker_exec(cmd: str) -> str:
    result = run(["docker", "exec", NOMBRE_CONTENEDOR, "bash", "-c", cmd])

    if result.returncode != 0:
        raise RuntimeError(
            f"[ERROR docker exec]\n"
            f"Comando: {cmd}\n"
            f"STDERR: {result.stderr}"
        )

    return result.stdout


def docker_cp_from(container_path: str, local_path: Path) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)

    result = run([
        "docker", "cp",
        f"{NOMBRE_CONTENEDOR}:{container_path}",
        str(local_path)
    ])

    if result.returncode != 0:
        raise RuntimeError(
            f"[ERROR docker cp FROM]\n"
            f"Origen contenedor: {container_path}\n"
            f"Destino local: {local_path}\n"
            f"STDERR: {result.stderr}"
        )


def docker_cp_to(local_path: Path, container_path: str) -> None:
    result = run([
        "docker", "cp",
        str(local_path),
        f"{NOMBRE_CONTENEDOR}:{container_path}"
    ])

    if result.returncode != 0:
        raise RuntimeError(
            f"[ERROR docker cp TO]\n"
            f"Origen local: {local_path}\n"
            f"Destino contenedor: {container_path}\n"
            f"STDERR: {result.stderr}"
        )


def hdfs_exists(path: str) -> bool:
    result = run([
        "docker", "exec", NOMBRE_CONTENEDOR,
        "bash", "-c", f'hdfs dfs -test -e "{path}"'
    ])
    return result.returncode == 0


def hdfs_mkdir(path: str) -> None:
    docker_exec(f'hdfs dfs -mkdir -p "{path}"')


def hdfs_get(hdfs_path: str, local_path: Path, tmp_container_dir: str) -> None:
    """
    Descarga de HDFS a local:
      HDFS -> /tmp dentro del contenedor -> docker cp -> local
    """
    local_path.parent.mkdir(parents=True, exist_ok=True)

    filename = local_path.name
    tmp_container_path = f"{tmp_container_dir}/{filename}"

    docker_exec(f'mkdir -p "{tmp_container_dir}"')
    docker_exec(f'rm -f "{tmp_container_path}"')
    docker_exec(f'hdfs dfs -get "{hdfs_path}" "{tmp_container_path}"')

    docker_cp_from(tmp_container_path, local_path)

    docker_exec(f'rm -f "{tmp_container_path}"')


def hdfs_put(local_path: Path, hdfs_path: str, tmp_container_dir: str) -> None:
    """
    Sube de local a HDFS:
      local -> docker cp -> /tmp dentro del contenedor -> HDFS
    """
    filename = local_path.name
    tmp_container_path = f"{tmp_container_dir}/{filename}"

    hdfs_dir = hdfs_path.rsplit("/", 1)[0]

    docker_exec(f'mkdir -p "{tmp_container_dir}"')
    docker_exec(f'rm -f "{tmp_container_path}"')

    hdfs_mkdir(hdfs_dir)

    docker_cp_to(local_path, tmp_container_path)

    docker_exec(f'hdfs dfs -put "{tmp_container_path}" "{hdfs_path}"')
    docker_exec(f'rm -f "{tmp_container_path}"')


def listar_hdfs(path: str) -> list[str]:
    result = run([
        "docker", "exec", NOMBRE_CONTENEDOR,
        "bash", "-c", f'hdfs dfs -ls "{path}"'
    ])

    if result.returncode != 0:
        return []

    items = []

    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 8:
            items.append(parts[-1])

    return items


def listar_archivos_hdfs(path: str, extension: str = ".csv") -> list[str]:
    result = run([
        "docker", "exec", NOMBRE_CONTENEDOR,
        "bash", "-c", f'hdfs dfs -find "{path}" -name "*{extension}"'
    ])

    if result.returncode != 0:
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


# =======================================================================
# SKIP RÁPIDO SILVER
# =======================================================================

def cargar_salidas_existentes() -> set[str]:
    """
    Carga una vez todos los CSV ya procesados en silver.
    Así evitamos hacer hdfs dfs -test archivo por archivo.
    """
    log("Leyendo salidas ya existentes en silver...")

    result = run([
        "docker", "exec", NOMBRE_CONTENEDOR,
        "bash", "-c", f'hdfs dfs -find "{HDFS_SILVER_CLIMA}" -name "*.csv"'
    ])

    if result.returncode != 0:
        stderr = (result.stderr or "").lower()

        if "no such file or directory" in stderr or "file does not exist" in stderr:
            log("Silver aún no existe. Se asumirá vacío.")
            return set()

        raise RuntimeError(f"[ERROR listando silver]\n{result.stderr}")

    existentes = {
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    }

    log(f"Salidas existentes en silver: {len(existentes)}")
    return existentes


# =======================================================================
# PROCESAMIENTO FÍSICO
# =======================================================================

def procesar_potencial_csv(csv_path: Path, out_csv: Path) -> None:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    requeridas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}

    if not requeridas.issubset(df.columns):
        raise ValueError(f"CSV incompleto: {csv_path}")

    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce")
    df = df.dropna(subset=["valid_time"])

    df["ssrd_kWhm2"] = pd.to_numeric(df["ssrd_kWhm2"], errors="coerce").clip(lower=0)
    df["t2m_C"] = pd.to_numeric(df["t2m_C"], errors="coerce")
    df["tcc"] = pd.to_numeric(df["tcc"], errors="coerce").clip(0, 1)

    df["month"] = df["valid_time"].dt.month
    df = df.sort_values("valid_time").reset_index(drop=True)

    df["rad_norm"] = (df["ssrd_kWhm2"] / REF_RADIACION).clip(0, 1)
    df["pen_nube"] = (1 - df["tcc"]).clip(lower=0) ** ALFA_NUBES

    exceso = (df["t2m_C"] - TEMP_BASE).clip(lower=0)
    df["pen_temp"] = (1 - BETA_TEMP * exceso).clip(lower=0)

    horas_max = max(HORAS_SOL_POR_MES.values())

    df["horas_norm"] = df["month"].map(
        lambda m: HORAS_SOL_POR_MES[int(m)] / horas_max
    )

    df["potencial_0_1"] = (
        df["rad_norm"] *
        df["pen_nube"] *
        df["pen_temp"] *
        df["horas_norm"]
    ).clip(0, 1)

    for col in ["rad_norm", "pen_nube", "pen_temp", "horas_norm", "potencial_0_1"]:
        df[col] = df[col].round(4)

    columnas_salida = [
        "valid_time",
        *[c for c in ["tile_id", "latitude", "longitude"] if c in df.columns],
        "ssrd_kWhm2", "t2m_C", "tcc",
        "rad_norm", "pen_nube", "pen_temp",
        "horas_norm", "potencial_0_1",
    ]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df[columnas_salida].to_csv(out_csv, index=False)


# =======================================================================
# LOTES TILE/AÑO
# =======================================================================

def obtener_lotes_tile_anio() -> list[tuple[str, str]]:
    tiles = listar_hdfs(HDFS_BRONZE_CSV)
    lotes = []

    for tile_path in tiles:
        tile = tile_path.rsplit("/", 1)[-1]

        if not TILE_PATTERN.match(tile):
            continue

        years = listar_hdfs(tile_path)

        for year_path in years:
            year = year_path.rsplit("/", 1)[-1]

            if YEAR_PATTERN.match(year):
                lotes.append((tile, year))

    return sorted(lotes)


def obtener_csvs_lote(tile: str, year: str) -> list[str]:
    hdfs_lote_path = f"{HDFS_BRONZE_CSV}/{tile}/{year}"
    csvs = listar_archivos_hdfs(hdfs_lote_path, ".csv")

    validos = []

    for csv_path in csvs:
        filename = csv_path.rsplit("/", 1)[-1]

        if CSV_PATTERN.match(filename) and "potencial" not in filename.lower():
            validos.append(csv_path)

    return sorted(validos)


def salida_hdfs_para_csv_entrada(hdfs_csv_path: str) -> str:
    """
    Entrada:
      /datalake/datos/bronze/csv/tile01/2013/2013_04.csv

    Salida:
      /datalake/datos/silver/Clima/tile01/2013/2013_04_potencial.csv
    """
    relative = hdfs_csv_path.replace(HDFS_BRONZE_CSV + "/", "")
    tile, year, filename = relative.split("/")

    stem = filename.replace(".csv", "")
    out_filename = f"{stem}_potencial.csv"

    return f"{HDFS_SILVER_CLIMA}/{tile}/{year}/{out_filename}"


def procesar_lote(
    tile: str,
    year: str,
    salidas_existentes: set[str],
    salidas_lock: threading.Lock
) -> tuple[int, int]:
    """
    Procesa un lote tile/año.
    """
    log(f"\n===== LOTE {tile}/{year} =====")

    csvs_hdfs = obtener_csvs_lote(tile, year)

    if not csvs_hdfs:
        log(f"[{tile}/{year}] No hay CSV.")
        return 0, 0

    tmp_lote = Path(tempfile.mkdtemp(prefix=f"etl_{tile}_{year}_"))
    tmp_container_dir = f"{RUTA_TMP_CONTENEDOR}/{tile}_{year}"

    procesados = 0
    saltados = 0

    try:
        for hdfs_csv in csvs_hdfs:
            hdfs_out = salida_hdfs_para_csv_entrada(hdfs_csv)

            with salidas_lock:
                ya_existe = hdfs_out in salidas_existentes

            if ya_existe:
                log("[SKIP]", hdfs_out)
                saltados += 1
                continue

            filename = hdfs_csv.rsplit("/", 1)[-1]

            local_in = tmp_lote / filename
            local_out = tmp_lote / filename.replace(".csv", "_potencial.csv")

            try:
                hdfs_get(hdfs_csv, local_in, tmp_container_dir)
                procesar_potencial_csv(local_in, local_out)
                hdfs_put(local_out, hdfs_out, tmp_container_dir)

                with salidas_lock:
                    salidas_existentes.add(hdfs_out)

                log("[SUBIDO]", hdfs_out)
                procesados += 1

            except Exception as exc:
                log(f"[ERROR] {tile}/{year} -> {hdfs_csv}")
                log(exc)

        return procesados, saltados

    finally:
        try:
            shutil.rmtree(tmp_lote, ignore_errors=True)
        except PermissionError:
            log(f"[AVISO] No se pudo borrar temporal local: {tmp_lote}")

        try:
            docker_exec(f'rm -rf "{tmp_container_dir}"')
        except Exception as exc:
            log(f"[AVISO] No se pudo borrar temporal contenedor {tmp_container_dir}: {exc}")


# =======================================================================
# MAIN
# =======================================================================

def procesar_potencial_hdfs_por_lotes() -> None:
    if not hdfs_exists(HDFS_BRONZE_CSV):
        print(f"No existe la ruta de entrada en HDFS: {HDFS_BRONZE_CSV}")
        return

    hdfs_mkdir(HDFS_SILVER_CLIMA)
    docker_exec(f'mkdir -p "{RUTA_TMP_CONTENEDOR}"')

    lotes = obtener_lotes_tile_anio()
    salidas_existentes = cargar_salidas_existentes()
    salidas_lock = threading.Lock()

    print("==============================================")
    print(f"Entrada HDFS : {HDFS_BRONZE_CSV}")
    print(f"Salida HDFS  : {HDFS_SILVER_CLIMA}")
    print(f"Lotes        : {len(lotes)}")
    print(f"Workers      : {MAX_WORKERS}")
    print("==============================================")

    total_procesados = 0
    total_saltados = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                procesar_lote,
                tile,
                year,
                salidas_existentes,
                salidas_lock
            ): (tile, year)
            for tile, year in lotes
        }

        for i, future in enumerate(as_completed(futures), start=1):
            tile, year = futures[future]

            try:
                procesados, saltados = future.result()
                total_procesados += procesados
                total_saltados += saltados

                print(
                    f"[{i}/{len(lotes)}] Terminado {tile}/{year} "
                    f"-> procesados={procesados}, saltados={saltados}"
                )

            except Exception as exc:
                print(f"[ERROR LOTE] {tile}/{year}")
                print(exc)

    print("\n============== RESUMEN FINAL ==============")
    print(f"Procesados nuevos: {total_procesados}")
    print(f"Saltados         : {total_saltados}")
    print("FIN")


if __name__ == "__main__":
    procesar_potencial_hdfs_por_lotes()