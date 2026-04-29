import subprocess
import tempfile
import textwrap
import shlex
import re
import threading
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# CONFIGURACIÓN
# ============================================================

CONTENEDOR = "solarmap_namenode"

RUTA_BRONZE = "/datalake/datos/bronze/csv"
RUTA_SILVER = "/datalake/datos/silver/Clima"

TMP_CONTENEDOR = "/tmp/etl_clima"
SCRIPT_POLARS_CONTENEDOR = "/tmp/procesar_potencial_polars.py"

NUM_WORKERS = 3

PATRON_TILE = re.compile(r"^tile\d{2}$")
PATRON_ANIO = re.compile(r"^\d{4}$")
PATRON_CSV = re.compile(r"^\d{4}_\d{2}\.csv$")

lock_print = threading.Lock()


def log(*args):
    with lock_print:
        print(*args)


# ============================================================
# COMANDOS DOCKER / HDFS
# ============================================================

def ejecutar(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def docker_exec(cmd: str) -> str:
    resultado = ejecutar(["docker", "exec", CONTENEDOR, "bash", "-c", cmd])

    if resultado.returncode != 0:
        raise RuntimeError(
            f"[ERROR docker exec]\n"
            f"Comando: {cmd}\n"
            f"STDERR: {resultado.stderr}"
        )

    return resultado.stdout


def docker_cp_a_contenedor(origen: Path, destino: str) -> None:
    resultado = ejecutar(["docker", "cp", str(origen), f"{CONTENEDOR}:{destino}"])

    if resultado.returncode != 0:
        raise RuntimeError(
            f"[ERROR docker cp]\n"
            f"Origen: {origen}\n"
            f"Destino: {destino}\n"
            f"STDERR: {resultado.stderr}"
        )


def existe_hdfs(ruta: str) -> bool:
    resultado = ejecutar([
        "docker", "exec", CONTENEDOR,
        "bash", "-c", f'hdfs dfs -test -e "{ruta}"'
    ])
    return resultado.returncode == 0


def crear_directorio_hdfs(ruta: str) -> None:
    docker_exec(f'hdfs dfs -mkdir -p "{ruta}"')


def listar_csv_hdfs(ruta: str) -> list[str]:
    resultado = ejecutar([
        "docker", "exec", CONTENEDOR,
        "bash", "-c", f'hdfs dfs -find "{ruta}" -name "*.csv"'
    ])

    if resultado.returncode != 0:
        stderr = (resultado.stderr or "").lower()

        if "no such file or directory" in stderr or "file does not exist" in stderr:
            return []

        raise RuntimeError(f"[ERROR listando HDFS]\n{resultado.stderr}")

    return [linea.strip() for linea in resultado.stdout.splitlines() if linea.strip()]


# ============================================================
# SCRIPT POLARS QUE SE EJECUTA DENTRO DEL CONTENEDOR
# ============================================================

SCRIPT_POLARS = r'''
import sys
from pathlib import Path
import polars as pl


HORAS_SOL = {
    1: 9.3,  2: 10.0, 3: 11.9, 4: 13.3,
    5: 14.5, 6: 16.8, 7: 15.7, 8: 15.1,
    9: 13.0, 10: 12.4, 11: 10.8, 12: 9.0
}

ALFA_NUBES = 0.90
TEMP_BASE = 25.0
BETA_TEMP = 0.004
REF_RADIACION = 1.0


def expresion_horas_norm():
    horas_max = max(HORAS_SOL.values())

    expr = None

    for mes, horas in HORAS_SOL.items():
        valor = horas / horas_max

        if expr is None:
            expr = pl.when(pl.col("month") == mes).then(pl.lit(valor))
        else:
            expr = expr.when(pl.col("month") == mes).then(pl.lit(valor))

    return expr.otherwise(None).alias("horas_norm")


def procesar_csv(ruta_entrada: Path, ruta_salida: Path):
    df = pl.read_csv(ruta_entrada)

    columnas_limpias = {c: c.strip() for c in df.columns if c != c.strip()}
    if columnas_limpias:
        df = df.rename(columnas_limpias)

    requeridas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}

    if not requeridas.issubset(set(df.columns)):
        raise ValueError(f"CSV incompleto: {ruta_entrada}")

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
        (pl.lit(1) - BETA_TEMP * ((pl.col("t2m_C") - TEMP_BASE).clip(0, None))).clip(0, None).alias("pen_temp"),
        expresion_horas_norm(),
    ])

    df = df.with_columns(
        (
            pl.col("rad_norm") *
            pl.col("pen_nube") *
            pl.col("pen_temp") *
            pl.col("horas_norm")
        ).clip(0, 1).alias("potencial_0_1")
    )

    for col in ["rad_norm", "pen_nube", "pen_temp", "horas_norm", "potencial_0_1"]:
        df = df.with_columns(pl.col(col).round(4).alias(col))

    columnas_salida = ["valid_time"]

    for col in ["tile_id", "latitude", "longitude"]:
        if col in df.columns:
            columnas_salida.append(col)

    columnas_salida += [
        "ssrd_kWhm2", "t2m_C", "tcc",
        "rad_norm", "pen_nube", "pen_temp",
        "horas_norm", "potencial_0_1",
    ]

    df_salida = df.select(columnas_salida)

    # Para parecerse a pandas: YYYY-MM-DD HH:MM:SS
    df_salida = df_salida.with_columns(
        pl.col("valid_time").dt.strftime("%Y-%m-%d %H:%M:%S").alias("valid_time")
    )

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    df_salida.write_csv(ruta_salida)


def main():
    if len(sys.argv) < 4:
        print("Uso: python3 procesar_potencial_polars.py <dir_entrada> <dir_salida> <csv1> [csv2 ...]")
        sys.exit(1)

    dir_entrada = Path(sys.argv[1])
    dir_salida = Path(sys.argv[2])
    nombres_csv = sys.argv[3:]

    procesados = 0

    for nombre_csv in nombres_csv:
        entrada = dir_entrada / nombre_csv
        salida = dir_salida / nombre_csv.replace(".csv", "_potencial.csv")

        procesar_csv(entrada, salida)
        procesados += 1

    print(f"Procesados en Polars: {procesados}")


if __name__ == "__main__":
    main()
'''


def copiar_script_polars_al_contenedor() -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(SCRIPT_POLARS)
        ruta_local = Path(f.name)

    try:
        docker_cp_a_contenedor(ruta_local, SCRIPT_POLARS_CONTENEDOR)
    finally:
        ruta_local.unlink(missing_ok=True)


def comprobar_polars() -> None:
    resultado = ejecutar([
        "docker", "exec", CONTENEDOR,
        "bash", "-c", "python3 -c 'import polars; print(polars.__version__)'"
    ])

    if resultado.returncode != 0:
        raise RuntimeError(
            "Polars no está instalado dentro del contenedor.\n"
            "Ejecuta:\n"
            f'docker exec {CONTENEDOR} bash -c "pip3 install polars"'
        )

    log("Polars detectado en contenedor:", resultado.stdout.strip())


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
    log("Listando CSV de bronze una sola vez...")
    csv_bronze = listar_csv_hdfs(RUTA_BRONZE)
    csv_bronze_validos = [p for p in csv_bronze if es_csv_bronze_valido(p)]

    log(f"CSV encontrados en bronze: {len(csv_bronze)}")
    log(f"CSV válidos en bronze    : {len(csv_bronze_validos)}")

    log("Listando CSV ya existentes en silver una sola vez...")
    csv_silver = set(listar_csv_hdfs(RUTA_SILVER))
    log(f"CSV existentes en silver : {len(csv_silver)}")

    trabajos = defaultdict(list)
    saltados = 0

    for entrada in csv_bronze_validos:
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
# PROCESAMIENTO POR LOTE DENTRO DEL CONTENEDOR
# ============================================================

def procesar_lote(tile: str, anio: str, trabajos_lote: list[tuple[str, str]]) -> tuple[int, int]:
    log(f"\n===== LOTE {tile}/{anio} | pendientes={len(trabajos_lote)} =====")

    tmp_lote = f"{TMP_CONTENEDOR}/{tile}_{anio}"
    tmp_entrada = f"{tmp_lote}/entrada"
    tmp_salida = f"{tmp_lote}/salida"

    ruta_hdfs_lote = f"{RUTA_BRONZE}/{tile}/{anio}"
    ruta_hdfs_salida = f"{RUTA_SILVER}/{tile}/{anio}"

    nombres_pendientes = [
        entrada.rsplit("/", 1)[-1]
        for entrada, _ in trabajos_lote
    ]

    try:
        docker_exec(f'rm -rf "{tmp_lote}"')
        docker_exec(f'mkdir -p "{tmp_entrada}" "{tmp_salida}"')

        # Descargamos el lote completo dentro del contenedor
        docker_exec(f'hdfs dfs -get "{ruta_hdfs_lote}"/*.csv "{tmp_entrada}/"')

        # Procesamos solo los CSV pendientes
        args_csv = " ".join(shlex.quote(nombre) for nombre in nombres_pendientes)

        docker_exec(
            f'python3 "{SCRIPT_POLARS_CONTENEDOR}" '
            f'"{tmp_entrada}" "{tmp_salida}" {args_csv}'
        )

        crear_directorio_hdfs(ruta_hdfs_salida)

        # Subimos todas las salidas generadas de golpe
        docker_exec(f'hdfs dfs -put "{tmp_salida}"/*.csv "{ruta_hdfs_salida}/"')

        log(f"[OK LOTE] {tile}/{anio} -> {len(nombres_pendientes)} archivos")
        return len(nombres_pendientes), 0

    except Exception as exc:
        log(f"[ERROR LOTE] {tile}/{anio}")
        log(exc)
        return 0, len(nombres_pendientes)

    finally:
        try:
            docker_exec(f'rm -rf "{tmp_lote}"')
        except Exception as exc:
            log(f"[AVISO] No se pudo borrar temporal {tmp_lote}: {exc}")


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    if not existe_hdfs(RUTA_BRONZE):
        print(f"No existe la ruta de entrada en HDFS: {RUTA_BRONZE}")
        return

    crear_directorio_hdfs(RUTA_SILVER)
    docker_exec(f'mkdir -p "{TMP_CONTENEDOR}"')

    comprobar_polars()
    copiar_script_polars_al_contenedor()

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