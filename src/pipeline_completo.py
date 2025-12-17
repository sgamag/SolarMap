# ============================================================
# PIPELINE INCREMENTAL COMPLETO (DESCARGA -> POTENCIAL -> BD)
#
# Objetivo:
# - Automatizar la carga de datos nuevos sin repetir descargas.
# - El estado del sistema lo marca la BD (era5_data).
# - El disco local se usa solo como zona temporal de trabajo.
#
# Flujo:
# 1) Leer en BD el último año cargado (MAX año en valid_time).
# 2) Calcular el último año completo disponible en Copernicus = año_actual - 1
# 3) Descargar SOLO los años faltantes (descargar_radiacion.py)
# 4) Procesar potencial SOLO para esos años (procesar_potencial.py, en modo batch)
# 5) Cargar *_potencial.csv en SQLite (load_data.py) + actualizar resumen
# 6) Limpiar temporales (CSV y descargas) para no ocupar espacio
# ============================================================

import sys
import subprocess
from pathlib import Path
import sqlite3
from datetime import datetime
import pandas as pd

# ------------------------------------------------------------
# CONFIGURACIÓN DE RUTAS (ajústalo si tu estructura cambia)
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # raíz del proyecto
SRC_DIR = PROJECT_ROOT / "src"

DB_PATH = PROJECT_ROOT / "BaseDeDatos" / "era5_madrid.db"

# Importante: según lo que has dicho, tus CSV están en src/data/csv
CSV_ROOT = SRC_DIR / "data" / "csv"

# Si tu descargador guarda el GRIB/NC en otro sitio, ajusta esto:
RAW_ROOT = PROJECT_ROOT / "data" / "raw"   # si tu descargar_radiacion usa data/raw/...
RAW_ROOT_ALT = SRC_DIR / "data" / "raw"    # si tu descargar_radiacion usa src/data/raw/...

DESCARGA_SCRIPT = SRC_DIR / "descargar_radiacion.py"
POTENCIAL_SCRIPT = SRC_DIR / "procesar_potencial.py"
LOAD_SCRIPT = SRC_DIR / "load_data.py"

# Política de limpieza (recomendado: True)
BORRAR_CSV_LIMPIOS = True
BORRAR_CSV_POTENCIAL = True
BORRAR_RAW_DESCARGAS = True


# ------------------------------------------------------------
# 1) OBTENER ÚLTIMO AÑO CARGADO EN BD
# ------------------------------------------------------------

def obtener_ultimo_ano_en_bd(db_path: Path) -> int | None:
    """
    Devuelve el último año que existe en era5_data (según valid_time).
    Si no hay datos, devuelve None.
    """
    if not db_path.exists():
        return None

    con = sqlite3.connect(db_path)
    try:
        # valid_time está en formato 'YYYY-MM-DD HH:MM:SS'
        # extraemos el año como entero con substr.
        cur = con.execute("""
            SELECT MAX(CAST(SUBSTR(valid_time, 1, 4) AS INTEGER)) AS max_year
            FROM era5_data
        """)
        row = cur.fetchone()
        max_year = row[0] if row else None
        return max_year
    except Exception:
        # Si la tabla no existe o falla algo, tratamos como vacío.
        return None
    finally:
        con.close()


# ------------------------------------------------------------
# 2) DEFINIR EL ÚLTIMO AÑO COMPLETO DISPONIBLE
# ------------------------------------------------------------

def ultimo_ano_completo_disponible() -> int:
    """
    Regla simple y defendible:
    - El año completo disponible es el año anterior al actual.
    - Ejemplo: si estamos en 2025, el último completo es 2024.
    """
    return datetime.now().year - 1


# ------------------------------------------------------------
# 3) EJECUTAR DESCARGA PARA UN RANGO DE AÑOS
# ------------------------------------------------------------

def ejecutar_descarga(start_year: int, end_year: int) -> None:
    """
    Llama al script descargar_radiacion.py para descargar solo el rango faltante.
    """
    if not DESCARGA_SCRIPT.exists():
        raise FileNotFoundError(f"No existe {DESCARGA_SCRIPT}")

    cmd = [
        sys.executable,
        str(DESCARGA_SCRIPT),
        "--start-year", str(start_year),
        "--end-year", str(end_year),
    ]

    print("\n--- DESCARGA ---")
    print("Ejecutando:", " ".join(cmd))

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError("Falló descargar_radiacion.py")


# ------------------------------------------------------------
# 4) PROCESAR POTENCIAL EN MODO BATCH (SIN INPUT)
# ------------------------------------------------------------

