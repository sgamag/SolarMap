# src/procesar_cams.py
import pandas as pd

def procesar_radiacion_csv(nombre_archivo="radiacion.csv"):
    """
    Procesa el archivo CSV descargado de CAMS y crea un dataset con
    columnas limpias y un índice de potencial solar (0-100).
    """

    print(f"📂 Leyendo datos de {nombre_archivo} ...")
    df = pd.read_csv(nombre_archivo)

    # Renombrar columnas para simplificar (según nombres típicos del CSV)
    df.columns = [col.lower().replace(" ", "_") for col in df.columns]

    # Asegurar que existan las columnas esperadas
    esperadas = ["time", "ssrd", "fdir", "fdif", "tcc"]
    for col in esperadas:
        if col not in df.columns:
            print(f"⚠️ Columna {col} no encontrada. Revisar CSV.")
    
    # Calcular el potencial solar como:
    #   (radiación global normalizada) * (1 - nubosidad)
    ssrd_max = df["ssrd"].max()
    df["potencial_solar"] = (df["ssrd"] / ssrd_max) * (1 - df["tcc"]) * 100

    # Guardar nuevo dataset limpio
    df.to_csv("dataset_potencial_solar.csv", index=False)
    print("✅ Dataset procesado y guardado como dataset_potencial_solar.csv")

    # Mostrar primeras filas
    print(df[["time", "ssrd", "tcc", "potencial_solar"]].head())

    return df


if __name__ == "__main__":
    procesar_radiacion_csv()
