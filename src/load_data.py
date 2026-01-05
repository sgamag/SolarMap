# ============================================================
# CARGA DE DATOS DE POTENCIAL EN LA BASE DE DATOS
#
# Este script se encarga de la fase final del pipeline:
#
# 1) Leer los CSV *_potencial.csv generados en el paso anterior
# 2) Insertar o actualizar los datos horarios en la tabla era5_data
#    (UPSERT: no duplica filas)
# 3) Recalcular el potencial medio por tile
#    y almacenarlo en la tabla potencial_tile_resumen
#
# NOTA IMPORTANTE:
# - Este script NO descarga datos
# - Este script NO calcula el potencial físico
# - Este script SOLO carga y resume datos en la base de datos MySQL
#
# Es el puente entre los CSV procesados y la BD.
# ============================================================

from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text


# ------------------------------------------------------------
# CONFIGURACIÓN DE CONEXIÓN A MYSQL
# ------------------------------------------------------------
# Se define la conexión a la base de datos central del proyecto.
# Se usa un usuario específico del proyecto (no root).
# ------------------------------------------------------------

DB_HOST = "localhost"     # En tu portátil: localhost
DB_PORT = 3306
DB_NAME = "era5_madrid"
DB_USER = "era5_user"
DB_PASS = "SolarMap67"    # Contraseña del usuario del proyecto

SQLALCHEMY_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Creamos el engine de SQLAlchemy.
# El engine gestiona conexiones, transacciones y ejecución SQL.
engine = create_engine(SQLALCHEMY_URL, future=True)


# ------------------------------------------------------------
# RUTA DONDE SE ENCUENTRAN LOS CSV DE POTENCIAL
# ------------------------------------------------------------
# Estructura esperada:
# src/data/csv/tile_XX_YY/AAAA/AAAA_MM_potencial.csv
# ------------------------------------------------------------

CSV_ROOT = Path(__file__).resolve().parent / "data" / "csv"


# ------------------------------------------------------------
# TAMAÑO DE LOTE PARA INSERCIONES
# ------------------------------------------------------------
# Insertar muchos registros de golpe puede ser costoso.
# Por eso se insertan en bloques (batch).
# ------------------------------------------------------------

BATCH = 50_000


# ------------------------------------------------------------
# SENTENCIA UPSERT PARA DATOS HORARIOS (era5_data)
# ------------------------------------------------------------
# En MySQL el UPSERT se hace con:
#   ON DUPLICATE KEY UPDATE
#
# La clave primaria de era5_data es:
#   (zona_id, valid_time)
#
# Esto garantiza:
# - Si la fila no existe → se inserta
# - Si ya existe → se actualiza
# ------------------------------------------------------------

UPSERT_ERA5 = text("""
INSERT INTO era5_data (
    zona_id,
    valid_time,
    ssrd_kWhm2,
    t2m_C,
    tcc,
    potencial_climatico
)
VALUES (
    :zona_id,
    :valid_time,
    :ssrd_kWhm2,
    :t2m_C,
    :tcc,
    :potencial_climatico
)
ON DUPLICATE KEY UPDATE
    ssrd_kWhm2          = VALUES(ssrd_kWhm2),
    t2m_C               = VALUES(t2m_C),
    tcc                 = VALUES(tcc),
    potencial_climatico = VALUES(potencial_climatico);
""")


# ------------------------------------------------------------
# CARGA DE UN CSV INDIVIDUAL
# ------------------------------------------------------------
# Esta función:
# - Lee un CSV *_potencial.csv
# - Valida columnas mínimas
# - Normaliza nombres de columnas
# - Inserta/actualiza datos en era5_data
# ------------------------------------------------------------

