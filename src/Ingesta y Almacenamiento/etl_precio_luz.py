import csv
import mysql.connector

# cambia esto por la ruta real de tu capa silver
RUTA_CSV_SILVER = "C:/ruta/a/tu/datalake/silver/precios_luz_proyeccion.csv"

def cargar_precios():
    datos = []
    with open(RUTA_CSV_SILVER, mode='r', encoding='utf-8') as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            anyo = int(fila['anyo'])
            precio_neutro = float(fila['precio_neutro'])
            precio_optimista = float(fila['precio_optimista'])
            precio_pesimista = float(fila['precio_pesimista'])
            datos.append((anyo, precio_neutro, precio_optimista, precio_pesimista))
    return datos

def main():
    print("cargando precios de luz en lorca...")
    datos_a_insertar = cargar_precios()
    
    conn = mysql.connector.connect(
        host="10.151.30.2", user="bd_rvm_solar_map",
        password="Mar123Qz", database="bd_rvm_solar_map"
    )
    cursor = conn.cursor()
    
    try:
        cursor.execute("TRUNCATE TABLE dim_precio_luz;")
        sql = """
            INSERT INTO dim_precio_luz 
            (anyo, precio_estimado_neutro, precio_estimado_optimista, precio_estimado_pesimista)
            VALUES (%s, %s, %s, %s)
        """
        cursor.executemany(sql, datos_a_insertar)
        conn.commit()
        print(f"listo, {cursor.rowcount} años de proyecciones cargados.")
    except Exception as e:
        print(f"error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()