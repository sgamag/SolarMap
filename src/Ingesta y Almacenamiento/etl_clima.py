# Script ETL de carga de la capa Silver a la tabla de hechos: fact_clima_agregado_mensual
# Sin dependencias externas (solo librerias nativas y mysql-connector)

import csv
import mysql.connector

# Ruta del archivo del clima en la capa silver de nuestro datalake
RUTA_CSV_CLIMA_SILVER = "/datalake/datos/silver/Clima"

def transformar_y_cargar_clima():
    print("1. Extrayendo datos Silver y calculando agregaciones...")
    
    # Diccionario para calcular la media TOTAL del potencial de cada zona (los 36 valores fijos)
    # Formato: id_zona -> {'suma_potencial': 0.0, 'contador': 0}
    potencial_global_zona = {}
    
    # Diccionario para calcular las variables climaticas POR MES del conjunto de años
    # Formato: (id_zona, mes) -> {'suma_rad': 0.0, 'suma_nub': 0.0, 'suma_temp': 0.0, 'max_temp': -999, 'min_temp': 999, 'contador': 0}
    clima_mensual_zona = {}
    
    with open(RUTA_CSV_CLIMA_SILVER, mode='r', encoding='utf-8') as archivo:
        lector = csv.DictReader(archivo)
        
        for fila in lector:
            id_zona = fila['tile_id']
            # Extraemos el mes de la columna valid_time (ej: "2001-02-01 12:00:00" -> 02)
            mes = int(fila['valid_time'][5:7])
            
            # Casteamos los datos a decimales
            radiacion = float(fila['ssrd_kWhm2'])
            nubosidad = float(fila['tcc'])
            temperatura = float(fila['t2m_C'])
            potencial = float(fila['potencial_0_1'])
            
            # --- PARTE 1: Acumulamos el potencial global (ignora el mes, es la media total del tile) ---
            if id_zona not in potencial_global_zona:
                potencial_global_zona[id_zona] = {'suma_potencial': 0.0, 'contador': 0}
                
            potencial_global_zona[id_zona]['suma_potencial'] += potencial
            potencial_global_zona[id_zona]['contador'] += 1
            
            # --- PARTE 2: Acumulamos el resto de variables agrupadas por zona y mes ---
            clave_mensual = (id_zona, mes)
            
            if clave_mensual not in clima_mensual_zona:
                clima_mensual_zona[clave_mensual] = {
                    'suma_rad': 0.0,
                    'suma_nub': 0.0,
                    'suma_temp': 0.0,
                    'max_temp': temperatura,
                    'min_temp': temperatura,
                    'contador': 0
                }
                
            grupo = clima_mensual_zona[clave_mensual]
            grupo['suma_rad'] += radiacion
            grupo['suma_nub'] += nubosidad
            grupo['suma_temp'] += temperatura
            grupo['contador'] += 1
            
            # Evaluamos si la temperatura actual rompe el record maximo o minimo del mes
            if temperatura > grupo['max_temp']:
                grupo['max_temp'] = temperatura
            if temperatura < grupo['min_temp']:
                grupo['min_temp'] = temperatura

    # Procesamos las medias finales y preparamos la lista para insertar en base de datos
    datos_a_insertar = []
    
    for (id_zona, mes), valores_mensuales in clima_mensual_zona.items():
        cantidad_mensual = valores_mensuales['contador']
        
        # Calculamos las medias mensuales (radiacion, nubosidad, temperatura)
        media_rad = valores_mensuales['suma_rad'] / cantidad_mensual
        media_nub = valores_mensuales['suma_nub'] / cantidad_mensual
        media_temp = valores_mensuales['suma_temp'] / cantidad_mensual
        
        # Obtenemos la media global del potencial para esta zona en concreto
        datos_potencial_zona = potencial_global_zona[id_zona]
        media_potencial_global = datos_potencial_zona['suma_potencial'] / datos_potencial_zona['contador']
        
        datos_a_insertar.append((
            id_zona, 
            mes, 
            media_rad, 
            media_nub, 
            media_temp, 
            valores_mensuales['max_temp'], 
            valores_mensuales['min_temp'], 
            media_potencial_global  # <-- Aqui se inyecta el valor constante para este tile
        ))
        
    print(f"-> ¡Calculos listos! {len(datos_a_insertar)} filas agregadas preparadas.")
    
    print("\n2. Conectando al servidor Lorca y cargando tabla fact_clima_agregado_mensual...")
    conn = mysql.connector.connect(
        host="10.151.30.2", user="bd_rvm_solar_map",
        password="Mar123Qz", database="bd_rvm_solar_map"
    )
    cursor = conn.cursor()
    
    try:
        # Vaciamos la tabla de hechos antes de recargar el historico completo
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE fact_clima_agregado_mensual;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        
        sql = """
            INSERT INTO fact_clima_agregado_mensual 
            (id_zona, mes, radiacion_media_mes, nubosidad_media_mes, 
            temperatura_media_mes, temperatura_maxima_mes, temperatura_minima_mes, potencial_medio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(sql, datos_a_insertar)
        conn.commit()
        print(f"-> ¡Exito! {cursor.rowcount} registros insertados correctamente.")
        
    except Exception as e:
        print(f"-> Error durante la insercion en base de datos: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    transformar_y_cargar_clima()