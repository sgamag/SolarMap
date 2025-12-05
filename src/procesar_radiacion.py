"""
Procesamiento avanzado de potencial solar horario (0–1).

Este script toma un CSV por tile con columnas:
- ssrd_kWhm2   (radiación solar acumulada por hora en kWh/m²)
- t2m_C        (temperatura del aire a 2 metros)
- tcc          (nubosidad, en 0–1 o 0–100)
- valid_time   (fecha-hora)

Y genera un índice horario de potencial solar entre 0 y 1, combinando:
- Radiación desestacionalizada (corrigiendo por horas de sol del mes)
- Normalización robusta a partir del percentil 95
- Penalización por nubosidad
- Penalización por temperatura

Salida:
- CSV en carpeta /potencial/ con:
    - valid_time
    - tile_id, latitude, longitude (si están en el CSV)
    - ssrd_kWhm2, t2m_C, tcc
    - horas_norm
    - ghi_norm       (radiación normalizada 0–1)
    - pen_nube
    - pen_temp
    - potencial_0_1  (métrica principal 0–1)
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


# =======================================================================
#   PARÁMETROS DEL MODELO FOTOVOLTAICO
# =======================================================================

# Horas medias de sol por mes (aproximación estable, no depende del año)
HORAS_SOL_POR_MES = {
    1: 9.3,   2: 10.0,  3: 11.9,  4: 13.3,
    5: 14.5,  6: 16.8,  7: 15.7,  8: 15.1,
    9: 13.0, 10: 12.4, 11: 10.8, 12: 9.0
}

# Exponente para penalización por nubosidad (curva suave)
ALFA_NUBES = 0.90

# Penalización térmica
TEMP_BASE = 25.0     # temperatura a partir de la cual pierde eficiencia
BETA_TEMP = 0.004    # ~0.4% de pérdida por ºC adicional


# =======================================================================
#   FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# =======================================================================

def procesar_potencial_csv(csv_path: str, guardar_grafico: bool = False):
    """
    Procesa un CSV con ssrd_kWhm2, t2m_C y tcc para generar potencial solar 0–1.
    """

    # -------------------------------
    # Validación de entrada
    # -------------------------------
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {csv_path}")

    print(f"Procesando archivo: {csv_path}")
    df = pd.read_csv(csv_path)

    # Limpieza de nombres de columnas
    df.columns = [c.strip() for c in df.columns]

    columnas_esperadas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}
    faltan = columnas_esperadas - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas obligatorias: {faltan}")

    # ===================================================================
    #   BLOQUE 1: LIMPIEZA Y TIPOS
    # ===================================================================
    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce")
    df = df.dropna(subset=["valid_time"])

    df["ssrd_kWhm2"] = pd.to_numeric(df["ssrd_kWhm2"], errors="coerce").clip(lower=0)
    df["t2m_C"] = pd.to_numeric(df["t2m_C"], errors="coerce")
    df["tcc"] = pd.to_numeric(df["tcc"], errors="coerce").clip(lower=0)

    # Nubosidad 0–100 → 0–1
    if df["tcc"].max() > 1:
        df["tcc"] = df["tcc"] / 100.0

    # Columnas temporales internas
    df["year"] = df["valid_time"].dt.year
    df["month"] = df["valid_time"].dt.month

    # Orden temporal
    df = df.sort_values("valid_time").reset_index(drop=True)


    # ===================================================================
    #   BLOQUE 2: NORMALIZACIÓN DE LA RADIACIÓN (0–1)
    # ===================================================================
    # Objetivo:
    #   - Ajustar por estación (más/menos horas de sol según el mes)
    #   - Normalizar de forma robusta entre 0 y 1 usando el percentil 95
    #
    # Pasos:
    #   1) horas_norm: factor mensual 0–1 según horas de sol
    #   2) ssrd_corr = ssrd_kWhm2 / horas_norm  (desestacionaliza)
    #   3) ref_max   = P95(ssrd_corr)
    #   4) ghi_norm  = ssrd_corr / ref_max, limitado a [0,1]
    # ===================================================================

    # 1) Horas solares normalizadas (0–1)
    max_horas = max(HORAS_SOL_POR_MES.values())
    df["horas_norm"] = df["month"].map(lambda m: HORAS_SOL_POR_MES[int(m)] / max_horas)

    # Evitar divisiones por cero
    df["horas_norm"] = df["horas_norm"].replace(0, 1e-6)

    # 2) Radiación desestacionalizada
    df["ssrd_corr"] = df["ssrd_kWhm2"] / df["horas_norm"]

    # 3) Referencia robusta: percentil 95 de ssrd_corr
    ref_max = df["ssrd_corr"].quantile(0.95)
    if ref_max <= 0 or pd.isna(ref_max):
        ref_max = max(df["ssrd_corr"].median(), 1e-6)

    # 4) Radiación normalizada 0–1
    df["ghi_norm"] = (df["ssrd_corr"] / ref_max).clip(0, 1)


    # ===================================================================
    #   BLOQUE 3: PENALIZACIÓN POR NUBES + TEMPERATURA
    # ===================================================================

    # Penalización por nubosidad (0 = muy nuboso, 1 = despejado)
    df["pen_nube"] = (1 - df["tcc"]).clip(lower=0) ** ALFA_NUBES

    # Penalización térmica (solo penaliza si t2m_C > TEMP_BASE)
    exceso_temp = (df["t2m_C"] - TEMP_BASE).clip(lower=0)
    df["pen_temp"] = (1 - BETA_TEMP * exceso_temp).clip(lower=0)


    # ===================================================================
    #   BLOQUE 4: POTENCIAL FINAL 0–1
    # ===================================================================
    # Como cada componente está en [0,1], el producto también lo está:
    #   - ghi_norm ∈ [0,1]
    #   - pen_nube ∈ [0,1]
    #   - pen_temp ∈ [0,1]
    # ⇒ potencial_0_1 ∈ [0,1]
    # ===================================================================

    df["potencial_0_1"] = (
        df["ghi_norm"] *
        df["pen_nube"] *
        df["pen_temp"]
    ).clip(0, 1)

    # Redondeo
    for col in ["ssrd_kWhm2", "t2m_C", "tcc",
                "horas_norm", "ghi_norm", "pen_nube", "pen_temp", "potencial_0_1"]:
        df[col] = df[col].round(4)


    # ===================================================================
    #   BLOQUE 5: EXPORTACIÓN A CSV (carpeta /potencial/)
    # ===================================================================

    out_folder = csv_path.parent / "potencial"
    out_folder.mkdir(exist_ok=True)

    out_csv = out_folder / f"{csv_path.stem}_potencial.csv"

    columnas_salida = [
        "valid_time",
        *[c for c in ["tile_id", "latitude", "longitude"] if c in df.columns],
        "ssrd_kWhm2", "t2m_C", "tcc",
        "horas_norm",
        "ghi_norm", "pen_nube", "pen_temp",
        "potencial_0_1",
    ]

    df[columnas_salida].to_csv(out_csv, index=False)
    print(f"CSV generado: {out_csv}")


    # ===================================================================
    #   GRÁFICO OPCIONAL
    # ===================================================================
    if guardar_grafico:
        try:
            plt.figure(figsize=(12, 4))
            plt.plot(df["valid_time"], df["potencial_0_1"])
            plt.xlabel("Fecha-hora")
            plt.ylabel("Potencial 0–1")
            plt.title(f"Potencial horario - {csv_path.stem}")
            plt.tight_layout()

            png_path = out_csv.with_suffix(".png")
            plt.savefig(png_path, dpi=150)
            plt.close()
            print(f"Gráfico generado: {png_path}")
        except Exception as e:
            print("No se pudo generar gráfico:", e)

    return df



# =======================================================================
#   BLOQUE 6: PROCESAR POTENCIAL POR AÑOS
# =======================================================================

def procesar_potencial_por_años():
    """
    Procesa todos los CSV en data/csv/tile_xx_yy/AÑO/ dentro del rango pedido.
    """
    print("=== PROCESAR POTENCIAL POR AÑOS ===")
    ai = int(input("Año inicial a procesar: "))
    af = int(input("Año final a procesar: "))

    carpeta_csv = Path("data/csv")
    if not carpeta_csv.exists():
        print("La carpeta data/csv no existe.")
        return

    archivos = sorted(carpeta_csv.rglob("*.csv"))
    print(f"Encontrados {len(archivos)} CSV. Procesando {ai}-{af}...")

    for archivo in archivos:

        # Extrae el año desde la carpeta tile_xx_yy/2000/
        try:
            year = int(archivo.parent.name)
        except Exception:
            continue

        if not (ai <= year <= af):
            continue

        if archivo.name.endswith("_potencial.csv"):
            continue

        procesar_potencial_csv(archivo)



# =======================================================================
#   EJECUCIÓN DIRECTA
# =======================================================================

if __name__ == "__main__":
    procesar_potencial_por_años()
