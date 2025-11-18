# src/load_data.py
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

DB_PATH = Path("BaseDeDatos/era5_madrid.db")
CSV_ROOT = Path("data/csv")
BATCH = 50_000

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

UPSERT = text("""
INSERT INTO era5_data (zona_id, valid_time, ssrd_kWhm2, t2m_C, tcc, potencial_0_100)
VALUES (:zona_id, :valid_time, :ssrd_kWhm2, :t2m_C, :tcc, :potencial_0_100)
ON CONFLICT(zona_id, valid_time) DO UPDATE SET
    ssrd_kWhm2      = excluded.ssrd_kWhm2,
    t2m_C           = excluded.t2m_C,
    tcc             = excluded.tcc,
    potencial_0_100 = excluded.potencial_0_100;
""")

def load_csv(path: Path):

    df = pd.read_csv(path)

    needed = {"valid_time","ssrd_kWhm2","t2m_C","tcc","potencial_0_100","tile_id"}
    if not needed.issubset(df.columns):
        print("[SKIP] columnas incompletas:", path)
        return

    df["valid_time"] = pd.to_datetime(df["valid_time"], utc=False).dt.strftime("%Y-%m-%d %H:%M:%S")
    df.rename(columns={"tile_id": "zona_id"}, inplace=True)

    df = df[["zona_id","valid_time","ssrd_kWhm2","t2m_C","tcc","potencial_0_100"]]

    with engine.begin() as con:
        for i in range(0, len(df), BATCH):
            chunk = df.iloc[i:i+BATCH]
            con.execute(UPSERT, chunk.to_dict(orient="records"))

    print("Insertado:", path)

def main():
    if not DB_PATH.exists():
        print("Base no encontrada. Ejecuta primero db_setup.py")
        return

    files = sorted(CSV_ROOT.rglob("*_potencial.csv"))
    print("Encontrados:", len(files), "CSV de potencial")

    if not files:
        print("No hay CSVs *_potencial.csv en data/csv/")
        return

    for f in files:
        load_csv(f)

    print("Carga completada.")

if __name__ == "__main__":
    main()
