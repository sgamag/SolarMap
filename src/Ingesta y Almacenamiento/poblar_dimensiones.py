# ==============================================================================
# SCRIPT 2: POBLADO DE TABLAS DE DIMENSIÓN (DATOS MAESTROS)
# ==============================================================================
# Objetivo: Llenar los "catálogos" (fechas, horas, zonas) para que la base de
# datos tenga el contexto necesario antes de recibir el volumen masivo del clima.
# ==============================================================================

import pymysql
import datetime
import pytz
import holidays

# Importamos tu script de geometría. 
# Asegúrate de que el archivo generacion_tiles.py esté en la misma carpeta.
try:
    import generacion_tiles
except ImportError:
    print("Aviso: No se encontró el archivo generacion_tiles.py en esta carpeta.")

def poblar_dim_fecha(cursor):
    print("Generando calendario desde el anio 2000 hasta el 2030...")
    
    fecha_inicio = datetime.date(2000, 1, 1)
    fecha_fin = datetime.date(2030, 12, 31)
    
    zona_horaria = pytz.timezone('Europe/Madrid')
    
    # Cargamos el calendario oficial de festivos para la Comunidad de Madrid
    festivos_madrid = holidays.ES(prov='MD', years=range(2000, 2031))
    
    nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    nombres_dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    
    datos_fechas = []
    fecha_actual = fecha_inicio
    
    while fecha_actual <= fecha_fin:
        # Generar un ID numérico como 20260407 (AnioMesDia)
        id_fecha = int(fecha_actual.strftime("%Y%m%d"))
        anio = fecha_actual.year
        mes = fecha_actual.month
        dia = fecha_actual.day
        
        # Cálculos de calendario
        trimestre = (mes - 1) // 3 + 1
        dia_semana = fecha_actual.weekday() + 1 # 1=Lunes, 7=Domingo
        es_fin_semana = True if dia_semana >= 6 else False
        
        # Evaluamos automáticamente si la fecha actual está en la lista de festivos de Madrid
        es_festivo = True if fecha_actual in festivos_madrid else False
        
        # Calcular estación aproximada
        if (mes == 3 and dia >= 21) or mes in [4, 5] or (mes == 6 and dia < 21):
            estacion = "Primavera"
        elif (mes == 6 and dia >= 21) or mes in [7, 8] or (mes == 9 and dia < 23):
            estacion = "Verano"
        elif (mes == 9 and dia >= 23) or mes in [10, 11] or (mes == 12 and dia < 21):
            estacion = "Otono"
        else:
            estacion = "Invierno"
            
        # Comprobar horario de verano usando pytz
        fecha_dt = datetime.datetime(anio, mes, dia)
        fecha_local = zona_horaria.localize(fecha_dt)
        es_horario_verano = bool(fecha_local.dst())

        # Añadimos la fila a la lista de datos a insertar
        datos_fechas.append((
            id_fecha, fecha_actual, anio, trimestre, mes, nombres_meses[mes-1],
            dia, dia_semana, nombres_dias[dia_semana-1], estacion, 
            es_fin_semana, es_festivo, es_horario_verano
        ))
        
        # Avanzamos un día
        fecha_actual += datetime.timedelta(days=1)

    # Sentencia SQL
    sql = """
        INSERT IGNORE INTO dim_fecha (
            id_fecha, fecha_completa, anio, trimestre, mes, nombre_mes, 
            dia, dia_semana, nombre_dia, estacion, es_fin_de_semana, es_festivo, es_horario_verano
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    # INGESTA POR LOTES (Batching): Insertamos de 1000 en 1000 para no saturar la memoria del servidor Lorca
    tamano_lote = 1000
    total_insertados = 0
    
    print("Insertando fechas en Lorca por lotes para no saturar la memoria...")
    for i in range(0, len(datos_fechas), tamano_lote):
        lote = datos_fechas[i:i + tamano_lote]
        cursor.executemany(sql, lote)
        total_insertados += len(lote)
        
    print(f"Completado: {total_insertados} dias insertados en dim_fecha.")

def poblar_dim_hora(cursor):
    print("Generando las 24 horas del reloj...")
    
    datos_horas = []
    
    for h in range(24):
        id_hora = h
        hora_del_dia = h
        minuto_del_dia = 0 # Asumimos horas en punto
        
        # Formato 24h (ej. "14:00")
        hora_24h = f"{h:02d}:00"
        
        # Formato 12h (ej. "02:00 PM")
        am_pm = "AM" if h < 12 else "PM"
        h_12 = h if h <= 12 else h - 12
        h_12 = 12 if h_12 == 0 else h_12
        hora_12h = f"{h_12:02d}:00 {am_pm}"
        
        # Clasificar tramo horario
        if 6 <= h < 12:
            tramo = "Manana"
        elif 12 <= h < 20:
            tramo = "Tarde"
        elif 20 <= h <= 23:
            tramo = "Noche"
        else:
            tramo = "Madrugada"
            
        datos_horas.append((
            id_hora, hora_del_dia, minuto_del_dia, hora_24h, hora_12h, tramo
        ))

    sql = """
        INSERT IGNORE INTO dim_hora (
            id_hora, hora_del_dia, minuto_del_dia, hora_formato_24h, hora_formato_12h, tramo_horario
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.executemany(sql, datos_horas)
    print("Completado: 24 horas insertadas en dim_hora.")

def poblar_dim_zona(cursor):
    print("Importando zonas desde generacion_tiles.py...")
    
    try:
        # Llamamos a tu función de generacion_tiles.
        # IMPORTANTE: Revisa que tu función se llame 'obtener_datos_tiles' dentro de tu archivo.
        lista_tiles = generacion_tiles.obtener_datos_tiles()
        
        datos_zonas = []
        
        for tile in lista_tiles:
            datos_zonas.append((
                tile['id_zona'],
                tile['municipio'],
                tile.get('provincia', 'Madrid'),
                tile.get('altitud', 0.0),
                tile['lat_center'],
                tile['lon_center'],
                tile['norte_lat_max'],
                tile['sur_lat_min'],
                tile['este_lon_max'],
                tile['oeste_lon_min']
            ))

        sql = """
            INSERT IGNORE INTO dim_zona (
                id_zona, municipio, provincia, altitud, lat_center, lon_center,
                norte_lat_max, sur_lat_min, este_lon_max, oeste_lon_min
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(sql, datos_zonas)
        print(f"Completado: {len(datos_zonas)} zonas insertadas en dim_zona.")
        
    except NameError:
        print("Error: No se pudo ejecutar porque no existe el modulo generacion_tiles. Salta este paso.")
    except AttributeError:
        print("Error: Tu archivo generacion_tiles.py existe, pero no tiene una función llamada 'obtener_datos_tiles()'.")
    except Exception as e:
        print(f"Error al procesar las zonas: {e}")

def main():
    # Parámetros de conexión a Lorca
    db_host = "10.151.30.2"
    db_port = 3306
    db_user = "bd_rvm_solar_map"
    db_pass = "Mar123Qz" 
    db_name = "bd_rvm_solar_map"

    print("Iniciando conexión a Lorca para poblar dimensiones...")

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
            
            # Ejecutamos las tres funciones de inserción
            poblar_dim_fecha(cursor)
            poblar_dim_hora(cursor)
            poblar_dim_zona(cursor)
            
            # Guardamos todos los cambios en la base de datos
            conexion.commit()
            print("=========================================================")
            print("¡ÉXITO TOTAL! Todas las dimensiones han sido pobladas.")
            print("=========================================================")

    except Exception as e:
        print(f"❌ Error crítico de base de datos: {e}")

    finally:
        if 'conexion' in locals() and conexion.open:
            cursor.close()
            conexion.close()
            print("Conexión cerrada de forma segura.")

if __name__ == "__main__":
    main()