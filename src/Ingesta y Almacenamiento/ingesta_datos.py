# ==============================================================================
# SCRIPT 3: INGESTA MASIVA DE CLIMA (BÚSQUEDA RECURSIVA Y TRADUCTOR UNIVERSAL)
# ==============================================================================

import os
import csv
import mysql.connector
from datetime import datetime

def ingestar_archivos_clima(cursor, conexion):
    # RUTA ABSOLUTA (La que comprobamos que funciona)
    carpeta_csv = r"C:\Users\Javier\Desktop\BigData\ProyectoBigData\src\Ingesta y Almacenamiento\data_Ingesta\csv_potencial" 
    
    if not os.path.exists(carpeta_csv):
        print(f"❌ Error: No se encuentra la carpeta en la ruta:\n{carpeta_csv}")
        return

    # 1. EL SABUESO (Búsqueda recursiva en todas las subcarpetas)
    archivos_csv_completos = []
    for raiz, directorios, archivos in os.walk(carpeta_csv):
        for archivo in archivos:
            if archivo.endswith('.csv'):
                # Guardamos la ruta entera hasta el archivo
                archivos_csv_completos.append(os.path.join(raiz, archivo))
                
    archivos_csv_completos.sort()
    
    if len(archivos_csv_completos) == 0:
        print(f"⚠️ La carpeta existe, pero el sabueso no encontró ningún .csv en sus subcarpetas.")
        return

    total_filas_global = 0

    sql_insert = """
        INSERT IGNORE INTO fact_clima_diario (
            id_fecha, id_zona, id_hora, 
            temperatura_max_c, radiacion_solar, cobertura_nubes, velocidad_viento, potencial_solar
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    print(f"🚀 Iniciando ingesta. Se han encontrado {len(archivos_csv_completos)} archivos CSV.")

    for ruta_completa in archivos_csv_completos:
        nombre_archivo = os.path.basename(ruta_completa)
        print(f"📂 Abriendo: {nombre_archivo}...")
        
        lote_datos = []
        filas_archivo_actual = 0
        
        with open(ruta_completa, mode='r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            
            for fila in lector:
                try:
                    # 2. EL TRADUCTOR UNIVERSAL DE FECHAS
                    fecha_texto = fila['valid_time']
                    fecha_obj = None
                    
                    # Lista de todos los formatos posibles en los CSV
                    formatos_posibles = [
                        '%d/%m/%Y %H:%M',     # Ej: 01/01/2000 12:00
                        '%Y-%m-%d %H:%M:%S',  # Ej: 2005-01-12 18:00:00
                        '%Y-%m-%d %H:%M',     # Ej: 2005-01-12 18:00
                        '%d/%m/%Y %H:%M:%S'   # Ej: 01/01/2000 12:00:00
                    ]
                    
                    for formato in formatos_posibles:
                        try:
                            fecha_obj = datetime.strptime(fecha_texto, formato)
                            break # Si acierta el formato, sale del bucle
                        except ValueError:
                            continue # Si falla, prueba el siguiente
                            
                    if fecha_obj is None:
                        print(f"⚠️ Fecha irreconocible: {fecha_texto} en {nombre_archivo}")
                        continue # Salta esta fila y sigue con la siguiente
                    
                    # Extraemos las llaves para Lorca
                    id_fecha = int(fecha_obj.strftime('%Y%m%d')) 
                    id_hora = fecha_obj.hour                     
                    
                    # EXTRACCIÓN DE MÉTRICAS
                    id_zona = fila['tile_id']
                    temperatura = float(fila['t2m_C'])
                    radiacion = float(fila['ssrd_kWhm2'])
                    nubes = float(fila['tcc'])
                    potencial = float(fila['potencial_0_1'])
                    velocidad_viento = None 
                    
                    lote_datos.append((
                        id_fecha, id_zona, id_hora,
                        temperatura, radiacion, nubes, velocidad_viento, potencial
                    ))
                    
                    filas_archivo_actual += 1
                    total_filas_global += 1
                    
                    # GUARDADO POR LOTES
                    if len(lote_datos) >= 5000:
                        cursor.executemany(sql_insert, lote_datos)
                        lote_datos = [] 
                        
                except Exception as e:
                    print(f"⚠️ Error leyendo una fila en {nombre_archivo}: {e}")
                    continue
            
            # Guardamos lo que haya sobrado al final del archivo
            if lote_datos:
                cursor.executemany(sql_insert, lote_datos)
        
        print(f"✅ Archivo completado: {filas_archivo_actual} registros.")
        
        # COMMIT AUTOMÁTICO
        conexion.commit() 
        
    print(f"\n🚀 ¡INGESTA TOTAL COMPLETADA! Se han procesado y guardado {total_filas_global} registros.")

def main():
    db_host = "10.151.30.2"
    db_port = 3306
    db_user = "bd_rvm_solar_map"
    db_pass = "Mar123Qz" 
    db_name = "bd_rvm_solar_map"

    try:
        conexion = mysql.connector.connect(
            host=db_host, port=db_port, user=db_user, 
            password=db_pass, database=db_name, ssl_disabled=True
        )
        if conexion.is_connected():
            cursor = conexion.cursor()
            ingestar_archivos_clima(cursor, conexion)
            
    except mysql.connector.Error as error:
        print(f"❌ Error crítico en Lorca: {error}")
    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()
            print("=========================================================")
            print("Conexión cerrada.")

if __name__ == "__main__":
    main()