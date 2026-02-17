# ============================================================
# PIPELINE INCREMENTAL COMPLETO (DESCARGA -> POTENCIAL -> BD)
#
# Flujo CORRECTO:
# 1) Descargar datos ERA5 (por años completos)
# 2) Identificar CSV válidos (<= último mes completo)
# 3) Verificar que TODOS tengan su *_potencial.csv
#    - si falta alguno → procesarlo
# 4) SOLO cuando todos los potenciales existen:
#    - cargar a MySQL
# ============================================================

import sys
import subprocess
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
import os

# ------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

CSV_ROOT = SRC_DIR / "data" / "csv"

DESCARGA_SCRIPT = SRC_DIR / "descargar_radiacion.py"
POTENCIAL_SCRIPT = SRC_DIR / "procesar_radiacion.py"
LOAD_SCRIPT = SRC_DIR / "load_data.py"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "era5_madrid")
DB_USER = os.getenv("DB_USER", "era5_user")
DB_PASS = os.getenv("DB_PASS", "SolarMap67")

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    future=True
)

# ------------------------------------------------------------
# 1) ÚLTIMO MES EN BD
# ------------------------------------------------------------

def obtener_ultimo_mes_en_bd():
    with engine.begin() as con:
        r = con.execute(text("SELECT MAX(valid_time) FROM era5_data")).scalar()
    if r is None:
        return None
    return r.year, r.month

# ------------------------------------------------------------
# 2) ÚLTIMO MES COMPLETO DISPONIBLE
# ------------------------------------------------------------

def ultimo_mes_completo():
    hoy = datetime.now()
    if hoy.month == 1:
        return hoy.year - 1, 12
    return hoy.year, hoy.month - 1

# ------------------------------------------------------------
# 3) DESCARGA ERA5 POR AÑOS
# ------------------------------------------------------------

def descargar_por_anos(start_year, end_year):
    cmd = [
        sys.executable,
        str(DESCARGA_SCRIPT),
        "--start-year", str(start_year),
        "--end-year", str(end_year),
    ]
    print("Descargando ERA5:", " ".join(cmd))
    if subprocess.run(cmd).returncode != 0:
        raise RuntimeError("Error en descargar_radiacion.py")

# ------------------------------------------------------------
# 4) CSV VÁLIDOS HASTA ÚLTIMO MES COMPLETO
# ------------------------------------------------------------

def csv_validos(end_year, end_month):
    validos = []
    for csv in CSV_ROOT.rglob("*.csv"):
        if csv.name.endswith("_potencial.csv"):
            continue
        try:
            year = int(csv.parent.name)
            month = int(csv.stem.split("_")[1])
        except Exception:
            continue
        if (year, month) <= (end_year, end_month):
            validos.append(csv)
    return sorted(validos)

# ------------------------------------------------------------
# 5) ASEGURAR POTENCIAL PARA TODOS LOS CSV
# ------------------------------------------------------------

def asegurar_potencial(csvs):
    pendientes = []
    for csv in csvs:
        pot = csv.parent / f"{csv.stem}_potencial.csv"
        if not pot.exists():
            pendientes.append(csv)

    if not pendientes:
        print("Todos los CSV ya tienen su potencial.")
        return

    print(f"Procesando {len(pendientes)} CSV sin potencial...")

    for csv in pendientes:
        print(" → procesando", csv)
        res = subprocess.run(
            [sys.executable, str(POTENCIAL_SCRIPT), str(csv)]
        )
        pot = csv.parent / f"{csv.stem}_potencial.csv"
        if res.returncode != 0 or not pot.exists():
            raise RuntimeError(f"No se generó potencial para {csv}")

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    print("=== PIPELINE INCREMENTAL VERIFICADO ===")

    ultimo_bd = obtener_ultimo_mes_en_bd()
    start_year = 2000 if ultimo_bd is None else ultimo_bd[0]

    end_year, end_month = ultimo_mes_completo()

    print("Último mes BD:", ultimo_bd)
    print("Último mes completo:", (end_year, end_month))

    if ultimo_bd and ultimo_bd >= (end_year, end_month):
        print("BD ya actualizada.")
        return

    # 1) Descargar
    descargar_por_anos(start_year, end_year)

    # 2) Detectar CSV válidos
    validos = csv_validos(end_year, end_month)
    print(f"{len(validos)} CSV válidos detectados")

    if not validos:
        print("No hay CSV válidos.")
        return

    # 3) Asegurar potencial
    asegurar_potencial(validos)

    # 4) Cargar SOLO cuando todo está listo
    print("Cargando datos en MySQL...")
    if subprocess.run([sys.executable, str(LOAD_SCRIPT)]).returncode != 0:
        raise RuntimeError("Error en load_data.py")

    print("Pipeline completado correctamente.")

# ------------------------------------------------------------
# EJECUCIÓN
# ------------------------------------------------------------

if __name__ == "__main__":
    main()
