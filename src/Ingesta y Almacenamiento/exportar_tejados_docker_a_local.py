import subprocess
from pathlib import Path

RUTA_DESTINO = Path(
    r"C:\BigData1\PROYECTOBIGDATA\src\Ingesta y Almacenamiento\datos_tejados_detectados"
)

NOMBRE_CONTENEDOR = "solarmap_api_tejados"

RUTA_CSV_DOCKER = (
    "/app/src/Mapa y Modelo Tejados/src/Ingesta y Almacenamiento/"
    "datos_tejados_detectados/tejados_detectados_web.csv"
)

def main():
    RUTA_DESTINO.mkdir(parents=True, exist_ok=True)

    ruta_destino_csv = RUTA_DESTINO / "tejados_detectados_web.csv"

    comando = [
        "docker",
        "cp",
        f"{NOMBRE_CONTENEDOR}:{RUTA_CSV_DOCKER}",
        str(ruta_destino_csv)
    ]

    print("Copiando CSV desde Docker a local...")

    resultado = subprocess.run(
        comando,
        capture_output=True,
        text=True
    )

    if resultado.returncode != 0:
        print("Error al copiar el CSV.")
        print(resultado.stderr)
        return

    print("CSV copiado correctamente en:")
    print(ruta_destino_csv)


if __name__ == "__main__":
    main()