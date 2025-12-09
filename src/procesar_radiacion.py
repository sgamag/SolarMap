"""
Procesamiento físico del potencial solar horario (0–1).

Este script toma un CSV por tile con columnas:
- ssrd_kWhm2   Radiación solar acumulada (kWh/m² por hora)
- t2m_C        Temperatura del aire a 2m
- tcc          Nubosidad (0–1 o 0–100)
- valid_time   Fecha-hora

Y genera un índice 0–1 realista basado en:
- Energía solar instantánea (normalización física)
- Penalización por nubosidad
- Penalización por temperatura
- Penalización mensual por horas de sol
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# =======================================================================
# PARÁMETROS FÍSICOS DEL MODELO
# =======================================================================

# Horas reales de sol por mes (Madrid)
HORAS_SOL_POR_MES = {
    1: 9.3,  2: 10.0, 3: 11.9, 4: 13.3,
    5: 14.5, 6: 16.8, 7: 15.7, 8: 15.1,
    9: 13.0, 10: 12.4, 11: 10.8, 12: 9.0
}

ALFA_NUBES   = 0.90      # Penalización suave por nubosidad
TEMP_BASE    = 25.0      # Temperatura a partir de la cual baja el rendimiento
BETA_TEMP    = 0.004     # 0.4% de pérdida por grado >25°C
REF_RADIACION = 1.0       # 1 kWh/m²/h ≈ hora muy buena física


# =======================================================================
# PROCESAR CSV INDIVIDUAL
# =======================================================================

def procesar_potencial_csv(csv_path: str, guardar_grafico: bool = False):

    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    print("Procesando:", csv_path)
    df = pd.read_csv(csv_path)

    df.columns = [c.strip() for c in df.columns]

    requeridas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}
    if not requeridas.issubset(df.columns):
        raise ValueError("CSV incompleto:", csv_path)

    # ------------------- LIMPIEZA -------------------
    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce")
    df = df.dropna(subset=["valid_time"])

    df["ssrd_kWhm2"] = pd.to_numeric(df["ssrd_kWhm2"], errors="coerce").clip(lower=0)
    df["t2m_C"]      = pd.to_numeric(df["t2m_C"], errors="coerce")
    df["tcc"]        = pd.to_numeric(df["tcc"], errors="coerce").clip(0, 1)

    df["month"] = df["valid_time"].dt.month
    df = df.sort_values("valid_time").reset_index(drop=True)

    # ============================================================
    # 1. Radiación normalizada (física, no estadística)
    # ============================================================

    # 1 kWh/m²/h representa una hora "muy buena"
    df["rad_norm"] = (df["ssrd_kWhm2"] / REF_RADIACION).clip(0, 1)

    # ============================================================
    # 2. Penalización por nubosidad
    # ============================================================

    df["pen_nube"] = (1 - df["tcc"]).clip(lower=0) ** ALFA_NUBES

    # ============================================================
    # 3. Penalización térmica (solo si t2m > 25°C)
    # ============================================================

    exceso = (df["t2m_C"] - TEMP_BASE).clip(lower=0)
    df["pen_temp"] = (1 - BETA_TEMP * exceso).clip(lower=0)

    # ============================================================
    # 4. Penalización por horas de sol del mes
    # ============================================================

    horas_max = max(HORAS_SOL_POR_MES.values())
    df["horas_norm"] = df["month"].map(lambda m: HORAS_SOL_POR_MES[int(m)] / horas_max)
    df["horas_norm"] = df["horas_norm"].clip(0, 1)

    # ============================================================
    # 5. Potencial final físico
    # ============================================================

    df["potencial_0_1"] = (
        df["rad_norm"]
        * df["pen_nube"]
        * df["pen_temp"]
        * df["horas_norm"]
    ).clip(0, 1)

    # Redondeos
    for col in ["rad_norm", "pen_nube", "pen_temp", "horas_norm", "potencial_0_1"]:
        df[col] = df[col].round(4)

    # ============================================================
    # EXPORTAR RESULTADOS
    # ============================================================

    out_folder = csv_path.parent / "potencial"
    out_folder.mkdir(exist_ok=True)

    out_csv = out_folder / f"{csv_path.stem}_potencial.csv"

    columnas_salida = [
        "valid_time",
        *[c for c in ["tile_id", "latitude", "longitude"] if c in df.columns],
        "ssrd_kWhm2", "t2m_C", "tcc",
        "rad_norm", "pen_nube", "pen_temp",
        "horas_norm",
        "potencial_0_1",
    ]

    df[columnas_salida].to_csv(out_csv, index=False)
    print("CSV generado:", out_csv)

    # ============================================================
    # GRÁFICO
    # ============================================================

    if guardar_grafico:
        try:
            plt.figure(figsize=(10, 4))
            plt.plot(df["valid_time"], df["potencial_0_1"], lw=1.5)
            plt.xlabel("Fecha")
            plt.ylabel("Potencial (0–1)")
            plt.title(f"Potencial horario - {csv_path.stem}")
            plt.grid(alpha=0.3)
            plt.tight_layout()
            png_path = out_csv.with_suffix(".png")
            plt.savefig(png_path, dpi=140)
            plt.close()
            print("Gráfico generado:", png_path)
        except Exception as e:
            print("No se pudo generar gráfico:", e)

    return df


# =======================================================================
# PROCESAR POR AÑOS COMPLETOS
# =======================================================================

def procesar_potencial_por_años():
    """
    Procesa todos los CSV limpios dentro de src/data/csv/tile_xx_xx/AÑO/
    y genera los archivos *_potencial.csv
    """
    print("=== PROCESAR POTENCIAL POR AÑOS ===")

    ai = int(input("Año inicial: "))
    af = int(input("Año final: "))

    carpeta = Path("src/data/csv")
    if not carpeta.exists():
        print("No existe la carpeta src/data/csv.")
        return

    archivos = sorted(carpeta.rglob("*.csv"))
    print(f"{len(archivos)} archivos encontrados.")

    for archivo in archivos:
        # ignorar los ya procesados
        if archivo.name.endswith("_potencial.csv"):
            continue

        # extraer año desde .../tile_00_00/2000/archivo.csv
        try:
            year = int(archivo.parent.name)
        except ValueError:
            continue

        if ai <= year <= af:
            procesar_potencial_csv(archivo)


# =======================================================================
# EJECUCIÓN DIRECTA
# =======================================================================

if __name__ == "__main__":
    procesar_potencial_por_años()
