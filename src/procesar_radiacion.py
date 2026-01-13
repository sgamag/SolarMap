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
# En este bloque fijamos constantes del modelo. Son "hiperparámetros" físicos
# simplificados para convertir variables climáticas en un índice 0–1.
#
# Nota: este modelo busca ser consistente y defendible, no un modelo fotovoltaico
# de ingeniería de detalle. La idea es disponer de un indicador comparativo por tile.
# =======================================================================

# Horas de sol medias aproximadas por mes (para estacionalidad).
# Se usan para reducir el potencial en meses con menos horas de luz.
HORAS_SOL_POR_MES = {
    1: 9.3,  2: 10.0, 3: 11.9, 4: 13.3,
    5: 14.5, 6: 16.8, 7: 15.7, 8: 15.1,
    9: 13.0, 10: 12.4, 11: 10.8, 12: 9.0
}

# Exponente de la penalización por nubes.
# Cuanto mayor, más agresiva la caída del potencial cuando aumenta tcc.
ALFA_NUBES    = 0.90

# Temperatura "base" a partir de la cual penalizamos (en ºC).
# Por debajo de TEMP_BASE no hay penalización térmica.
TEMP_BASE     = 25.0

# Sensibilidad térmica: cuánto baja el potencial por cada grado por encima de TEMP_BASE.
BETA_TEMP     = 0.004

# Radiación de referencia (kWh/m²) para normalizar.
# Si REF_RADIACION=1.0, interpretamos ssrd_kWhm2 como ya "en escala 0–1" al recortar.
REF_RADIACION = 1.0


# =======================================================================
# PROCESAR CSV INDIVIDUAL
# =======================================================================
# Esta función hace el trabajo "físico" sobre un solo fichero:
# - Lee CSV de entrada
# - Limpia tipos y valores
# - Calcula variables intermedias y potencial final
# - Escribe un CSV de salida en la MISMA carpeta con sufijo _potencial.csv
# =======================================================================

def procesar_potencial_csv(csv_path: Path):
    """
    Procesa un CSV limpio (un tile y un mes típicamente) y genera el CSV
    con columnas adicionales:
    - rad_norm, pen_nube, pen_temp, horas_norm, potencial_0_1

    Entrada esperada (mínimo):
    - valid_time, ssrd_kWhm2, t2m_C, tcc

    Salida:
    - <mismo_nombre>_potencial.csv en la misma carpeta que el input.
    """

    print("Procesando:", csv_path)

    # -----------------------------------------------------------
    # 1) LECTURA Y VALIDACIÓN DE COLUMNAS
    # -----------------------------------------------------------
    df = pd.read_csv(csv_path)

    # A veces los CSV vienen con espacios accidentales en nombres de columnas.
    df.columns = [c.strip() for c in df.columns]

    # Comprobamos que el CSV tiene lo mínimo necesario para el modelo.
    requeridas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}
    if not requeridas.issubset(df.columns):
        raise ValueError(f"CSV incompleto: {csv_path}")

    # -----------------------------------------------------------
    # 2) LIMPIEZA DE TIPOS Y VALORES
    # -----------------------------------------------------------

    # valid_time: lo convertimos a datetime; si falla, queda NaT.
    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce")

    # Eliminamos filas sin fecha válida (sin tiempo no podemos calcular month ni ordenar).
    df = df.dropna(subset=["valid_time"])

    # Radiación: numérico y no negativo (clip lower=0).
    df["ssrd_kWhm2"] = pd.to_numeric(df["ssrd_kWhm2"], errors="coerce").clip(lower=0)

    # Temperatura: numérico. No recortamos por arriba/abajo porque la penalización
    # ya maneja el exceso, pero si hay NaN quedará como NaN.
    df["t2m_C"] = pd.to_numeric(df["t2m_C"], errors="coerce")

    # Nubosidad: numérico y forzamos el rango [0,1].
    df["tcc"] = pd.to_numeric(df["tcc"], errors="coerce").clip(0, 1)

    # Obtenemos el mes (1..12) desde la fecha para la penalización estacional.
    df["month"] = df["valid_time"].dt.month

    # Orden temporal consistente (por si vienen filas desordenadas).
    df = df.sort_values("valid_time").reset_index(drop=True)

    # ============================================================
    # 3) MODELO FÍSICO (CÁLCULO DE COMPONENTES)
    # ============================================================

    # -----------------------------------------------------------
    # 3.1 Radiación normalizada (0–1)
    # -----------------------------------------------------------
    # Normalizamos respecto a una referencia y recortamos a [0,1].
    # Si REF_RADIACION=1, todo valor >=1 se satura en 1.
    df["rad_norm"] = (df["ssrd_kWhm2"] / REF_RADIACION).clip(0, 1)

    # -----------------------------------------------------------
    # 3.2 Penalización por nubosidad
    # -----------------------------------------------------------
    # Si tcc=0 (cielo despejado) => pen_nube=1
    # Si tcc=1 (completamente cubierto) => pen_nube=0
    # Exponente ALFA_NUBES ajusta la curva.
    df["pen_nube"] = (1 - df["tcc"]).clip(lower=0) ** ALFA_NUBES

    # -----------------------------------------------------------
    # 3.3 Penalización térmica
    # -----------------------------------------------------------
    # Solo penalizamos cuando T > TEMP_BASE.
    # exceso = max(T - TEMP_BASE, 0)
    exceso = (df["t2m_C"] - TEMP_BASE).clip(lower=0)

    # pen_temp = 1 - BETA_TEMP * exceso, recortado a [0, +inf)
    # (si hace muchísimo calor, podría bajar a 0).
    df["pen_temp"] = (1 - BETA_TEMP * exceso).clip(lower=0)

    # -----------------------------------------------------------
    # 3.4 Penalización por horas de sol (estacionalidad mensual)
    # -----------------------------------------------------------
    # Normalizamos horas de sol del mes respecto al máximo del año.
    horas_max = max(HORAS_SOL_POR_MES.values())

    # Mapeamos month -> horas/horas_max.
    # Se usa lambda para convertir m a int y acceder al dict.
    df["horas_norm"] = df["month"].map(
        lambda m: HORAS_SOL_POR_MES[int(m)] / horas_max
    )

    # -----------------------------------------------------------
    # 3.5 Potencial final (0–1)
    # -----------------------------------------------------------
    # Producto de los factores (energía * penalizaciones).
    # Recortamos a [0,1] para mantener escala.
    df["potencial_0_1"] = (
        df["rad_norm"] *
        df["pen_nube"] *
        df["pen_temp"] *
        df["horas_norm"]
    ).clip(0, 1)

    # -----------------------------------------------------------
    # 3.6 Redondeos (para estabilidad y tamaño de CSV)
    # -----------------------------------------------------------
    # Redondeamos componentes y salida final a 4 decimales.
    for col in ["rad_norm", "pen_nube", "pen_temp", "horas_norm", "potencial_0_1"]:
        df[col] = df[col].round(4)

    # ============================================================
    # 4) EXPORTAR RESULTADOS
    # ============================================================
    # Guardamos el CSV en la MISMA carpeta que el CSV de entrada
    # para mantener la estructura tile/año.
    # ============================================================

    # Ruta de salida: mismo nombre + sufijo _potencial.csv
    out_csv = csv_path.parent / f"{csv_path.stem}_potencial.csv"

    # Columnas a guardar: mantenemos las climáticas y añadimos las calculadas.
    # Incluimos tile_id/lat/lon si existen en el CSV original.
    columnas_salida = [
        "valid_time",
        *[c for c in ["tile_id", "latitude", "longitude"] if c in df.columns],
        "ssrd_kWhm2", "t2m_C", "tcc",
        "rad_norm", "pen_nube", "pen_temp",
        "horas_norm", "potencial_0_1",
    ]

    # Exportamos a CSV sin índice.
    df[columnas_salida].to_csv(out_csv, index=False)

    print("  → generado:", out_csv.name)


