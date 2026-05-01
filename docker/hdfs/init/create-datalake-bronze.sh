#!/usr/bin/env bash
set -e

echo "==> Creando estructura HDFS..."

gribBASE="/datalake/datos/bronze/grib"
csvBASE="/datalake/datos/bronze/csv"
imagBASE="/datalake/datos/bronze/imagenes"
luzBASE="/datalake/datos/bronze/luz"

# ============================================================
# CREAR BASES (1 llamada cada una)
# ============================================================

hdfs dfs -mkdir -p \
  "$gribBASE" \
  "$csvBASE" \
  "$imagBASE" \
  "$luzBASE" \
  "$luzBASE/precio" \
  "$luzBASE/gas" \
  "$luzBASE/eolica" \
  "$luzBASE/solar"

# ============================================================
# TILES (36 llamadas en vez de 936)
# ============================================================

echo "==> Creando estructura de tiles..."

for i in $(seq 1 36); do
  tile=$(printf "%02d" "$i")

  hdfs dfs -mkdir -p \
    "$gribBASE/tile${tile}" \
    "$csvBASE/tile${tile}" \
    "$imagBASE/tile${tile}"
done

# ============================================================
# AÑOS (solo para grib y csv)
# ============================================================

echo "==> Creando estructura anual..."

for year in $(seq 2000 2025); do
  for i in $(seq 1 36); do
    tile=$(printf "%02d" "$i")

    hdfs dfs -mkdir -p \
      "$gribBASE/tile${tile}/$year" \
      "$csvBASE/tile${tile}/$year"
  done
done

# ============================================================

echo "==> Terminado"