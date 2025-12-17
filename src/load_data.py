# ============================================================
# CARGA DE DATOS DE POTENCIAL EN LA BASE DE DATOS
#
# Este script:
# 1) Inserta / actualiza datos horarios en 'era5_data'
# 2) Recalcula la media del potencial por tile
#    y la guarda en 'potencial_tile_resumen'
#
# NOTA:
# - No se usan medianas ni percentiles para mantener
#   compatibilidad con SQLite.
# ============================================================

from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

# ------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------

DB_PATH = Path("BaseDeDatos/era5_madrid.db")

# Los CSV *_potencial.csv están en:
# src/data/csv/tile_xx_yy/AAAA/potencial/
CSV_ROOT = Path(__file__).resolve().parent / "data" / "csv"

BATCH = 50_000

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

# ------------------------------------------------------------
# UPSERT DE DATOS HORARIOS
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
ON CONFLICT(zona_id, valid_time) DO UPDATE SET
    ssrd_kWhm2          = excluded.ssrd_kWhm2,
    t2m_C               = excluded.t2m_C,
    tcc                 = excluded.tcc,
    potencial_climatico = excluded.potencial_climatico;
""")

# ------------------------------------------------------------
# CARGA DE UN CSV INDIVIDUAL
# ------------------------------------------------------------

def load_csv(path: Path):
    df = pd.read_csv(path)

    required = {
        "valid_time",
        "ssrd_kWhm2",
        "t2m_C",
        "tcc",
        "potencial_0_1",
        "tile_id"
    }

    if not required.issubset(df.columns):
        print("[SKIP] Columnas incompletas:", path)
        return

    df["valid_time"] = (
        pd.to_datetime(df["valid_time"], errors="coerce")
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    df.rename(
        columns={
            "tile_id": "zona_id",
            "potencial_0_1": "potencial_climatico"
        },
        inplace=True
    )

    df = df[
        ["zona_id", "valid_time", "ssrd_kWhm2", "t2m_C", "tcc", "potencial_climatico"]
    ]

    with engine.begin() as con:
        for i in range(0, len(df), BATCH):
            chunk = df.iloc[i:i + BATCH]
            con.execute(UPSERT_ERA5, chunk.to_dict(orient="records"))

    print("Insertado en era5_data:", path)

# ------------------------------------------------------------
# ACTUALIZACIÓN DEL RESUMEN POR TILE (MEDIA)
# ------------------------------------------------------------

def actualizar_resumen_por_tile():
    print("Actualizando potencial_tile_resumen (media)...")

    df = pd.read_sql_query(
        "SELECT zona_id, potencial_climatico FROM era5_data",
        engine
    )

    if df.empty:
        print("No hay datos para resumir.")
        return

    resumen = (
        df.groupby("zona_id")["potencial_climatico"]
          .agg(
              potencial_medio="mean",
              n_registros="count"
          )
          .reset_index()
    )

    resumen["last_updated"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

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
        ON CONFLICT(zona_id) DO UPDATE SET
            potencial_medio = excluded.potencial_medio,
            n_registros     = excluded.n_registros,
            last_updated    = excluded.last_updated;
    """)

    with engine.begin() as con:
        con.execute(
            UPSERT_RESUMEN,
            resumen.to_dict(orient="records")
        )

    print("potencial_tile_resumen actualizada.")

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    if not DB_PATH.exists():
        print("Base de datos no encontrada. Ejecuta primero db_setup.py")
        return

    files = sorted(CSV_ROOT.rglob("potencial/*_potencial.csv"))

    print(f"Encontrados {len(files)} CSV de potencial.")

    if not files:
        print("No hay CSV *_potencial.csv para cargar.")
        return

    for f in files:
        load_csv(f)

    actualizar_resumen_por_tile()

    print("Carga completada correctamente.")

# ------------------------------------------------------------
# EJECUCIÓN
# ------------------------------------------------------------

if __name__ == "__main__":
    main()
