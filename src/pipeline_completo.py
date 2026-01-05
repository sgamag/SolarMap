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
# 3) Descargar por AÑOS completos (descargar_radiacion.py)
# 4) Procesar potencial SOLO hasta el último mes completo
# 5) Cargar *_potencial.csv en MySQL (load_data.py)
#
# NOTA CLAVE:
# - Aunque se descarguen meses "de más", solo se procesan y cargan
#   los meses completos válidos.
# ============================================================

import sys
import subprocess
from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine, text

# ------------------------------------------------------------
# CONFIGURACIÓN DE RUTAS
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

CSV_ROOT = SRC_DIR / "data" / "csv"

DESCARGA_SCRIPT = SRC_DIR / "descargar_radiacion.py"
POTENCIAL_SCRIPT = SRC_DIR / "procesar_potencial.py"
LOAD_SCRIPT = SRC_DIR / "load_data.py"

# ------------------------------------------------------------
# CONEXIÓN A MYSQL
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
    Devuelve (year, month) del último dato presente en era5_data.
    Si la BD está vacía, devuelve None.
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
    El último mes completo disponible es el mes anterior al actual.
    Ejemplo:
      - Hoy = noviembre 2025 → último completo = octubre 2025
    """
    hoy = datetime.now()
    if hoy.month == 1:
        return hoy.year - 1, 12
    return hoy.year, hoy.month - 1

# ------------------------------------------------------------
# 3) DESCARGA POR AÑOS (INTERFAZ REAL DEL DESCARGADOR)
# ------------------------------------------------------------

def ejecutar_descarga_por_anos(start_year: int, end_year: int):
    """
    Llama a descargar_radiacion.py usando --start-year / --end-year.
    El control mensual fino se hará después.
    """
    if not DESCARGA_SCRIPT.exists():
        raise FileNotFoundError(f"No existe {DESCARGA_SCRIPT}")

    cmd = [
        sys.executable,
        str(DESCARGA_SCRIPT),
        "--start-year", str(start_year),
        "--end-year", str(end_year),
    ]

    print("\n--- DESCARGA ERA5 POR AÑOS ---")
    print("Ejecutando:", " ".join(cmd))

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError("Falló descargar_radiacion.py")

# ------------------------------------------------------------
# 4) LIMPIEZA DE CSV POSTERIORES AL ÚLTIMO MES COMPLETO
# ------------------------------------------------------------

def limpiar_csv_fuera_de_rango(end_year: int, end_month: int):
    """
    Elimina (o ignora) CSV que correspondan a meses posteriores
    al último mes completo disponible.
    Esto garantiza que solo se procesen meses válidos.
    """
    if not CSV_ROOT.exists():
        return

    for csv_path in CSV_ROOT.rglob("*.csv"):
        try:
            # Estructura esperada:
            # .../tile_xx_yy/YYYY/YYYY_MM.csv o YYYY_MM_potencial.csv
            year = int(csv_path.parent.name)
            month = int(csv_path.stem.split("_")[1])

            if (year, month) > (end_year, end_month):
                print(f"Saltando CSV fuera de rango: {csv_path}")
                csv_path.unlink(missing_ok=True)

        except Exception:
            # Si el nombre no sigue el patrón esperado, no tocamos nada
            continue

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    print("=== PIPELINE INCREMENTAL (MENSUAL, CONTROLADO) ===")

    # 1) Último mes cargado en BD
    ultimo_bd = obtener_ultimo_mes_en_bd()

    if ultimo_bd is None:
        print("No hay datos en BD. Se asume inicio en 2000-01.")
        start_year = 2000
    else:
        start_year = ultimo_bd[0]

    # 2) Último mes completo disponible
    end_year, end_month = ultimo_mes_completo_disponible()

    print("Último mes en BD:", ultimo_bd)
    print("Último mes completo disponible:", (end_year, end_month))

    if ultimo_bd and (ultimo_bd[0], ultimo_bd[1]) >= (end_year, end_month):
        print("La BD ya está actualizada hasta el último mes completo.")
        return

    # 3) Descargar por años completos
    ejecutar_descarga_por_anos(start_year, end_year)

    # 4) Limpiar CSV fuera de rango mensual
    limpiar_csv_fuera_de_rango(end_year, end_month)

    # 5) Procesar potencial (solo CSV válidos)
    subprocess.run([sys.executable, str(POTENCIAL_SCRIPT)])

    # 6) Cargar a MySQL
    subprocess.run([sys.executable, str(LOAD_SCRIPT)])

    print("\nPipeline completado correctamente.")

# ------------------------------------------------------------
# EJECUCIÓN
# ------------------------------------------------------------

if __name__ == "__main__":
    main()
