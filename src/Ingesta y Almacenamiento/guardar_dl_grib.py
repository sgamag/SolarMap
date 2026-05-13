import os
from pathlib import Path
import subprocess
import sys
import re

# ============================================================
# CONFIGURACIÓN
# ============================================================

ruta_proyecto = Path(os.getenv("Ruta_Datalake", "."))
    
# Contenedor Docker donde ejecutar comandos HDFS
nombre_contenedor = "solarmap_namenode"

# Ruta base en HDFS donde se guardarán los .nc
ruta_datalake = "/datalake/datos/bronze/grib"

# Ruta temporal dentro del contenedor
ruta_docker_temporal = "/tmp/grib_uploads"

# Ruta local de origen
SOURCE_ROOT = ruta_proyecto / "data" / "datosBigData" / "data" / "raw" / "era5"

# Si True, borra el archivo local cuando:
# - se sube correctamente a HDFS
# - o ya existía en HDFS
BORRAR_LOCAL_TRAS_SUBIR = False

# Si True, imprime skips y más detalle
MOSTRAR_SKIPS = True

# ============================================================
# PATRONES
# ============================================================

TILE_PATTERN = re.compile(r"^tile_(\d{2})_(\d{2})$")
YEAR_PATTERN = re.compile(r"^\d{4}$")
FILE_PATTERN = re.compile(r"^\d{4}_\d{2}\.nc$")


# ============================================================
# UTILIDADES COMANDOS
# ============================================================

def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def docker_exec(cmd: str) -> str:
    result = run(["docker", "exec", nombre_contenedor, "bash", "-c", cmd])
    if result.returncode != 0:
        print("[ERROR docker exec]")
        print("Comando:", cmd)
        print("STDERR :", result.stderr)
        sys.exit(1)
    return result.stdout


def docker_cp(local: Path, remote: str) -> None:
    result = run(["docker", "cp", str(local), f"{nombre_contenedor}:{remote}"])
    if result.returncode != 0:
        print("[ERROR docker cp]")
        print("Archivo local :", local)
        print("Destino docker:", remote)
        print("STDERR       :", result.stderr)
        sys.exit(1)


# ============================================================
# VALIDACIÓN Y MAPEOS
# ============================================================

def source_tile_to_dest_tile(name: str) -> str:
    """
    Convierte:
      tile_00_00 -> tile01
      tile_00_01 -> tile02
      ...
      tile_05_05 -> tile36
    """
    match = TILE_PATTERN.match(name)
    if not match:
        raise ValueError(f"Tile con formato inválido: {name}")

    row = int(match.group(1))
    col = int(match.group(2))

    if not (0 <= row <= 5 and 0 <= col <= 5):
        raise ValueError(f"Tile fuera de rango: {name}")

    return f"tile{row * 6 + col + 1:02}"


def is_valid(path: Path) -> bool:
    """
    Valida rutas locales del tipo:
      SOURCE_ROOT/tile_00_00/2005/2005_07.nc
    """
    try:
        rel = path.relative_to(SOURCE_ROOT)
    except ValueError:
        return False

    if len(rel.parts) != 3:
        return False

    tile_name, year, filename = rel.parts

    return bool(
        TILE_PATTERN.match(tile_name)
        and YEAR_PATTERN.match(year)
        and FILE_PATTERN.match(filename)
    )


def build_hdfs_path(file_path: Path) -> tuple[str, str, str, str]:
    """
    Devuelve:
      source_tile, dest_tile, year, hdfs_path
    """
    rel = file_path.relative_to(SOURCE_ROOT)
    source_tile, year, filename = rel.parts
    dest_tile = source_tile_to_dest_tile(source_tile)
    hdfs_path = f"{ruta_datalake}/{dest_tile}/{year}/{filename}"
    return source_tile, dest_tile, year, hdfs_path


# ============================================================
# HDFS: LECTURA DE ESTADO PARA SKIP RÁPIDO
# ============================================================

def get_existing_hdfs_files() -> set[str]:
    """
    Lista una sola vez todos los .nc ya existentes en HDFS
    para evitar hacer 'hdfs dfs -test -e' archivo por archivo.
    """
    print("Leyendo archivos ya existentes en HDFS...")

    cmd = f'hdfs dfs -find "{ruta_datalake}" -name "*.nc"'
    result = run(["docker", "exec", nombre_contenedor, "bash", "-c", cmd])

    # Si la ruta aún no existe en HDFS, devolvemos set vacío.
    # Esto evita romper el script en la primera carga.
    if result.returncode != 0:
        stderr = (result.stderr or "").lower()
        if "no such file or directory" in stderr or "file does not exist" in stderr:
            print("La ruta base aún no existe en HDFS. Se asumirá vacía.")
            return set()

        print("[ERROR al listar HDFS]")
        print(result.stderr)
        sys.exit(1)

    existing = set()

    for line in result.stdout.splitlines():
        path = line.strip()
        if path:
            existing.add(path)

    print(f"Archivos ya existentes en HDFS: {len(existing)}")
    return existing


