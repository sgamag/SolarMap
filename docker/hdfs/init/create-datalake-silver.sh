#!/usr/bin/env bash
set -e

echo "==> Creando estructura SILVER..."

climaBASE="/datalake/datos/silver/Clima"
imagBASE="/datalake/datos/silver/Imagenes"
luzBASE="/datalake/datos/silver/luz"
combinadoBASE="$luzBASE/precio/suelto"

# ============================================================
# BASES
# ============================================================

hdfs dfs -mkdir -p \
  "$climaBASE" \
  "$imagBASE/Produccion" \
  "$imagBASE/Entreno/test" \
  "$imagBASE/Entreno/train" \
  "$imagBASE/Entreno/train_mask" \
  "$imagBASE/Entreno/validate" \
  "$imagBASE/Entreno/validate_mask" \
  "$luzBASE/precio/suelto" \
  "$luzBASE/precio/combinado" \
  "$luzBASE/gas" \
  "$luzBASE/eolica" \
  "$luzBASE/solar" \
  "$combinadoBASE"

# ============================================================
# COMBINADO 2018–2025
# ============================================================

echo "==> Creando estructura combinada anual..."

hdfs dfs -mkdir -p \
  "$combinadoBASE/2018" \
  "$combinadoBASE/2019" \
  "$combinadoBASE/2020" \
  "$combinadoBASE/2021" \
  "$combinadoBASE/2022" \
  "$combinadoBASE/2023" \
  "$combinadoBASE/2024" \
  "$combinadoBASE/2025"

echo "==> SILVER structure created successfully."

# ============================================================
# TILES CLIMA + IMÁGENES PRODUCCIÓN
# ============================================================

echo "==> Creando estructura de tiles..."

for i in $(seq 1 36); do
  tile=$(printf "%02d" "$i")

  hdfs dfs -mkdir -p \
    "$climaBASE/tile${tile}" \
    "$imagBASE/Produccion/tile${tile}"
done

# ============================================================
# AÑOS CLIMA
# ============================================================

echo "==> Creando estructura anual de Clima..."

for year in $(seq 2000 2025); do
  for i in $(seq 1 36); do
    tile=$(printf "%02d" "$i")

    hdfs dfs -mkdir -p "$climaBASE/tile${tile}/$year"
  done
done

