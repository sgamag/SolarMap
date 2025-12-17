"""
Procesamiento físico del potencial solar horario (0–1).

El script:
- Recorre automáticamente data/csv/
- Detecta qué CSV existen realmente
- Procesa SOLO los que no tienen su _potencial.csv asociado
- No pide fechas ni años
"""

import pandas as pd
from pathlib import Path

# =======================================================================
# PARÁMETROS FÍSICOS DEL MODELO
# =======================================================================

HORAS_SOL_POR_MES = {
    1: 9.3,  2: 10.0, 3: 11.9, 4: 13.3,
    5: 14.5, 6: 16.8, 7: 15.7, 8: 15.1,
    9: 13.0, 10: 12.4, 11: 10.8, 12: 9.0
}

ALFA_NUBES    = 0.90
TEMP_BASE     = 25.0
BETA_TEMP     = 0.004
REF_RADIACION = 1.0


# =======================================================================
# PROCESAR CSV INDIVIDUAL
# =======================================================================

def procesar_potencial_csv(csv_path: Path):

    print("Procesando:", csv_path)

    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    requeridas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}
    if not requeridas.issubset(df.columns):
        raise ValueError(f"CSV incompleto: {csv_path}")

    # ------------------- LIMPIEZA -------------------
    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce")
    df = df.dropna(subset=["valid_time"])

    df["ssrd_kWhm2"] = pd.to_numeric(df["ssrd_kWhm2"], errors="coerce").clip(lower=0)
    df["t2m_C"]      = pd.to_numeric(df["t2m_C"], errors="coerce")
    df["tcc"]        = pd.to_numeric(df["tcc"], errors="coerce").clip(0, 1)

    df["month"] = df["valid_time"].dt.month
    df = df.sort_values("valid_time").reset_index(drop=True)

    # ============================================================
    # MODELO FÍSICO
    # ============================================================

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

    # ============================================================
    # EXPORTAR (MISMA CARPETA)
    # ============================================================

    out_csv = csv_path.parent / f"{csv_path.stem}_potencial.csv"

    columnas_salida = [
        "valid_time",
        *[c for c in ["tile_id", "latitude", "longitude"] if c in df.columns],
        "ssrd_kWhm2", "t2m_C", "tcc",
        "rad_norm", "pen_nube", "pen_temp",
        "horas_norm", "potencial_0_1",
    ]

    df[columnas_salida].to_csv(out_csv, index=False)
    print("  → generado:", out_csv.name)


# =======================================================================
# PROCESO AUTOMÁTICO COMPLETO
# =======================================================================

def procesar_potencial_automatico():

    base = Path("data/csv")
    if not base.exists():
        print("No existe data/csv")
        return

    csvs = sorted(base.rglob("*.csv"))

    print(f"{len(csvs)} CSV encontrados")

    procesados = 0
    saltados = 0

    for csv_path in csvs:

        # Saltar los ya procesados
        if csv_path.name.endswith("_potencial.csv"):
            continue

        potencial_csv = csv_path.parent / f"{csv_path.stem}_potencial.csv"

        if potencial_csv.exists():
            saltados += 1
            continue

        procesar_potencial_csv(csv_path)
        procesados += 1

    print("\n=== RESUMEN ===")
    print(f"Procesados nuevos: {procesados}")
    print(f"Saltados (ya existían): {saltados}")


# =======================================================================
# EJECUCIÓN
# =======================================================================

if __name__ == "__main__":
    procesar_potencial_automatico()