# ============================================================
# PROCESADO DE SUBIDA
# ============================================================

def process_file(
    file_path: Path,
    existing_hdfs_files: set[str],
    created_dirs: set[str]
) -> str:
    """
    Sube un único archivo a HDFS si no existe ya.

    Devuelve uno de:
      - "skip"
      - "ok"
    """
    _, dest_tile, year, hdfs_path = build_hdfs_path(file_path)

    # Skip rápido en memoria
    if hdfs_path in existing_hdfs_files:
        if MOSTRAR_SKIPS:
            print("[SKIP]", hdfs_path)

        if BORRAR_LOCAL_TRAS_SUBIR:
            try:
                file_path.unlink()
                print("[BORRADO LOCAL]", file_path)
            except Exception as exc:
                print(f"[AVISO] No se pudo borrar localmente {file_path}: {exc}")

        return "skip"

    dest_dir = f"{ruta_datalake}/{dest_tile}/{year}"
    tmp_path = f"{ruta_docker_temporal}/{dest_tile}_{file_path.name}"

    # Crear carpeta HDFS solo una vez por directorio
    if dest_dir not in created_dirs:
        docker_exec(f'hdfs dfs -mkdir -p "{dest_dir}"')
        created_dirs.add(dest_dir)

    # Copiar al contenedor
    docker_cp(file_path, tmp_path)

    # Subir a HDFS
    docker_exec(f'hdfs dfs -put "{tmp_path}" "{hdfs_path}"')

    # Borrar temporal del contenedor
    docker_exec(f'rm -f "{tmp_path}"')

    # Añadir a cache en memoria para evitar reintentos dentro del mismo run
    existing_hdfs_files.add(hdfs_path)

    # Borrar local si así se quiere
    if BORRAR_LOCAL_TRAS_SUBIR:
        try:
            file_path.unlink()
            print("[OK + BORRADO LOCAL]", hdfs_path)
        except Exception as exc:
            print(f"[OK] {hdfs_path}")
            print(f"[AVISO] Subido, pero no se pudo borrar localmente {file_path}: {exc}")
    else:
        print("[OK]", hdfs_path)

    return "ok"


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    if not SOURCE_ROOT.exists():
        print("[ERROR] SOURCE_ROOT no existe:")
        print(SOURCE_ROOT)
        sys.exit(1)

    # Comprobar Docker
    result = run(["docker", "ps"])
    if result.returncode != 0:
        print("[ERROR] Docker no está disponible.")
        print(result.stderr)
        sys.exit(1)

    # Comprobar contenedor
    result = run(["docker", "inspect", nombre_contenedor])
    if result.returncode != 0:
        print(f"[ERROR] No existe el contenedor: {nombre_contenedor}")
        sys.exit(1)

    # Crear temporal dentro del contenedor
    docker_exec(f'mkdir -p "{ruta_docker_temporal}"')

    # Buscar archivos locales
    files = [p for p in SOURCE_ROOT.rglob("*.nc") if p.is_file()]
    valid = [p for p in files if is_valid(p)]

    print("====================================================")
    print(f"SOURCE_ROOT         : {SOURCE_ROOT}")
    print(f"Contenedor          : {nombre_contenedor}")
    print(f"Ruta HDFS base      : {ruta_datalake}")
    print(f"Temporal contenedor : {ruta_docker_temporal}")
    print(f".nc encontrados     : {len(files)}")
    print(f".nc válidos         : {len(valid)}")
    print("====================================================")

    if not valid:
        print("No hay archivos válidos para subir.")
        return

    # Cargar estado actual de HDFS UNA sola vez
    existing_hdfs_files = get_existing_hdfs_files()

    # Cache de directorios ya creados
    created_dirs: set[str] = set()

    subidos = 0
    saltados = 0

    total = len(valid)

    for i, f in enumerate(valid, start=1):
        print(f"[{i}/{total}] {f.name}")

        resultado = process_file(
            file_path=f,
            existing_hdfs_files=existing_hdfs_files,
            created_dirs=created_dirs
        )

        if resultado == "ok":
            subidos += 1
        else:
            saltados += 1

    print("\n================ RESUMEN ================")
    print(f"Total válidos     : {total}")
    print(f"Subidos nuevos    : {subidos}")
    print(f"Saltados (skip)   : {saltados}")
    print("FIN")


if __name__ == "__main__":
    main()