# ============================================================
# VISUALIZACIÓN Y VALIDACIÓN DE LA BASE DE DATOS SQLite
#
# Este script sirve para:
# - Conectarse a la base de datos del proyecto
# - Ver qué tablas existen
# - Mostrar las primeras filas de cada tabla
# - Ver número de filas y columnas
# - Calcular estadísticos básicos (media, mediana, etc.)
#
# Es una herramienta de inspección y depuración,
# NO modifica la base de datos.
# ============================================================

import sqlite3
import pandas as pd
from pathlib import Path

# ============================================================
# RUTA DE LA BASE DE DATOS
# ============================================================

DB_PATH = Path("src/BaseDeDatos/era5_madrid.db")

if not DB_PATH.exists():
    print(f"No se encontró la base de datos en {DB_PATH.resolve()}")
    print("Ejecuta primero 'python src/db_setup.py' para crearla.")
    exit(1)

print(f"Conectando a la base de datos: {DB_PATH.resolve()}")

# ============================================================
# CONEXIÓN A SQLITE
# ============================================================

conn = sqlite3.connect(DB_PATH)

# ============================================================
# OBTENER TABLAS EXISTENTES
# ============================================================

tablas = pd.read_sql_query(
    "SELECT name FROM sqlite_master WHERE type='table';",
    conn
)

print("\nTablas existentes en la base de datos:")
print(tablas)

# ============================================================
# FUNCIÓN AUXILIAR PARA INSPECCIONAR UNA TABLA
# ============================================================

def inspeccionar_tabla(nombre_tabla: str, n_filas: int = 5):
    """
    Muestra información básica de una tabla:
    - número de filas
    - número de columnas
    - primeras filas
    - estadísticas descriptivas (si aplica)
    """

    print("\n" + "=" * 60)
    print(f"Tabla: {nombre_tabla}")
    print("=" * 60)

    # Número de filas
    df_count = pd.read_sql_query(
        f"SELECT COUNT(*) AS filas FROM {nombre_tabla};",
        conn
    )
    n_rows = df_count.loc[0, "filas"]
    print(f"Número de filas: {n_rows}")

    # Cargar una muestra de la tabla
    df = pd.read_sql_query(
        f"SELECT * FROM {nombre_tabla} LIMIT {n_filas};",
        conn
    )

    print(f"Número de columnas: {df.shape[1]}")
    print("\nPrimeras filas:")
    print(df)

    # Estadísticos básicos si hay columnas numéricas
    columnas_numericas = df.select_dtypes(include="number").columns

    if len(columnas_numericas) > 0:
        print("\nEstadísticos básicos (describe):")
        df_full = pd.read_sql_query(
            f"SELECT * FROM {nombre_tabla};",
            conn
        )
        print(df_full[columnas_numericas].describe())

        # Estadísticos adicionales relevantes
        print("\nEstadísticos adicionales:")
        for col in columnas_numericas:
            print(f"\nColumna: {col}")
            print(f"  Media:     {df_full[col].mean():.4f}")
            print(f"  Mediana:   {df_full[col].median():.4f}")
            print(f"  Percentil 90: {df_full[col].quantile(0.90):.4f}")
            print(f"  Percentil 95: {df_full[col].quantile(0.95):.4f}")
    else:
        print("\nLa tabla no contiene columnas numéricas para análisis.")

# ============================================================
# INSPECCIÓN DE CADA TABLA RELEVANTE
# ============================================================

nombres_tablas = tablas["name"].tolist()

if "zonas" in nombres_tablas:
    inspeccionar_tabla("zonas")

if "era5_data" in nombres_tablas:
    inspeccionar_tabla("era5_data")

if "potencial_tile_resumen" in nombres_tablas:
    inspeccionar_tabla("potencial_tile_resumen")

# ============================================================
# CIERRE DE CONEXIÓN
# ============================================================

conn.close()
print("\nConexión cerrada correctamente.")
