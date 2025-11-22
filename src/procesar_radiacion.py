# src/procesar_potencial.py
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

def procesar_potencial_csv(csv_path: str, guardar_grafico=False):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {csv_path}")

    print("Leyendo:", csv_path)
    df = pd.read_csv(csv_path)

    # Normaliza nombres y verifica columnas
    df.columns = [c.strip() for c in df.columns]
    esperadas = {"valid_time", "ssrd_kWhm2", "t2m_C", "tcc"}
    faltan = esperadas - set(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas: {faltan}")

    # Tipos y limpieza mínima
    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce", utc=False)
    df = df.dropna(subset=["valid_time"])
    df["t2m_C"] = pd.to_numeric(df["t2m_C"], errors="coerce")
    df["tcc"]   = pd.to_numeric(df["tcc"], errors="coerce").clip(lower=0)
    df["ssrd_kWhm2"] = pd.to_numeric(df["ssrd_kWhm2"], errors="coerce").clip(lower=0)

    # Por si algún fichero trae nubosidad 0–100
    if df["tcc"].max() > 1:
        df["tcc"] = df["tcc"] / 100.0

    # Añade columnas de fecha para normalización mensual
    df["year"] = df["valid_time"].dt.year
    df["month"] = df["valid_time"].dt.month
    df["date"] = df["valid_time"].dt.date
    df = df.sort_values("valid_time")

    # Normalización mensual por P95 (robusta a picos)
    # p95_mes = percentil 95 de ssrd_kWhm2 dentro de cada (año, mes)
    p95 = (df.groupby(["year","month"])["ssrd_kWhm2"]
             .quantile(0.95)
             .rename("p95_mes"))
    df = df.merge(p95, on=["year","month"], how="left")
    # evita división por cero
    df["p95_mes"] = df["p95_mes"].replace(0, df["ssrd_kWhm2"].median() if df["ssrd_kWhm2"].median()>0 else 1e-6)

    # Componentes del índice
    df["ghi_norm"] = (df["ssrd_kWhm2"] / df["p95_mes"]).clip(upper=1.25)  # cap suave
    df["pen_nube"] = (1 - df["tcc"]).clip(lower=0) ** 0.8
    # penalización térmica (~0.4%/°C por encima de 25°C)
    exceso = (df["t2m_C"] - 25).clip(lower=0)
    df["pen_temp"] = (1 - 0.004 * exceso).clip(lower=0)

    # Potencial horario
    df["potencial_0_100"] = (100 * df["ghi_norm"] * df["pen_nube"] * df["pen_temp"]).clip(0, 100)

    # Redondeos de salida (dos decimales)
    for col in ["ssrd_kWhm2", "t2m_C", "tcc", "potencial_0_100"]:
        df[col] = df[col].round(2)

    # Selección de columnas finales
    cols_final = [c for c in ["valid_time","tile_id","latitude","longitude"] if c in df.columns]
    cols_final += ["ssrd_kWhm2","t2m_C","tcc","potencial_0_100"]
    df_out = df[cols_final].copy()

    # Guardar CSV
    out_csv = csv_path.with_name(csv_path.stem + "_potencial.csv")
    df_out.to_csv(out_csv, index=False)
    print("Guardado:", out_csv)

    # Gráfico opcional
    if guardar_grafico:
        plt.figure(figsize=(10,4))
        plt.plot(df_out["valid_time"], df_out["potencial_0_100"], lw=1.8)
        plt.title("Potencial solar horario (0–100)")
        plt.xlabel("Fecha")
        plt.ylabel("Índice")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        fig_path = csv_path.with_name(csv_path.stem + "_potencial.png")
        plt.savefig(fig_path, dpi=140)
        print("Gráfico:", fig_path)

    # Muestra
    print(df_out.head(10))
    return df_out

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv)>1 else "data/csv/tile_00_00/2000/2000_01.csv"
    procesar_potencial_csv(path, guardar_grafico=False)
