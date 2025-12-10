"""
Procesamiento físico del potencial solar horario (0–1).

Este script toma un CSV por tile con columnas:
- ssrd_kWhm2   Radiación solar acumulada (kWh/m² por hora)
- t2m_C        Temperatura del aire a 2m
- tcc          Nubosidad (0–1 o 0–100)
- valid_time   Fecha-hora

Y genera un índice 0–1 realista basado en:
- Energía solar instantánea
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

HORAS_SOL_POR_MES = {
    1: 9.3,  2: 10.0, 3: 11.9, 4: 13.3,
    5: 14.5, 6: 16.8, 7: 15.7, 8: 15.1,
    9: 13.0, 10: 12.4, 11: 10.8, 12: 9.0
}

ALFA_NUBES   = 0.90
TEMP_BASE    = 25.0
BETA_TEMP    = 0.004
REF_RADIACION = 1.0


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
    # 1. Radiación normalizada física
    # ============================================================

    df["rad_norm"] = (df["ssrd_kWhm2"] / REF_RADIACION).clip(0, 1)

    # ============================================================
    # 2. Penalización por nubosidad
    # ============================================================

    df["pen_nube"] = (1 - df["tcc"]).clip(lower=0) ** ALFA_NUBES

    # ============================================================
    # 3. Penalización térmica
    # ============================================================

    exceso = (df["t2m_C"] - TEMP_BASE).clip(lower=0)
    df["pen_temp"] = (1 - BETA_TEMP * exceso).clip(lower=0)

    # ============================================================
    # 4. Penalización por horas de sol
    # ============================================================

    horas_max = max(HORAS_SOL_POR_MES.values())
    df["horas_norm"] = df["month"].map(lambda m: HORAS_SOL_POR_MES[int(m)] / horas_max)

    # ============================================================
    # 5. Potencial final físico
    # ============================================================

    df["potencial_0_1"] = (
        df["rad_norm"] *
        df["pen_nube"] *
        df["pen_temp"] *
        df["horas_norm"]
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
        "horas_norm", "potencial_0_1",
    ]

    df[columnas_salida].to_csv(out_csv, index=False)
    print("CSV generado:", out_csv)

    return out_csv



# =======================================================================
# PROCESAR TODO POR AÑOS Y MOSTRAR MEDIA POR TILE
# =======================================================================

def procesar_potencial_por_años():
    print("=== PROCESAR POTENCIAL POR AÑOS ===")

    ai = int(input("Año inicial: "))
    af = int(input("Año final: "))

    carpeta = Path("data/csv")
    if not carpeta.exists():
        print("No existe la carpeta src/data/csv.")
        return

    archivos = sorted(carpeta.rglob("*.csv"))
    print(f"{len(archivos)} archivos encontrados.")

    potenciales_generados = []

    for archivo in archivos:

        if archivo.name.endswith("_potencial.csv"):
            continue

        try:
            year = int(archivo.parent.name)
        except ValueError:
            continue

        if ai <= year <= af:
            out_csv = procesar_potencial_csv(archivo)
            potenciales_generados.append(out_csv)

    # ============================================================
    # MEDIA DE POTENCIAL POR TILE
    # ============================================================

    print("\n=== MEDIA DE POTENCIAL POR TILE ===")

    medias = {}

    for csv_pot in potenciales_generados:

        df = pd.read_csv(csv_pot)

        if "tile_id" not in df.columns:
            continue

        tile = df["tile_id"].iloc[0]
        media_tile = df["potencial_0_1"].mean()

        if tile not in medias:
            medias[tile] = []

        medias[tile].append(media_tile)

    for tile, valores in medias.items():
        print(f"{tile}: {sum(valores)/len(valores):.4f}")



# =======================================================================
# EJECUCIÓN DIRECTA
# =======================================================================

if __name__ == "__main__":
    procesar_potencial_por_años()
