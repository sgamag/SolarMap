# ============================================================
# VISUALIZACIÓN Y VALIDACIÓN DE LA BASE DE DATOS MYSQL
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

import pandas as pd
from sqlalchemy import create_engine, text
import os

# ============================================================
# CONFIGURACIÓN DE CONEXIÓN A MYSQL
# ============================================================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "era5_madrid")
DB_USER = os.getenv("DB_USER", "era5_user")
DB_PASS = os.getenv("DB_PASS", "SolarMap67")

SQLALCHEMY_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

print("Conectando a la base de datos MySQL...")

engine = create_engine(SQLALCHEMY_URL, future=True)

# ============================================================
# OBTENER TABLAS EXISTENTES
# ============================================================

tablas = pd.read_sql_query(
    "SHOW TABLES;",
    engine
)

# MySQL devuelve el nombre de la columna como el nombre de la BD
col_tablas = tablas.columns[0]
nombres_tablas = tablas[col_tablas].tolist()

print("\nTablas existentes en la base de datos:")
print(nombres_tablas)

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
        engine
    )
    n_rows = df_count.loc[0, "filas"]
    print(f"Número de filas: {n_rows}")

    # Cargar una muestra de la tabla
    df = pd.read_sql_query(
        f"SELECT * FROM {nombre_tabla} LIMIT {n_filas};",
        engine
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
            engine
        )
        print(df_full[columnas_numericas].describe())

        print("\nEstadísticos adicionales:")
        for col in columnas_numericas:
            print(f"\nColumna: {col}")
            print(f"  Media:        {df_full[col].mean():.4f}")
            print(f"  Mediana:      {df_full[col].median():.4f}")
            print(f"  Percentil 90: {df_full[col].quantile(0.90):.4f}")
            print(f"  Percentil 95: {df_full[col].quantile(0.95):.4f}")
    else:
        print("\nLa tabla no contiene columnas numéricas para análisis.")

# ============================================================
# INSPECCIÓN DE CADA TABLA RELEVANTE
# ============================================================

if "zonas" in nombres_tablas:
    inspeccionar_tabla("zonas")

if "era5_data" in nombres_tablas:
    inspeccionar_tabla("era5_data")

if "potencial_tile_resumen" in nombres_tablas:
    inspeccionar_tabla("potencial_tile_resumen")

print("\nInspección completada correctamente.")
