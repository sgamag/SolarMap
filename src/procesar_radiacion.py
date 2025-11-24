"""
Procesamiento avanzado de potencial solar horario (0–100).
Este script toma un CSV por tile con:
- ssrd_kWhm2   (radiación solar acumulada en kWh/m²)
- t2m_C        (temperatura en 2 metros)
- tcc          (nubosidad 0–1)
- valid_time   (fecha-hora)

Y genera un índice robusto de potencial solar para paneles fotovoltaicos,
combinando normalización dinámica, penalización por nubosidad y efectos térmicos.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


# =======================================================================
#   PARÁMETROS DEL MODELO FOTOVOLTAICO
# =======================================================================
# Estos parámetros NO son arbitrarios: provienen de modelos reales
# de irradiancia, física de paneles solares y literatura energética.
# Se definen aquí arriba para facilitar su modificación.
# =======================================================================

# Percentil dinámico para normalizar radiación según mes.
# Motivo: la dispersión de la radiación varía mucho por estación.
# - Invierno: radiación baja y homogénea → percentil más bajo (P90–P92)
# - Verano: radiación muy variable → percentil más alto (P95–P97)

PERC_POR_MES = {
    1: 0.90,  2: 0.92,  3: 0.94,
    4: 0.95,  5: 0.96,  6: 0.97,
    7: 0.97,  8: 0.96,  9: 0.95,
    10: 0.94, 11: 0.93, 12: 0.92,
}

# límite superior para radiación normalizada (evita que un valor extremo distorsione)
CAP_GHI = 1.20

# Exponente para penalización por nubosidad (curva no lineal)
ALFA_NUBES = 0.90

# Temperatura base de referencia
TEMP_BASE = 25.0

# Coeficiente térmico real de paneles fotovoltaicos (~0.4% pérdida por °C)
BETA_TEMP = 0.004


# =======================================================================
#   FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# =======================================================================
# Toma el CSV original y genera:
# - CSV con columnas procesadas
# - potencial_0_100 basado en radiación, nubes y temperatura
# - opcionalmente, gráfico del potencial horario
#
# Este es el módulo que realmente usará pipeline tras la conversión GRIB→CSV.
# =======================================================================

def procesar_potencial_csv(csv_path: str, guardar_grafico: bool = False):
    """
    Procesa un CSV con ssrd, t2m y tcc para generar un índice horario de potencial solar.
    """

    # -------------------------------
    # Validación de entrada
    # -------------------------------
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {csv_path}")

    print(f"Procesando archivo: {csv_path}")
    df = pd.read_csv(csv_path)

    # Normalizamos nombres de columnas
    df.columns = [c.strip() for c in df.columns]

    # Comprobación estricta de columnas obligatorias
    columnas_esperadas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}
    faltan = columnas_esperadas - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas obligatorias: {faltan}")


    # =======================================================================
    #   BLOQUE 1: LIMPIEZA Y CONVERSIÓN DE TIPOS
    # =======================================================================
    # - Se ajustan tipos de datos.
    # - Se corrige nubosidad 0–100.
    # - Se eliminan fechas inválidas.
    # =======================================================================

    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce", utc=False)
    df = df.dropna(subset=["valid_time"])

    df["t2m_C"] = pd.to_numeric(df["t2m_C"], errors="coerce")
    df["tcc"] = pd.to_numeric(df["tcc"], errors="coerce").clip(lower=0)
    df["ssrd_kWhm2"] = pd.to_numeric(df["ssrd_kWhm2"], errors="coerce").clip(lower=0)

    # Si la nubosidad viene en porcentaje, la convertimos a 0–1
    if df["tcc"].max() > 1:
        df["tcc"] = df["tcc"] / 100.0

    # Columnas auxiliares para agrupación por mes
    df["year"] = df["valid_time"].dt.year
    df["month"] = df["valid_time"].dt.month

    df = df.sort_values("valid_time")


    # =======================================================================
    #   BLOQUE 2: NORMALIZACIÓN DINÁMICA DE LA RADIACIÓN SOLAR
    # =======================================================================
    # - Se calcula un percentil mensual adaptativo (P90–P97 según el mes).
    # - Esto hace que el índice final sea robusto a estaciones diferentes
    #   y evita que un mes de invierno tenga valores artificialmente bajos
    #   respecto a uno de verano.
    # =======================================================================

    df["percentil_mes"] = df["month"].map(PERC_POR_MES)

    pXX = (
        df.groupby(["year", "month"])
          .apply(lambda g: g["ssrd_kWhm2"].quantile(g["percentil_mes"].iloc[0]))
          .rename("pXX_mes")
    )

    df = df.merge(pXX, on=["year", "month"], how="left")

    # Previene divisiones por cero
    mediana_global = df["ssrd_kWhm2"].median()
    df["pXX_mes"] = df["pXX_mes"].replace(0, mediana_global if mediana_global > 0 else 1e-6)

    # Radiación normalizada con límite superior
    df["ghi_norm"] = (df["ssrd_kWhm2"] / df["pXX_mes"]).clip(upper=CAP_GHI)


    # =======================================================================
    #   BLOQUE 3: COMPONENTES DEL ÍNDICE (NUBES + TEMPERATURA)
    # =======================================================================
    # 1) Penalización por nubosidad
    #    - Curva no lineal: (1 - tcc)^ALFA
    #    - Más realista que una penalización lineal pura
    #
    # 2) Penalización térmica
    #    - Los paneles pierden rendimiento si t2m supera 25°C
    #    - Caída: 0.4% por °C
    # =======================================================================

    df["pen_nube"] = (1 - df["tcc"]).clip(lower=0) ** ALFA_NUBES

    exceso_temp = (df["t2m_C"] - TEMP_BASE).clip(lower=0)
    df["pen_temp"] = (1 - BETA_TEMP * exceso_temp).clip(lower=0)


    # =======================================================================
    #   BLOQUE 4: ÍNDICE FINAL 0–100
    # =======================================================================

    df["potencial_0_100"] = (
        100 * df["ghi_norm"] * df["pen_nube"] * df["pen_temp"]
    ).clip(0, 100)

    # Redondeo final
    for col in ["ssrd_kWhm2", "t2m_C", "tcc", "potencial_0_100"]:
        df[col] = df[col].round(2)


    # =======================================================================
    #   BLOQUE 5: SELECCIÓN Y EXPORTACIÓN DE RESULTADOS
    # =======================================================================

    columnas_salida = [
        c for c in ["valid_time", "tile_id", "latitude", "longitude"] if c in df.columns
    ]
    columnas_salida += ["ssrd_kWhm2", "t2m_C", "tcc", "potencial_0_100"]

    df_out = df[columnas_salida].copy()

    out_csv = csv_path.with_name(csv_path.stem + "_potencial.csv")
    df_out.to_csv(out_csv, index=False)

    print(f"CSV generado: {out_csv}")

    return df_out


# =======================================================================
#   NUEVO BLOQUE: PROCESAR POTENCIAL POR AÑOS
# =======================================================================

def procesar_potencial_por_años():
    """
    Pide año inicial y año final por consola,
    recorre data/csv,
    y procesa todos los CSV dentro de esos años.
    """

    print("=== PROCESAR POTENCIAL POR AÑOS ===")

    año_inicial = int(input("Año inicial a procesar: "))
    año_final = int(input("Año final a procesar: "))

    carpeta_csv = Path("data/csv")

    if not carpeta_csv.exists():
        print("La carpeta data/csv no existe.")
        return

    archivos = sorted(carpeta_csv.rglob("*.csv"))

    if not archivos:
        print("No se encontraron CSV para procesar.")
        return

    print(f"Se han encontrado {len(archivos)} CSV. Procesando rango {año_inicial}–{año_final}.")

    for archivo in archivos:

        # Extraer el año desde la carpeta padre (tile_xx_xx/AÑO/)
        try:
            año = int(archivo.parent.name)
        except:
            continue

        # Filtrar por rango seleccionado
        if año < año_inicial or año > año_final:
            continue

        # Saltar archivos ya procesados
        if archivo.name.endswith("_potencial.csv"):
            continue

        procesar_potencial_csv(archivo)


# =======================================================================
#   EJECUCIÓN DIRECTA DESDE TERMINAL
# =======================================================================

if __name__ == "__main__":
    procesar_potencial_por_años()
