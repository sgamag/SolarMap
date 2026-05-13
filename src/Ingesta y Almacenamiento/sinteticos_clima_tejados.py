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

print("Iniciando generacion de datos...")

zonas = leer_csv(CARPETA_DIM, "dim_zona")
caracteristicas = leer_csv(CARPETA_DIM, "dim_caracteristicas_tejado")

# Hechos: Tejados Detectados
FACTOR_ORIENTACION = {"Sur": 1.00, "Sureste": 0.95, "Suroeste": 0.93, "Este": 0.80, "Oeste": 0.78, "Norte": 0.60}
filas_tejados = []
id_tejado = 1

for z in zonas:
    num_tejados = random.randint(15, 25) if z["municipio"] == "Madrid" else random.randint(0, 8)
    
    # Asignamos un potencial base para la formula del tejado ya que el clima se cargara por ETL desde data lake
    potencial_base_zona = round(random.uniform(4.2, 4.8), 2)
    
    for _ in range(num_tejados):
        area_bruta = round(random.uniform(12, 120), 2)
        area_util = round(area_bruta * 0.85, 2)
        ori = random.choices(list(FACTOR_ORIENTACION.keys()), weights=[0.35, 0.22, 0.18, 0.12, 0.08, 0.05])[0]
        tamano = "Pequeño" if area_util < 20 else ("Grande" if area_util > 50 else "Mediano")
        id_caract = next(c["id_caracteristica"] for c in caracteristicas if c["tamaño_categoria"] == tamano and c["orientacion_principal"] == ori)
        
        # Calculo de la nota usando el potencial base simulado
        nota = ((potencial_base_zona * area_util * FACTOR_ORIENTACION[ori] - 0.3) / (44.0 - 0.3)) * 10
        
        filas_tejados.append({
            "id_tejado": id_tejado, 
            "id_zona": z["id_zona"], 
            "id_caracteristica": id_caract, 
            "latitud": round(random.uniform(float(z["sur_lat_min"]), float(z["norte_lat_max"])), 6), 
            "longitud": round(random.uniform(float(z["oeste_lon_min"]), float(z["este_lon_max"])), 6), 
            "area_total_bruta_m2": area_bruta, 
            "area_util_m2": area_util, 
            "orientacion_grados": round({"Norte": 0, "Este": 90, "Sureste": 135, "Sur": 180, "Suroeste": 225, "Oeste": 270}[ori] + random.uniform(-8, 8), 1), 
            "orientacion_principal": ori, 
            "potencial_final": round(max(0.0, min(10.0, nota)), 2)
        })
        id_tejado += 1

if filas_tejados:
    guardar_csv("fact_tejados_detectados", filas_tejados, list(filas_tejados[0].keys()))

print("Se ha creado con exito.")