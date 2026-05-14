import csv
import mysql.connector
from pathlib import Path

# =========================
# CONFIG
# =========================

DB_HOST = "10.151.30.2"
DB_PORT = 3306
DB_USER = "bd_rvm_solar_map"
DB_PASS = "Mar123Qz"
DB_NAME = "bd_rvm_solar_map"

CSV_PATH = Path(
    "datos_tejados_detectados/tejados_detectados_web.csv"
)

# =========================
# MAIN
# =========================

conexion = mysql.connector.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASS,
    database=DB_NAME,
    ssl_disabled=True
)

cursor = conexion.cursor()

with open(CSV_PATH, "r", encoding="utf-8") as f:

    lector = csv.DictReader(f)

    for fila in lector:

        query = """
        INSERT INTO fact_tejados_detectados
        (
            id_zona,
            id_caracteristica,
            latitud,
            longitud,
            area_total_bruta_m2,
            area_util_m2,
            orientacion_grados,
            orientacion_principal,
            potencial_final
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        valores = (
        "tile_00_00",
        1,
        fila["latitud"],
        fila["longitud"],
        fila["area_total_bruta_m2"],
        fila["area_util_m2"],
        fila["orientacion_grados"],
        fila["orientacion_principal"],
        None
    )

        cursor.execute(query, valores)

conexion.commit()

cursor.close()
conexion.close()

print("Tejados web insertados correctamente")