def load_csv(path: Path):

    # Leemos el CSV de potencial
    df = pd.read_csv(path)

    # Columnas mínimas necesarias
    required = {
        "valid_time",
        "ssrd_kWhm2",
        "t2m_C",
        "tcc",
        "potencial_0_1",
        "tile_id"
    }

    # Si falta alguna columna, no se carga este archivo
    if not required.issubset(df.columns):
        print("[SKIP] Columnas incompletas:", path)
        return

    # --------------------------------------------------------
    # NORMALIZACIÓN DE FECHAS
    # --------------------------------------------------------
    # Convertimos valid_time a formato compatible con MySQL DATETIME
    # --------------------------------------------------------

    df["valid_time"] = (
        pd.to_datetime(df["valid_time"], errors="coerce")
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    # --------------------------------------------------------
    # MAPEO DE NOMBRES CSV → BASE DE DATOS
    # --------------------------------------------------------
    # CSV:
    #   tile_id        → identificador del tile
    #   potencial_0_1  → potencial normalizado
    #
    # BD:
    #   zona_id              → FK a zonas
    #   potencial_climatico  → valor horario
    # --------------------------------------------------------

    df.rename(
        columns={
            "tile_id": "zona_id",
            "potencial_0_1": "potencial_climatico"
        },
        inplace=True
    )

    # Seleccionamos SOLO las columnas que existen en era5_data
    df = df[
        ["zona_id", "valid_time", "ssrd_kWhm2", "t2m_C", "tcc", "potencial_climatico"]
    ]

    # --------------------------------------------------------
    # INSERCIÓN EN BD POR LOTES
    # --------------------------------------------------------
    # Usamos una transacción para asegurar consistencia.
    # --------------------------------------------------------

    with engine.begin() as con:
        for i in range(0, len(df), BATCH):
            chunk = df.iloc[i:i + BATCH]
            con.execute(
                UPSERT_ERA5,
                chunk.to_dict(orient="records")
            )

    print("Insertado en era5_data:", path)


# ------------------------------------------------------------
# ACTUALIZACIÓN DEL RESUMEN POR TILE
# ------------------------------------------------------------
# Recalcula la tabla potencial_tile_resumen:
# - 1 fila por tile
# - media del potencial horario
# - número de registros usados
# ------------------------------------------------------------

def actualizar_resumen_por_tile():

    print("Actualizando potencial_tile_resumen (media)...")

    # Leemos solo lo necesario de la tabla grande
    df = pd.read_sql_query(
        "SELECT zona_id, potencial_climatico FROM era5_data",
        engine
    )

    # Si no hay datos, no hacemos nada
    if df.empty:
        print("No hay datos para resumir.")
        return

    # --------------------------------------------------------
    # AGREGACIÓN POR TILE
    # --------------------------------------------------------
    resumen = (
        df.groupby("zona_id")["potencial_climatico"]
          .agg(
              potencial_medio="mean",
              n_registros="count"
          )
          .reset_index()
    )

    # Timestamp de actualización
    resumen["last_updated"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    # --------------------------------------------------------
    # UPSERT DEL RESUMEN EN MYSQL
    # --------------------------------------------------------

    UPSERT_RESUMEN = text("""
        INSERT INTO potencial_tile_resumen (
            zona_id,
            potencial_medio,
            n_registros,
            last_updated
        )
        VALUES (
            :zona_id,
            :potencial_medio,
            :n_registros,
            :last_updated
        )
        ON DUPLICATE KEY UPDATE
            potencial_medio = VALUES(potencial_medio),
            n_registros     = VALUES(n_registros),
            last_updated    = VALUES(last_updated);
    """)

    with engine.begin() as con:
        con.execute(
            UPSERT_RESUMEN,
            resumen.to_dict(orient="records")
        )

    print("potencial_tile_resumen actualizada.")


# ------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# ------------------------------------------------------------
# Orquesta la carga completa:
# 1) Localiza todos los *_potencial.csv
# 2) Los carga en era5_data
# 3) Recalcula el resumen final
# ------------------------------------------------------------

def main():

    # Buscamos todos los CSV de potencial existentes
    files = sorted(CSV_ROOT.rglob("*_potencial.csv"))

    print(f"Encontrados {len(files)} CSV de potencial.")

    # Si no hay CSV, no hay nada que cargar
    if not files:
        print("No hay CSV *_potencial.csv para cargar.")
        return

    # Cargamos cada CSV individual
    for f in files:
        load_csv(f)

    # Actualizamos el resumen al final
    actualizar_resumen_por_tile()

    print("Carga completada correctamente.")


# ------------------------------------------------------------
# EJECUCIÓN DEL SCRIPT
# ------------------------------------------------------------

if __name__ == "__main__":
    main()