# =======================================================================
# PROCESO AUTOMÁTICO COMPLETO
# =======================================================================
# Este bloque automatiza el procesamiento:
# - Busca todos los .csv en data/csv
# - Ignora los que ya son _potencial.csv
# - Para cada CSV limpio, comprueba si su salida ya existe
# - Si existe: lo salta (pipeline idempotente)
# - Si no existe: procesa y genera el _potencial.csv
# =======================================================================

def procesar_potencial_automatico():
    """
    Ejecuta el procesamiento en modo automático:
    - no pide años
    - se guía por lo que existe en disco
    - solo calcula lo faltante
    """

    base = Path("data/csv")

    # Si la carpeta base no existe, no hay nada que procesar.
    if not base.exists():
        print("No existe data/csv")
        return

    # Recorremos recursivamente todos los CSV.
    csvs = sorted(base.rglob("*.csv"))

    print(f"{len(csvs)} CSV encontrados")

    procesados = 0
    saltados = 0

    for csv_path in csvs:

        # -------------------------------------------------------
        # 1) Saltar los CSV que ya son resultado (_potencial)
        # -------------------------------------------------------
        if csv_path.name.endswith("_potencial.csv"):
            continue

        # -------------------------------------------------------
        # 2) Determinar cuál sería el archivo de salida esperado
        # -------------------------------------------------------
        potencial_csv = csv_path.parent / f"{csv_path.stem}_potencial.csv"

        # Si ya existe, no lo recalculamos (idempotencia).
        if potencial_csv.exists():
            saltados += 1
            continue

        # -------------------------------------------------------
        # 3) Si no existe, procesamos el CSV limpio
        # -------------------------------------------------------
        procesar_potencial_csv(csv_path)
        procesados += 1

    # -----------------------------------------------------------
    # Resumen final de ejecución
    # -----------------------------------------------------------
    print("\n=== RESUMEN ===")
    print(f"Procesados nuevos: {procesados}")
    print(f"Saltados (ya existían): {saltados}")


# =======================================================================
# EJECUCIÓN
# =======================================================================

if __name__ == "__main__":
    procesar_potencial_automatico()
