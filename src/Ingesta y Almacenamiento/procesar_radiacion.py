"""
Procesamiento físico del potencial solar horario (0–1).

Objetivo general:
- Partimos de CSV "limpios" por tile con variables climáticas (ssrd_kWhm2, t2m_C, tcc, valid_time).
- Calculamos un índice físico de potencial solar horario (0–1) basado en:
  1) Radiación normalizada (energía disponible)
  2) Penalización por nubosidad (atenuación por nubes)
  3) Penalización por temperatura (pérdida por exceso térmico)
  4) Penalización mensual por horas de sol (estacionalidad simple)

Comportamiento del script:
- Recorre automáticamente data/csv/
- Detecta qué CSV existen realmente
- Procesa SOLO los que no tienen su _potencial.csv asociado
- No pide fechas ni años (modo batch incremental por presencia de ficheros)
"""

import pandas as pd
from pathlib import Path


# =======================================================================
# PARÁMETROS FÍSICOS DEL MODELO
# =======================================================================

# Horas de sol medias aproximadas por mes (para estacionalidad).
HORAS_SOL_POR_MES = {
    1: 9.3,  2: 10.0, 3: 11.9, 4: 13.3,
    5: 14.5, 6: 16.8, 7: 15.7, 8: 15.1,
    9: 13.0, 10: 12.4, 11: 10.8, 12: 9.0
}

# Fracción de penalización máxima por nubes (100% nublado = pierde 75% de eficiencia, conserva 25% por luz difusa).
FACTOR_NUBES  = 0.75  

# Temperatura "base" a partir de la cual penalizamos (en ºC).
TEMP_BASE     = 25.0 

# Sensibilidad térmica: cuánto baja el potencial por cada grado por encima de TEMP_BASE.
BETA_TEMP     = 0.004 

# Radiación de referencia (kWh/m²) para normalizar.
REF_RADIACION = 1.0


# =======================================================================
# PROCESAR CSV INDIVIDUAL
# =======================================================================

def procesar_potencial_csv(csv_path: Path, carpeta_salida: Path):
    print("Procesando:", csv_path)

    # 1) LECTURA Y VALIDACIÓN DE COLUMNAS
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    requeridas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}
    if not requeridas.issubset(df.columns):
        raise ValueError(f"CSV incompleto: {csv_path}")

    # 2) LIMPIEZA DE TIPOS Y VALORES
    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce")
    df = df.dropna(subset=["valid_time"])
    df["ssrd_kWhm2"] = pd.to_numeric(df["ssrd_kWhm2"], errors="coerce").clip(lower=0)
    df["t2m_C"] = pd.to_numeric(df["t2m_C"], errors="coerce")
    df["tcc"] = pd.to_numeric(df["tcc"], errors="coerce").clip(0, 1)
    df["month"] = df["valid_time"].dt.month
    df = df.sort_values("valid_time").reset_index(drop=True)

    # 3) MODELO FÍSICO (CÁLCULO DE COMPONENTES)
    
    # Radiación normalizada (0–1)
    df["rad_norm"] = (df["ssrd_kWhm2"] / REF_RADIACION).clip(0, 1)

    # Penalización por nubosidad (suavizada para luz difusa)
    df["pen_nube"] = (1 - (df["tcc"] * FACTOR_NUBES)).clip(lower=0)

    # Penalización térmica
    exceso = (df["t2m_C"] - TEMP_BASE).clip(lower=0)
    df["pen_temp"] = (1 - BETA_TEMP * exceso).clip(lower=0)

    # Penalización por horas de sol
    horas_max = max(HORAS_SOL_POR_MES.values())
    df["horas_norm"] = df["month"].map(
        lambda m: HORAS_SOL_POR_MES[int(m)] / horas_max
    )

    # Potencial final (0–1) sin hundir los valores
    potencial_base = (
        df["rad_norm"] *
        df["pen_nube"] *
        df["pen_temp"] *      
        df["horas_norm"]
    ).clip(0, 1)

    df["potencial_0_1"] = potencial_base

    # Redondeos
    for col in ["rad_norm", "pen_nube", "pen_temp", "horas_norm", "potencial_0_1"]:
        df[col] = df[col].round(4)

    # 4) EXPORTAR RESULTADOS
    out_csv = carpeta_salida / f"{csv_path.stem}_potencial.csv" 
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
    base = Path("data_Ingesta/csv")
    carpeta_salida_base = Path("data_Ingesta/csv_potencial")

    if not base.exists():
        print("No existe data_Ingesta/csv")
        return

    csvs = sorted(base.rglob("*.csv"))
    print(f"{len(csvs)} CSV encontrados")

    procesados = 0
    saltados = 0

    for csv_path in csvs:
        if csv_path.name.endswith("_potencial.csv"):
            continue

        ruta_relativa = csv_path.relative_to(base).parent
        carpeta_destino_especifica = carpeta_salida_base / ruta_relativa
        carpeta_destino_especifica.mkdir(parents=True, exist_ok=True)

        potencial_csv = carpeta_destino_especifica / f"{csv_path.stem}_potencial.csv"

        if potencial_csv.exists():
            saltados += 1
            continue

        procesar_potencial_csv(csv_path, carpeta_destino_especifica)
        procesados += 1

    print("\n=== RESUMEN ===")
    print(f"Procesados nuevos: {procesados}")
    print(f"Saltados (ya existían): {saltados}")

if __name__ == "__main__":
    procesar_potencial_automatico()