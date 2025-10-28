# ======================================================
# 🧮 PROCESAR RADIACIÓN HORARIA - Cálculo del Potencial Solar (0–100)
# ======================================================

import pandas as pd
import matplotlib.pyplot as plt

def procesar_radiacion_csv(nombre_archivo="era5_completo.csv"):
    """
    Lee el CSV generado por descargar_radiacion.py y calcula el
    potencial solar horario (0–100) a partir de la radiación solar,
    nubosidad y radiación instantánea.
    Guarda el dataset final como dataset_potencial_solar.csv.
    """

    print(f"📂 Leyendo datos de {nombre_archivo}...")
    df = pd.read_csv(nombre_archivo)

    # Normalizar nombres de columnas
    df.columns = [c.strip().lower() for c in df.columns]

    # Verificar columnas esperadas
    esperadas = ["time", "ssrd", "tcc"]
    for col in esperadas:
        if col not in df.columns:
            raise ValueError(f"❌ Falta la columna '{col}' en el CSV.")

    # Convertir columna de tiempo a datetime
    df["time"] = pd.to_datetime(df["time"])

    # Si no existe radiación instantánea, calcularla
    if "ssrd_instantanea" not in df.columns:
        df["ssrd_instantanea"] = df["ssrd"].diff().clip(lower=0)

    # ======================================================
    # ⚙️ Cálculo del Potencial Solar
    # ======================================================
    # Potencial = (radiación instantánea normalizada) * (1 - nubosidad) * 100

    ssrd_max = df["ssrd_instantanea"].max()
    if ssrd_max == 0:
        raise ValueError("❌ La radiación instantánea está vacía o es toda cero.")

    df["potencial_solar"] = (df["ssrd_instantanea"] / ssrd_max) * (1 - df["tcc"]) * 100

    # Asegurar límites de 0 a 100
    df["potencial_solar"] = df["potencial_solar"].clip(lower=0, upper=100)

    # ======================================================
    # 💾 Guardar dataset final
    # ======================================================
    salida = "dataset_potencial_solar.csv"
    df.to_csv(salida, index=False, float_format="%.2f")
    print(f"✅ Dataset procesado guardado: {salida}")

    # ======================================================
    # 📈 Gráfico del potencial solar horario
    # ======================================================
    plt.figure(figsize=(12, 6))
    plt.plot(df["time"], df["potencial_solar"], color="orange", linewidth=2)
    plt.title("☀️ Potencial Solar Horario (ERA5 - Octubre 2024)", fontsize=14)
    plt.xlabel("Fecha y hora")
    plt.ylabel("Índice de Potencial (0–100)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    # Mostrar muestra de resultados
    print("\n=== Muestra de resultados ===")
    print(df[["time", "ssrd_instantanea", "tcc", "potencial_solar"]].head(12))

    return df


# ======================================================
# 🚀 EJECUCIÓN DIRECTA
# ======================================================
if __name__ == "__main__":
    try:
        procesar_radiacion_csv()
        print("\n✅ Procesamiento completado con éxito.")
    except Exception as e:
        print(f"\n❌ Error durante el procesamiento: {e}")
