# Script para la generacion de tabla de hechos Tejados Detectados

import csv
import random
from pathlib import Path

random.seed(24)
CARPETA_DIM    = Path("data_ingesta/sinteticos/dimensiones")
CARPETA_SALIDA = Path("data_ingesta/sinteticos/hechos")
CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

def leer_csv(carpeta, nombre):
    with open(carpeta / f"{nombre}.csv", "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def guardar_csv(nombre_tabla, filas, columnas):
    with open(CARPETA_SALIDA / f"{nombre_tabla}.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"Generado: {nombre_tabla}.csv ({len(filas)} filas)")

print("Iniciando generacion de datos de tejados...")

zonas = leer_csv(CARPETA_DIM, "dim_zona")
caracteristicas = leer_csv(CARPETA_DIM, "dim_caracteristicas_tejado")

# ====================================================================
# GENERACION DE TEJADOS
# ====================================================================
filas_tejados = []
id_tejado = 1

# 1. INYECTOR: Aseguramos que existan las 18 combinaciones de tejado al menos una vez
for c in caracteristicas:
    z = random.choice(zonas)
    ori = c["orientacion_principal"]
    tamano = c["tamaño_categoria"]
    horas_sol = int(c["horas_sol"])

    # Forzamos el area util (40% de la bruta) segun la categoria
    if tamano == "Pequeño":
        area_bruta = round(random.uniform(40, 74.9), 2)
    elif tamano == "Mediano":
        area_bruta = round(random.uniform(75, 174.9), 2)
    else: # Grande
        area_bruta = round(random.uniform(175, 300), 2)
        
    area_util = round(area_bruta * 0.40, 2)
    
    # Calculo del potencial fijando el potencial medio en 0.25
    pot_medio = 0.25
    factor_ori = horas_sol / 1750.0 # Normalizado sobre el maximo (Sur)
    factor_tam = {"Pequeño": 0.85, "Mediano": 1.0, "Grande": 1.15}[tamano]
    
    # Formula: potencial_medio * 10 * orientacion * tamaño
    nota = (pot_medio * 10) * factor_ori * factor_tam
    
    filas_tejados.append({
        "id_tejado": id_tejado, 
        "id_zona": z["id_zona"], 
        "id_caracteristica": c["id_caracteristica"], 
        "latitud": round(random.uniform(float(z["sur_lat_min"]), float(z["norte_lat_max"])), 6), 
        "longitud": round(random.uniform(float(z["oeste_lon_min"]), float(z["este_lon_max"])), 6), 
        "area_total_bruta_m2": area_bruta, 
        "area_util_m2": area_util, 
        "orientacion_grados": round({"Norte": 0, "Este": 90, "Sureste": 135, "Sur": 180, "Suroeste": 225, "Oeste": 270}[ori] + random.uniform(-8, 8), 1), 
        "orientacion_principal": ori, 
        "potencial_final": round(max(0.0, min(10.0, nota)), 2)
    })
    id_tejado += 1

# 2. GENERACION MASIVA: Repartimos por todas las zonas
ciudades_grandes = ["Mostoles", "Fuenlabrada", "Getafe", "Alcobendas", "Las Rozas de Madrid", "Pozuelo de Alarcon"]

for z in zonas:
    # Densidad logica de tejados
    if z["municipio"] == "Madrid":
        num_tejados = random.randint(20, 35)
    elif z["municipio"] in ciudades_grandes:
        num_tejados = random.randint(10, 20)
    else:
        num_tejados = random.randint(3, 8) # Aseguramos minimo 3 en todos lados
        
    for _ in range(num_tejados):
        # Grupos de area bruta (ni muy pequenas ni gigantes, tope 300)
        prob = random.random()
        if prob < 0.60:
            area_bruta = round(random.uniform(60, 120), 2)
        elif prob < 0.90:
            area_bruta = round(random.uniform(120, 200), 2)
        else:
            area_bruta = round(random.uniform(200, 300), 2)
            
        area_util = round(area_bruta * 0.40, 2)
        
        # Orientacion por pesos
        ori = random.choices(["Sur", "Sureste", "Suroeste", "Este", "Oeste", "Norte"], weights=[0.35, 0.22, 0.18, 0.12, 0.08, 0.05])[0]
        
        # Categorizamos el tamaño en base a la superficie util real
        tamano = "Pequeño" if area_util < 30 else ("Grande" if area_util > 70 else "Mediano")
        
        caract_seleccionada = next(c for c in caracteristicas if c["tamaño_categoria"] == tamano and c["orientacion_principal"] == ori)
        horas_sol = int(caract_seleccionada["horas_sol"])
        
        # Calculo del potencial fijando el potencial medio en 0.25
        pot_medio = 0.25
        factor_ori = horas_sol / 1750.0
        factor_tam = {"Pequeño": 0.85, "Mediano": 1.0, "Grande": 1.15}[tamano]
        
        # Formula: potencial_medio * 10 * orientacion * tamaño
        nota = (pot_medio * 10) * factor_ori * factor_tam
        
        filas_tejados.append({
            "id_tejado": id_tejado, 
            "id_zona": z["id_zona"], 
            "id_caracteristica": caract_seleccionada["id_caracteristica"], 
            "latitud": round(random.uniform(float(z["sur_lat_min"]), float(z["norte_lat_max"])), 6), 
            "longitud": round(random.uniform(float(z["oeste_lon_min"]), float(z["este_lon_max"])), 6), 
            "area_total_bruta_m2": area_bruta, 
            "area_util_m2": area_util, 
            "orientacion_grados": round({"Norte": 0, "Este": 90, "Sureste": 135, "Sur": 180, "Suroeste": 225, "Oeste": 270}[ori] + random.uniform(-8, 8), 1), 
            "orientacion_principal": ori, 
            "potencial_final": round(max(0.0, min(10.0, nota)), 2) # Limitado a 10 para que no pete
        })
        id_tejado += 1

if filas_tejados:
    guardar_csv("fact_tejados_detectados", filas_tejados, list(filas_tejados[0].keys()))

print("Se ha creado la tabla fact_tejados_detectados con exito.")