# src/pipeline_completo.py
import subprocess
import sys
from pathlib import Path

# Ruta FIJA al directorio src
SRC_DIR = Path(__file__).parent.resolve()

# Scripts que queremos ejecutar
SCRIPT_DESCARGA = SRC_DIR / "descargar_radiacion.py"
SCRIPT_POTENCIAL = SRC_DIR / "procesar_potencial.py"

def ejecutar_descarga(start_year, end_year):
    print("=== DESCARGANDO RADIACIÓN ===")

    cmd = [
        sys.executable,
        str(SCRIPT_DESCARGA),
        "--start-year", str(start_year),
        "--end-year", str(end_year)
    ]

    print("Ejecutando:", " ".join(cmd))
    proceso = subprocess.run(cmd)

    if proceso.returncode != 0:
        print("❌ Error ejecutando descargar_radiacion.py")
        sys.exit(1)

    print("✔ Descarga finalizada.\n")


def procesar_potenciales():
    print("=== PROCESANDO POTENCIAL ===")

    # Ruta absoluta a data/csv
    CSV_ROOT = SRC_DIR.parent / "data" / "csv"

    csvs = sorted(CSV_ROOT.rglob("*.csv"))

    if not csvs:
        print("❌ No se encontraron CSV limpios en data/csv/")
        return

    for csv_file in csvs:

        if csv_file.name.endswith("_potencial.csv"):
            continue

        cmd = [
            sys.executable,
            str(SCRIPT_POTENCIAL),
            str(csv_file)
        ]

        print(f"Procesando potencial -> {csv_file}")
        proceso = subprocess.run(cmd)

        if proceso.returncode != 0:
            print(f"❌ Error procesando {csv_file}")
        else:
            print(f"✔ Potencial generado: {csv_file.name}")

    print("✔ Procesamiento de potencial COMPLETADO.\n")


def main():
    print("=== PIPELINE COMPLETO ===")

    start_year = int(input("Año inicial: "))
    end_year   = int(input("Año final: "))

    ejecutar_descarga(start_year, end_year)
    procesar_potenciales()

    print("========================================")
    print(" Pipeline completado correctamente.")
    print(" Ahora ejecuta: python src/load_data.py")
    print(" para cargar los datos en la base.")
    print("========================================")


if __name__ == "__main__":
    main()
