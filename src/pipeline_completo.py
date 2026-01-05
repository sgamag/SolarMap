# ============================================================
# PIPELINE INCREMENTAL COMPLETO (DESCARGA -> POTENCIAL -> BD)
#
# Objetivo:
# - Automatizar la carga de datos nuevos sin repetir descargas.
# - El estado del sistema lo marca la BD (era5_data).
# - El disco local se usa solo como zona temporal de trabajo.
#
# Flujo:
# 1) Leer en BD el último mes cargado (MAX valid_time).
# 2) Calcular el último mes completo disponible = mes_actual - 1
# 3) Descargar SOLO los meses faltantes (descargar_radiacion.py)
# 4) Procesar potencial SOLO para esos meses (procesar_potencial.py, en modo batch)
# 5) Cargar *_potencial.csv en MySQL (load_data.py) + actualizar resumen
# 6) Limpiar temporales (CSV y descargas) para no ocupar espacio
# ============================================================

import sys
import subprocess
from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine, text

# ------------------------------------------------------------
# CONFIGURACIÓN DE RUTAS (ajústalo si tu estructura cambia)
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# Importante: según lo que has dicho, tus CSV están en src/data/csv
CSV_ROOT = SRC_DIR / "data" / "csv"

RAW_ROOT = PROJECT_ROOT / "data" / "raw"
RAW_ROOT_ALT = SRC_DIR / "data" / "raw"

DESCARGA_SCRIPT = SRC_DIR / "descargar_radiacion.py"
POTENCIAL_SCRIPT = SRC_DIR / "procesar_potencial.py"
LOAD_SCRIPT = SRC_DIR / "load_data.py"

# ------------------------------------------------------------
# CONEXIÓN A MYSQL (MISMA QUE EN load_data.py)
# ------------------------------------------------------------

DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "era5_madrid"
DB_USER = "era5_user"
DB_PASS = "SolarMap67"

SQLALCHEMY_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(SQLALCHEMY_URL, future=True)

# ------------------------------------------------------------
# 1) OBTENER ÚLTIMO MES CARGADO EN BD
# ------------------------------------------------------------

def obtener_ultimo_mes_en_bd():
    """
    Devuelve (year, month) del último dato presente en era5_data
    según valid_time.
    Si no hay datos, devuelve None.
    """

    with engine.begin() as con:
        result = con.execute(
            text("SELECT MAX(valid_time) FROM era5_data")
        ).scalar()

    if result is None:
        return None

    return result.year, result.month

# ------------------------------------------------------------
# 2) DEFINIR EL ÚLTIMO MES COMPLETO DISPONIBLE
# ------------------------------------------------------------

def ultimo_mes_completo_disponible():
    """
    Regla simple y defendible:
    - El último mes completo disponible es el mes anterior al actual.
    """
    hoy = datetime.now()
    if hoy.month == 1:
        return hoy.year - 1, 12
    return hoy.year, hoy.month - 1

# ------------------------------------------------------------
# 3) ITERADOR DE MESES
# ------------------------------------------------------------

def iterar_meses(y_ini, m_ini, y_fin, m_fin):
    y, m = y_ini, m_ini
    while (y < y_fin) or (y == y_fin and m <= m_fin):
        yield y, m
        m += 1
        if m == 13:
            m = 1
            y += 1

# ------------------------------------------------------------
# 4) EJECUTAR DESCARGA PARA UN MES
# ------------------------------------------------------------

def ejecutar_descarga_mes(year: int, month: int) -> None:
    if not DESCARGA_SCRIPT.exists():
        raise FileNotFoundError(f"No existe {DESCARGA_SCRIPT}")

    cmd = [
        sys.executable,
        str(DESCARGA_SCRIPT),
        "--year", str(year),
        "--month", f"{month:02d}",
    ]

    print(f"\n--- DESCARGA {year}-{month:02d} ---")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(f"Falló descargar_radiacion.py para {year}-{month:02d}")

# ------------------------------------------------------------
# MAIN: ORQUESTACIÓN COMPLETA
# ------------------------------------------------------------

def main():
    print("=== PIPELINE INCREMENTAL (MENSUAL) ===")

    # 1) Identificar último mes en BD
    ultimo_bd = obtener_ultimo_mes_en_bd()

    if ultimo_bd is None:
        print("No hay datos en BD. Se asume inicio en 2000-01.")
        start_year, start_month = 2000, 1
    else:
        y, m = ultimo_bd
        if m == 12:
            start_year, start_month = y + 1, 1
        else:
            start_year, start_month = y, m + 1

    # 2) Determinar hasta dónde podemos descargar
    end_year, end_month = ultimo_mes_completo_disponible()

    print("Último mes en BD:", ultimo_bd)
    print("Último mes completo disponible:", (end_year, end_month))

    if (start_year, start_month) > (end_year, end_month):
        print("No hay nuevos meses completos que descargar.")
        return

    print(
        f"Se descargarán y cargarán datos desde "
        f"{start_year}-{start_month:02d} hasta {end_year}-{end_month:02d}"
    )

    # 3) Ejecutar descarga mes a mes
    for y, m in iterar_meses(start_year, start_month, end_year, end_month):
        ejecutar_descarga_mes(y, m)

    # 4) Ejecutar pipeline de potencial y carga
    subprocess.run([sys.executable, str(POTENCIAL_SCRIPT)])
    subprocess.run([sys.executable, str(LOAD_SCRIPT)])

    print("\nPipeline completado correctamente.")

# ------------------------------------------------------------
# EJECUCIÓN
# ------------------------------------------------------------

if __name__ == "__main__":
    main()
