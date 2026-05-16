# Script para la generacion de la navegacion web y simulaciones ROI

import csv
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(24)
CARPETA_DIM    = Path("data_ingesta/sinteticos/dimensiones")
CARPETA_HECHOS = Path("data_ingesta/sinteticos/hechos")

def leer_csv(carpeta, nombre_tabla):
    with open(carpeta / f"{nombre_tabla}.csv", "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def guardar_csv(nombre_tabla, filas, columnas):
    with open(CARPETA_HECHOS / f"{nombre_tabla}.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"Generado: {nombre_tabla}.csv ({len(filas)} filas)")

print("Iniciando simulacion de trafico web y registros de ROI...")

usuarios = leer_csv(CARPETA_DIM, "dim_usuario")
zonas    = leer_csv(CARPETA_DIM, "dim_zona")
tejados  = leer_csv(CARPETA_HECHOS, "fact_tejados_detectados")

ZONAS_MADRID = [z["id_zona"] for z in zonas if z["municipio"] == "Madrid"]
ZONAS_PERIFERIA = [z["id_zona"] for z in zonas if z["municipio"] != "Madrid"]

# Diccionario de tiempos base de cada evento (min_segundos, max_segundos)
TIEMPOS_BASE = {
    "EVT_ACCESO_WEB": (2, 5),
    "EVT_LOGIN": (10, 25),
    "EVT_ABRIR_MAPA": (3, 8),
    "EVT_BUSCAR_DIR": (15, 45),     # Escribir la calle lleva su tiempo
    "EVT_CAPTURAR_ZONA": (5, 12),
    "EVT_SELEC_TEJADO": (10, 30),   # Mirar el mapa y hacer clic en la casa
    "EVT_VER_POTENCIAL": (15, 40),  # Leer el popup de potencial
    "EVT_ABRIR_SIM": (3, 8),
    "EVT_CALCULAR_ROI": (45, 180),  # Aquí se tiran un buen rato leyendo datos y gráficas
    "EVT_DESCARGAR_INF": (5, 15),
    "EVT_CONTACTO_PROV": (30, 90)   # Rellenar formulario de contacto
}

filas_eventos, filas_roi = [], []
id_evento, id_simulacion = 1, 1

# Pesos de probabilidad de uso de la web según la hora del día (0-23h)
PESOS_HORAS = [1, 1, 1, 1, 1, 2, 5, 10, 15, 20, 20, 15, 15, 20, 25, 30, 30, 40, 50, 80, 90, 80, 50, 20]

for u in usuarios:
    es_anonimo = u["grupo_usuario"] == ""
    # Si es anónimo va más lento por defecto (no conoce la web). Ajuste por edad para el resto:
    multiplicador_tiempo = 1.2 if es_anonimo else (0.7 if u["grupo_usuario"] == "Joven" else (1.0 if u["grupo_usuario"] == "Adulto" else 1.5))
    
    primer_acceso = date.fromisoformat(u["fecha_primer_acceso"])
    max_sesiones = random.randint(1, 2) if es_anonimo else (random.randint(4, 8) if u["grupo_usuario"] == "Adulto" else random.randint(2, 5))
    
    for num_sesion in range(max_sesiones): 
        if num_sesion == 0:
            fecha_sesion = primer_acceso
        else:
            fecha_sesion = primer_acceso + timedelta(days=random.randint(5, 90))
            
        if fecha_sesion > date(2026, 4, 30): 
            continue
        
        id_sesion = f"SES_{uuid.uuid4().hex[:10].upper()}"
        hora_inicio = random.choices(range(24), weights=PESOS_HORAS)[0]
        momento_actual = datetime(fecha_sesion.year, fecha_sesion.month, fecha_sesion.day, hora_inicio, random.randint(0, 59))
        
        zona_actual = random.choice(ZONAS_MADRID if random.random() < 0.7 else ZONAS_PERIFERIA)
        orden = 1
        
        # --- GENERACIÓN DE LA NAVEGACIÓN (CON BUCLES LÓGICOS) ---
        flujo_sesion = ["EVT_ACCESO_WEB"]
        
        if not es_anonimo:
            flujo_sesion.append("EVT_LOGIN")
            
        # Pasa al mapa?
        if random.random() < 0.85:
            flujo_sesion.extend(["EVT_ABRIR_MAPA", "EVT_BUSCAR_DIR"])
            
            # Variación 1: Busca una dirección y luego busca otra distinta porque se equivocó
            if random.random() < 0.20:
                flujo_sesion.append("EVT_BUSCAR_DIR")
                
            # Captura la zona y pincha un tejado?
            if random.random() < 0.90:
                flujo_sesion.extend(["EVT_CAPTURAR_ZONA", "EVT_SELEC_TEJADO"])
                
                # Variación 2: Pinchó el tejado del vecino, vuelve a buscar o pincha otro
                if random.random() < 0.15:
                    if random.random() < 0.5:
                        flujo_sesion.extend(["EVT_BUSCAR_DIR", "EVT_CAPTURAR_ZONA", "EVT_SELEC_TEJADO"])
                    else:
                        flujo_sesion.append("EVT_SELEC_TEJADO")
                        
                flujo_sesion.append("EVT_VER_POTENCIAL")
                
                # Entra al simulador?
                prob_simular = 0.50 if es_anonimo else 0.85
                if random.random() < prob_simular:
                    flujo_sesion.extend(["EVT_ABRIR_SIM", "EVT_CALCULAR_ROI"])
                    
                    # Acciones finales post-simulación
                    if random.random() < 0.40:
                        flujo_sesion.append("EVT_DESCARGAR_INF")
                    if not es_anonimo and random.random() < 0.15:
                        flujo_sesion.append("EVT_CONTACTO_PROV")

        # --- PROCESADO DEL FLUJO (TIEMPOS Y REGISTRO) ---
        for id_ev in flujo_sesion:
            # Calculamos los segundos ajustados por el perfil del usuario
            t_min, t_max = TIEMPOS_BASE[id_ev]
            duracion = int(random.randint(t_min, t_max) * multiplicador_tiempo)
            
            # Los eventos de inicio no tienen zona asignada aun
            zona_evento = "" if id_ev in ["EVT_ACCESO_WEB", "EVT_LOGIN"] else zona_actual
            
            filas_eventos.append({
                "id_evento": id_evento, 
                "id_usuario": u["id_usuario"], 
                "id_sesion": id_sesion, 
                "id_tipo_evento": id_ev, 
                "id_zona": zona_evento, 
                "id_fecha": int(momento_actual.strftime("%Y%m%d")), 
                "id_hora": momento_actual.hour, 
                "timestamp_evento": momento_actual.strftime("%Y-%m-%d %H:%M:%S"), 
                "duracion_evento_segundos": duracion, 
                "orden_en_sesion": orden
            })
            
            # --- REGISTRO DE SIMULACIÓN ROI (ADAPTADO EXACTO A TU BASE DE DATOS) ---
            if id_ev == "EVT_CALCULAR_ROI" and tejados:
                # Buscamos un tejado aleatorio pero que esté en la zona que está mirando
                tejados_zona = [t for t in tejados if t["id_zona"] == zona_actual]
                tejado_simulado = random.choice(tejados_zona) if tejados_zona else random.choice(tejados)
                
                filas_roi.append({
                    "id_simulacion": id_simulacion, 
                    "id_tejado": tejado_simulado["id_tejado"], 
                    "id_usuario": u["id_usuario"], 
                    "id_sesion": id_sesion, 
                    "timestamp_simulacion": momento_actual.strftime("%Y-%m-%d %H:%M:%S")
                })
                id_simulacion += 1
            
            # Actualizamos contadores y sumamos los segundos al reloj para el siguiente evento
            id_evento += 1
            orden += 1
            momento_actual += timedelta(seconds=duracion)

if filas_eventos:
    guardar_csv("fact_eventos_web", filas_eventos, list(filas_eventos[0].keys()))
if filas_roi:
    guardar_csv("fact_simulacion_roi", filas_roi, list(filas_roi[0].keys()))

print("Se han creado ambas tablas con exito. Todo ajustado a la BD actual.")