def procesar_potencial_batch(start_year: int, end_year: int) -> None:
    """
    Procesa todos los CSV limpios (no potencial) dentro del rango de años
    y genera los *_potencial.csv correspondientes.

    Nota:
    - No llamamos a procesar_potencial.py en modo interactivo.
    - Recorremos los CSV en disco y ejecutamos el script con cada fichero.
    """
    if not POTENCIAL_SCRIPT.exists():
        raise FileNotFoundError(f"No existe {POTENCIAL_SCRIPT}")

    if not CSV_ROOT.exists():
        print("No existe la carpeta de CSV:", CSV_ROOT)
        return

    print("\n--- PROCESAR POTENCIAL ---")
    print(f"Buscando CSV limpios en {CSV_ROOT} para años {start_year}-{end_year}")

    # CSV limpios suelen estar en: src/data/csv/tile_xx_yy/AAAA/*.csv
    # Ignoramos los ya *_potencial.csv
    candidatos = sorted(CSV_ROOT.rglob("*.csv"))

    procesados = 0
    for f in candidatos:
        if f.name.endswith("_potencial.csv"):
            continue

        # Extraer año desde carpeta padre (tile/AAAA/archivo.csv)
        try:
            year = int(f.parent.name)
        except Exception:
            continue

        if year < start_year or year > end_year:
            continue

        cmd = [sys.executable, str(POTENCIAL_SCRIPT), str(f)]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"Falló procesar_potencial.py para {f}")

        procesados += 1

    print(f"CSVs procesados a potencial: {procesados}")


# ------------------------------------------------------------
# 5) CARGAR EN BD (load_data.py)
# ------------------------------------------------------------

def ejecutar_carga_bd() -> None:
    """
    Llama a load_data.py para:
    - insertar los *_potencial.csv en era5_data
    - actualizar potencial_tile_resumen
    """
    if not LOAD_SCRIPT.exists():
        raise FileNotFoundError(f"No existe {LOAD_SCRIPT}")

    print("\n--- CARGA EN BD ---")
    cmd = [sys.executable, str(LOAD_SCRIPT)]
    print("Ejecutando:", " ".join(cmd))

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError("Falló load_data.py")


# ------------------------------------------------------------
# 6) LIMPIEZA DE TEMPORALES
# ------------------------------------------------------------

def borrar_archivos(pattern: str, root: Path) -> int:
    """
    Borra archivos por patrón y devuelve cuántos se han borrado.
    """
    if not root.exists():
        return 0

    count = 0
    for f in root.rglob(pattern):
        try:
            f.unlink()
            count += 1
        except Exception:
            pass
    return count


def limpiar_temporales() -> None:
    """
    Limpia los temporales para no ocupar espacio local.
    - CSV limpios: *.csv (excepto los potencial si quieres mantenerlos)
    - CSV potencial: *_potencial.csv
    - Descargas raw: .nc / .grib (si existen)
    """
    print("\n--- LIMPIEZA ---")

    # CSV potencial
    if BORRAR_CSV_POTENCIAL:
        n = borrar_archivos("*_potencial.csv", CSV_ROOT)
        print("Borrados *_potencial.csv:", n)

    # CSV limpios (no potencial)
    if BORRAR_CSV_LIMPIOS:
        # borra todos los .csv que NO sean potencial
        if CSV_ROOT.exists():
            count = 0
            for f in CSV_ROOT.rglob("*.csv"):
                if f.name.endswith("_potencial.csv"):
                    continue
                try:
                    f.unlink()
                    count += 1
                except Exception:
                    pass
            print("Borrados CSV limpios:", count)

    # Raw descargas (dependiendo de dónde guarde descargar_radiacion)
    if BORRAR_RAW_DESCARGAS:
        borrados = 0
        for root in [RAW_ROOT, RAW_ROOT_ALT]:
            if root.exists():
                borrados += borrar_archivos("*.nc", root)
                borrados += borrar_archivos("*.grib", root)
        print("Borrados raw (*.nc / *.grib):", borrados)


# ------------------------------------------------------------
# MAIN: ORQUESTACIÓN COMPLETA
# ------------------------------------------------------------

def main():
    print("=== PIPELINE INCREMENTAL ===")

    # 1) Identificar último año en BD
    ultimo_bd = obtener_ultimo_ano_en_bd(DB_PATH)
    if ultimo_bd is None:
        print("No hay datos en BD (o BD no existe). Se asume inicio en 2000.")
        ultimo_bd = 1999

    # 2) Determinar hasta dónde podemos descargar (año completo)
    ultimo_cop = ultimo_ano_completo_disponible()
    print("Último año en BD:", ultimo_bd)
    print("Último año completo disponible:", ultimo_cop)

    # 3) Calcular rango faltante
    start_year = max(2000, ultimo_bd + 1)
    end_year = ultimo_cop

    if start_year > end_year:
        print("No hay nuevos años completos que descargar. BD ya está actualizada.")
        return

    print(f"Se descargarán y cargarán datos para: {start_year}-{end_year}")

    # 4) Ejecutar pipeline completo
    ejecutar_descarga(start_year, end_year)
    procesar_potencial_batch(start_year, end_year)
    ejecutar_carga_bd()
    limpiar_temporales()

    print("\nPipeline completado correctamente.")


if __name__ == "__main__":
    main()
