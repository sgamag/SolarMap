# src/ver_db.py
import sqlite3
import pandas as pd
from pathlib import Path

# ---------- Ruta de la base de datos ----------
DB_PATH = Path("data/era5_madrid.db")

if not DB_PATH.exists():
    print(f"⚠️ No se encontró la base de datos en {DB_PATH.resolve()}")
    print("Ejecuta primero 'python src/db_setup.py' para crearla.")
else:
    print(f"Conectando a la base de datos: {DB_PATH.resolve()}")

    # ---------- Conexión con la base ----------
    conn = sqlite3.connect(DB_PATH)

    # ---------- Ver las tablas existentes ----------
    tablas = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table';", conn
    )
    print("\n📋 Tablas en la base de datos:")
    print(tablas)

    # ---------- Mostrar las primeras filas de la tabla 'zonas' ----------
    if "zonas" in tablas["name"].values:
        df_zonas = pd.read_sql_query("SELECT * FROM zonas LIMIT 10;", conn)
        print("\n🗺️ Primeras filas de 'zonas':")
        print(df_zonas)
    else:
        print("\n⚠️ La tabla 'zonas' no existe todavía.")

    # ---------- Mostrar si 'era5_data' tiene algo ----------
    if "era5_data" in tablas["name"].values:
        n = pd.read_sql_query("SELECT COUNT(*) AS filas FROM era5_data;", conn)
        print(f"\n📊 La tabla 'era5_data' tiene {n.loc[0, 'filas']} filas.")
    else:
        print("\n⚠️ La tabla 'era5_data' no existe todavía.")

    # ---------- Cerrar conexión ----------
    conn.close()
    print("\n✅ Conexión cerrada.")
