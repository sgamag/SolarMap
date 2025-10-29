# ======================================================
# 🧮 PROCESAR RADIACIÓN - Cálculo del Potencial Solar
# ======================================================

import pandas as pd
import matplotlib.pyplot as plt

def procesar_radiacion_csv(nombre_archivo="radiacion.csv"):
    """
    Lee el CSV generado por descargar_radiacion.py y calcula el potencial solar (0–100).
    Guarda el dataset final con los valores procesados.
    """
    print(f"📂 Leyendo datos de {nombre_archivo}...")
    df = pd.read_csv(nombre_archivo)

    ssrd_col = next((c for c in df.columns if "ssrd" in c), None)
    tcc_col  = next((c for c in df.columns if "tcc" in c), None)

    if not ssrd_col or not tcc_col:
        raise ValueError(f"No se encontraron columnas esperadas. Columnas: {list(df.columns)}")

    ssrd_max = df[ssrd_col].max()
    df["potencial_solar"] = (df[ssrd_col] / ssrd_max) * (1 - df[tcc_col]) * 100

    df.to_csv("dataset_potencial_solar.csv", index=False, float_format="%.2f")

    print("✅ Dataset guardado: dataset_potencial_solar.csv")

    print("\n=== Muestra de resultados ===")
    print(df[["time", ssrd_col, tcc_col, "potencial_solar"]].head())

    # 📈 Gráfico rápido
    plt.figure(figsize=(10, 5))
    plt.plot(df["time"], df["potencial_solar"], color="orange", marker="o", linewidth=2)
    plt.title("☀ Potencial Solar Diario (Madrid, Octubre 2024)")
    plt.xlabel("Fecha y hora")
    plt.ylabel("Índice de Potencial (0–100)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    return df


if _name_ == "_main_":
    procesar_radiacion_csv()