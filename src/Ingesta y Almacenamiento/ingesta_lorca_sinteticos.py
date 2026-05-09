# Script de ingesta de datos sinteticos a la base de datos en Lorca

import os
import csv
import mysql.connector
from pathlib import Path

# Configuracion de la conexion al servidor Lorca
DB_HOST = "10.151.30.2"
DB_PORT = 3306
DB_USER = "bd_rvm_solar_map"
DB_PASS = os.getenv("DB_PASS", "Mar123Qz")
DB_NAME = "bd_rvm_solar_map"

# Rutas de origen de los datos
CARPETA_DIM = Path("data_ingesta/sinteticos/dimensiones")
CARPETA_HECHOS = Path("data_ingesta/sinteticos/hechos")

# Lista de tablas a subir 
TABLAS_A_SUBIR = [
    (CARPETA_DIM, "dim_zona"),
    (CARPETA_DIM, "dim_fecha"),
    (CARPETA_DIM, "dim_hora"),
    (CARPETA_DIM, "dim_usuario"),
    (CARPETA_DIM, "app_credenciales_usuario"),
    (CARPETA_DIM, "dim_tipo_evento"),
    (CARPETA_DIM, "dim_caracteristicas_tejado"),
    (CARPETA_DIM, "dim_escenario_economico"),
    (CARPETA_DIM, "dim_panel"),
    (CARPETA_HECHOS, "fact_tejados_detectados"),
    (CARPETA_HECHOS, "fact_eventos_web"),
    (CARPETA_HECHOS, "fact_simulacion_roi")
]

def procesar_valor(valor):
    # Se convierten cadenas vacias del CSV en NULL para la base de datos.
    if valor == "" or valor is None:
        return None
    return valor

def cargar_tabla(cursor, ruta_carpeta, nombre_tabla):
    ruta_csv = ruta_carpeta / f"{nombre_tabla}.csv"
    
    if not ruta_csv.exists():
        print(f" No se encontro el archivo {nombre_tabla}.csv. Saltando...")
        return

    with open(ruta_csv, "r", encoding="utf-8") as f:
        lector = csv.reader(f)
        columnas = next(lector)
        
        # Construccion dinamica de la consulta INSERT
        placeholders = ", ".join(["%s"] * len(columnas))
        query = f"INSERT INTO {nombre_tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
        
        filas_procesadas = []
        for fila in lector:
            filas_procesadas.append(tuple(procesar_valor(x) for x in fila))
        
        if filas_procesadas:
            cursor.executemany(query, filas_procesadas)
            print(f"  OK -> {nombre_tabla} ({len(filas_procesadas)} filas cargadas)")

def main():
    try:
        conexion = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            ssl_disabled=True
        )

        if conexion.is_connected():
            print("Conectado a Lorca con exito")
            cursor = conexion.cursor()

            # Desactivar temporalmente el chequeo de claves foraneas 
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            # Limpiar datos previos de las tablas que vamos a cargar
            print("Limpiando registros previos en tablas seleccionadas...")
            for _, tabla in reversed(TABLAS_A_SUBIR):
                cursor.execute(f"TRUNCATE TABLE {tabla};")

            print("Iniciando carga de archivos CSV...")
            for carpeta, tabla in TABLAS_A_SUBIR:
                cargar_tabla(cursor, carpeta, tabla)

            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            conexion.commit()
            print("Ingesta completada correctamente")

    except mysql.connector.Error as error:
        print(f"Error durante la ingesta en Lorca: {error}")

    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()
            print("Conexion cerrada.")

if __name__ == "__main__":
    main()