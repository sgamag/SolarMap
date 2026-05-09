# Script para la generacion de la navegacion web y calculos financieros

import csv
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(24)
CARPETA_DIM    = Path("data_ingesta/sinteticos/dimensiones")
CARPETA_HECHOS = Path("data_ingesta/sinteticos/hechos")
RUTA_PRECIOS   = Path("prediccion_30_anios.csv")

def leer_csv(carpeta, nombre_tabla):
    with open(carpeta / f"{nombre_tabla}.csv", "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def guardar_csv(nombre_tabla, filas, columnas):
    with open(CARPETA_HECHOS / f"{nombre_tabla}.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"Generado: {nombre_tabla}.csv ({len(filas)} filas)")

print("Iniciando simulacion de trafico web y calculo de ROI...")

usuarios   = leer_csv(CARPETA_DIM, "dim_usuario")
zonas      = leer_csv(CARPETA_DIM, "dim_zona")
tejados    = leer_csv(CARPETA_HECHOS, "fact_tejados_detectados")
paneles    = leer_csv(CARPETA_DIM, "dim_panel")
escenarios = leer_csv(CARPETA_DIM, "dim_escenario_economico")
ZONAS_MADRID = [z["id_zona"] for z in zonas if z["municipio"] == "Madrid"]
ZONAS_PERIFERIA = [z["id_zona"] for z in zonas if z["municipio"] != "Madrid"]

# Carga del modelo predictivo externo
precios_luz = {}
if RUTA_PRECIOS.exists():
    with open(RUTA_PRECIOS, "r", encoding="utf-8") as f:
        for fila in csv.DictReader(f, delimiter=";"):
            try:
                clave = (int(fila["anio"]), fila["escenario"].strip())
                precios_luz.setdefault(clave, []).append(float(fila["precio_luz"]))
            except: pass
    precios_luz = {k: round(sum(v)/len(v), 5) for k, v in precios_luz.items()}

def obtener_precio(año, esc): return precios_luz.get((año, esc), 0.15)

# Matriz de Embudo de Conversion de la web
EMBUDO = [
    ("EVT_ACCESO_WEB", 1.00, 2, 8),
    ("EVT_LOGIN", 0.70, 20, 40), 
    ("EVT_ABRIR_MAPA", 0.95, 5, 15),
    ("EVT_BUSCAR_DIR", 0.90, 45, 90),
    ("EVT_CAPTURAR_ZONA", 0.95, 10, 25),
    ("EVT_SELEC_TEJADO", 0.90, 45, 90),
    ("EVT_VER_POTENCIAL", 1.00, 15, 30),
    ("EVT_ABRIR_SIM", 0.90, 5, 15),
    ("EVT_CALCULAR_ROI", 0.95, 60, 150),
    ("EVT_DESCARGAR_INF", 0.60, 10, 20),
    ("EVT_CONTACTO_PROV", 0.25, 60, 120)
]

filas_eventos, filas_roi = [], []
id_evento, id_simulacion = 1, 1

# Pesos horarios de transito 
PESOS_HORAS = [0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 2.0, 1.5, 1.5, 2.0, 2.5, 3.0, 3.0, 4.0, 5.0, 8.0, 9.0, 8.0, 5.0, 2.0]

for u in usuarios:
    es_anonimo = u["grupo_usuario"] == ""
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
        hora = random.choices(range(24), weights=PESOS_HORAS)[0]
        momento = datetime(fecha_sesion.year, fecha_sesion.month, fecha_sesion.day, hora, random.randint(0, 59))
        zona_actual = random.choice(ZONAS_MADRID if random.random() < 0.7 else ZONAS_PERIFERIA)
        orden = 1
        
        for id_ev, prob_base, t_min, t_max in EMBUDO:

            if es_anonimo and id_ev == "EVT_LOGIN":
                break
                
            prob = prob_base
            if not es_anonimo:
                if u["grupo_usuario"] == "Senior" and id_ev == "EVT_LOGIN": prob *= 0.40
                elif u["grupo_usuario"] == "Joven" and id_ev in ["EVT_DESCARGAR_INF", "EVT_CONTACTO_PROV"]: prob *= 0.15
                elif u["grupo_usuario"] == "Adulto": prob = min(prob * 1.15, 1.0)
            
            if random.random() > prob:
                break
                
            duracion = random.randint(t_min, t_max)
            filas_eventos.append({"id_evento": id_evento, "id_usuario": u["id_usuario"], "id_sesion": id_sesion, "id_tipo_evento": id_ev, "id_zona": zona_actual if id_ev not in ["EVT_ACCESO_WEB", "EVT_LOGIN", "EVT_REGISTRO"] else "", "id_fecha": int(fecha_sesion.strftime("%Y%m%d")), "id_hora": momento.hour, "timestamp_evento": momento.strftime("%Y-%m-%d %H:%M:%S"), "duracion_evento_segundos": duracion, "orden_en_sesion": orden})
            id_evento += 1
            orden += 1
            momento += timedelta(seconds=duracion)
            
            # Procedimiento de calculo financiero asociado al evento
            if id_ev == "EVT_CALCULAR_ROI" and tejados:
                tjd, pnl, esc = random.choice(tejados), random.choice(paneles), random.choice(escenarios)
                max_paneles = max(1, int(float(tjd["area_util_m2"]) / float(pnl["area_panel_m2"])))
                num_paneles = min(max_paneles, random.randint(8, 10))
                inversion = round((num_paneles * float(pnl["precio_unitario_euros"])) + float(pnl["coste_instalacion_fijo_euros"]), 2)
                
                horas_sol = {"Sur": 1750, "Sureste": 1620, "Suroeste": 1580, "Este": 1380, "Oeste": 1350, "Norte": 1050}.get(tjd["orientacion_principal"], 1400)
                ahorro_acumulado, energia_primer_año = 0.0, 0.0
                
                for i in range(30):
                    energia = num_paneles * (int(pnl["potencia_w"]) / 1000) * horas_sol * (0.80 * ((1 - 0.005) ** i))
                    if i == 0: energia_primer_año = energia
                    ahorro_acumulado += energia * obtener_precio(fecha_sesion.year + i, esc["nombre_escenario"])
                
                ahorro_año1 = round(energia_primer_año * obtener_precio(fecha_sesion.year, esc["nombre_escenario"]), 2)
                roi = round(((ahorro_acumulado - inversion) / inversion) * 3.33, 2) if inversion > 0 else 0.0
                
                filas_roi.append({"id_simulacion": id_simulacion, "id_tejado": tjd["id_tejado"], "id_panel": pnl["id_panel"], "id_escenario": esc["id_escenario"], "id_usuario": u["id_usuario"], "id_sesion": id_sesion, "numero_paneles_instalados": num_paneles, "energia_generada_anual_kwh": round(energia_primer_año, 2), "inversion_inicial_euros": inversion, "ahorro_primer_año_euros": ahorro_año1, "tiempo_amortizacion_años": round(inversion / ahorro_año1, 2) if ahorro_año1 > 0 else 0.0, "roi_porcentaje": roi, "timestamp_simulacion": momento.strftime("%Y-%m-%d %H:%M:%S")})
                id_simulacion += 1

guardar_csv("fact_eventos_web", filas_eventos, list(filas_eventos[0].keys()))
guardar_csv("fact_simulacion_roi", filas_roi, list(filas_roi[0].keys()))

print("Se ha creado con exito.")