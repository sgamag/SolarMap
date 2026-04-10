# ==============================================================================
# SCRIPT 3: INGESTA MASIVA DE DATOS CLIMÁTICOS (SIN PANDAS)
# ==============================================================================

import pymysql
import csv
from datetime import datetime

def ingestar_clima(cursor, ruta_csv):
    print(f"Abriendo el archivo {ruta_csv} en modo lectura secuencial...")
    
    try:
        # Usamos encoding='utf-8' por si hay algún carácter raro en el archivo
        with open(ruta_csv, mode='r', encoding='utf-8') as archivo:
            
            # DictReader lee la primera línea como cabeceras y convierte cada fila en un diccionario
            # Cambia delimiter=';' si tu Excel al guardarlo como CSV usa punto y coma
            lector_csv = csv.DictReader(archivo, delimiter=',')
            
            datos_a_insertar = []
            tamano_lote = 10000
            filas_totales_insertadas = 0
            
            # Sentencia SQL
            sql = """
                INSERT IGNORE INTO fact_clima_diario (
                    id_fecha, id_zona, id_hora, temperatura_max_c, radiacion_solar, cobertura_nubes, velocidad_viento
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            print(f"Iniciando volcado en Lorca en lotes de {tamano_lote}...")

            for fila in lector_csv:
                # =================================================================
                # ⚠️ ZONA DE MAPEO: ADAPTA LOS NOMBRES A LAS CABECERAS DE TU CSV
                # =================================================================
                
                # 1. Función de limpieza: Convierte celdas vacías en NULL para la base de datos
                def limpiar_dato(valor, tipo):
                    if not valor or valor.strip() == "":
                        return None
                    return tipo(valor)

                # 2. Fechas e IDs
                fecha_str = fila['Fecha_CSV'] # Cambiar 'Fecha_CSV' por tu nombre real
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                id_fecha = int(fecha_obj.strftime('%Y%m%d'))
                
                # 3. Casteo manual (como no hay Pandas, tenemos que decirle qué es número y qué es texto)
                id_zona = limpiar_dato(fila['Zona_ID'], str) 
                id_hora = limpiar_dato(fila['Hora_CSV'], int)
                
                # 4. Métricas climáticas (Ojo: en Python los decimales van con punto, no con coma)
                temp_max = limpiar_dato(fila['Temp_Max'], float)
                radiacion = limpiar_dato(fila['Radiacion_Solar'], float)
                nubes = limpiar_dato(fila['Porcentaje_Nubes'], float)
                viento = limpiar_dato(fila['Velocidad_Viento'], float)
                
                # =================================================================

                # Añadimos la fila limpia a nuestro lote
                datos_a_insertar.append((
                    id_fecha, id_zona, id_hora, temp_max, radiacion, nubes, viento
                ))

                # Si nuestro lote llega a 10.000, lo enviamos a Lorca y vaciamos la mochila
                if len(datos_a_insertar) >= tamano_lote:
                    cursor.executemany(sql, datos_a_insertar)
                    filas_totales_insertadas += len(datos_a_insertar)
                    print(f"Progreso: {filas_totales_insertadas} filas insertadas...")
                    datos_a_insertar.clear() # Vaciamos la lista para no saturar la RAM

            # Cuando termina el bucle, es posible que queden filas en la mochila (ej. las últimas 3.400)
            if len(datos_a_insertar) > 0:
                cursor.executemany(sql, datos_a_insertar)
                filas_totales_insertadas += len(datos_a_insertar)
                
            print(f"¡Éxito! Ingesta completada. Se han guardado {filas_totales_insertadas} registros.")

    except FileNotFoundError:
        print(f"❌ Error: No se ha encontrado el archivo en la ruta: {ruta_csv}")
    except KeyError as e:
        print(f"❌ Error: No se encuentra la columna {e} en tu archivo CSV. Revisa las mayúsculas/minúsculas en la ZONA DE MAPEO.")
    except Exception as e:
        print(f"❌ Error crítico en la fila {filas_totales_insertadas}: {e}")

def main():
    db_host = "10.151.30.2"
    db_port = 3306
    db_user = "bd_rvm_solar_map"
    db_pass = "Mar123Qz" 
    db_name = "bd_rvm_solar_map"

    # Asegúrate de poner el nombre exacto de tu archivo y que esté en la misma carpeta
    ARCHIVO_CSV = "datos_clima.csv" 

    print("Conectando a Lorca para ingesta masiva...")

    try:
        conexion = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name
        )

        if conexion.open:
            cursor = conexion.cursor()
            
            ingestar_clima(cursor, ARCHIVO_CSV)
            
            # ¡Importantísimo! Si no hacemos commit, la base de datos olvida todo
            conexion.commit()
            print("=========================================================")
            print("Los datos han sido confirmados y guardados en el disco duro.")
            print("=========================================================")

    except Exception as e:
        print(f"Error de conexión a la base de datos: {e}")

    finally:
        if 'conexion' in locals() and conexion.open:
            cursor.close()
            conexion.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    main()