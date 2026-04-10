from pathlib import Path
import subprocess
import sys
import re

# ============================================================
# EDITA SOLO ESTO
# ============================================================

ruta_proyecto = Path(r"C:\Users\sergi\OneDrive\Escritorio\Universidad\BigData\ProyectoBigData")

nombre_contenedor = "solarmap_namenode"

# Ruta HDFS (ya confirmada por tu captura)
ruta_datalake = "/datalake/datos/bronze/grib"

ruta_docker_temporal = "/tmp/grib_uploads"

# ============================================================

SOURCE_ROOT = ruta_proyecto / "data" / "datosBigData" / "data" / "raw" / "era5"

TILE_PATTERN = re.compile(r"^tile_(\d{2})_(\d{2})$")
YEAR_PATTERN = re.compile(r"^\d{4}$")
FILE_PATTERN = re.compile(r"^\d{4}_\d{2}\.nc$")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def docker_exec(cmd):
    result = run(["docker", "exec", nombre_contenedor, "bash", "-c", cmd])
    if result.returncode != 0:
        print("[ERROR]", result.stderr)
        sys.exit(1)


def docker_cp(local, remote):
    result = run(["docker", "cp", str(local), f"{nombre_contenedor}:{remote}"])
    if result.returncode != 0:
        print("[ERROR docker cp]", result.stderr)
        sys.exit(1)


def hdfs_exists(path):
    cmd = f"hdfs dfs -test -e {path}"
    result = run(["docker", "exec", nombre_contenedor, "bash", "-c", cmd])
    return result.returncode == 0


def source_tile_to_dest_tile(name):
    match = TILE_PATTERN.match(name)
    row = int(match.group(1))
    col = int(match.group(2))
    return f"tile{row*6 + col + 1:02}"


def is_valid(path):
    try:
        rel = path.relative_to(SOURCE_ROOT)
    except:
        return False

    if len(rel.parts) != 3:
        return False

    t, y, f = rel.parts

    return (
        TILE_PATTERN.match(t)
        and YEAR_PATTERN.match(y)
        and FILE_PATTERN.match(f)
    )


def process(file):
    rel = file.relative_to(SOURCE_ROOT)
    tile, year, filename = rel.parts

    dest_tile = source_tile_to_dest_tile(tile)

    hdfs_path = f"{ruta_datalake}/{dest_tile}/{year}/{filename}"

    # 🚨 Si ya existe → skip
    if hdfs_exists(hdfs_path):
        print("[SKIP]", hdfs_path)
        return

    tmp_path = f"{ruta_docker_temporal}/{dest_tile}_{filename}"

    # copiar al contenedor
    docker_cp(file, tmp_path)

    # crear carpeta en HDFS
    docker_exec(f"hdfs dfs -mkdir -p {ruta_datalake}/{dest_tile}/{year}")

    # subir a HDFS
    docker_exec(f"hdfs dfs -put {tmp_path} {hdfs_path}")

    # borrar tmp
    docker_exec(f"rm {tmp_path}")

    print("[OK]", hdfs_path)


def main():
    files = [p for p in SOURCE_ROOT.rglob("*.nc") if p.is_file()]
    valid = [p for p in files if is_valid(p)]

    print(f"Archivos válidos: {len(valid)}")

    for f in valid:
        process(f)

    print("FIN")


if __name__ == "__main__":
    docker_exec(f'mkdir -p "{ruta_docker_temporal}"')
    main()