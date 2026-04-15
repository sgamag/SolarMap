#!/usr/bin/env bash
set -e

echo "==> Waiting for HDFS..."

gribBASE="/datalake/datos/bronze/grib"

echo "==> Creating GRIB tile structure..."

# Crear base
hdfs dfs -mkdir -p $gribBASE

# Loop tiles (01 a 36)
for tile in $(seq -w 1 36); do
  TILE_PATH="$gribBASE/tile${tile}"
  hdfs dfs -mkdir -p $TILE_PATH

  # Años 2000 a 2025
  for year in $(seq 2000 2025); do
    YEAR_PATH="$TILE_PATH/$year"
    hdfs dfs -mkdir -p $YEAR_PATH
  done  
done

imagBASE="/datalake/datos/bronze/imagenes"

echo "==> Creating image tile structure..."

hdfs dfs -mkdir -p $imagBASE

for tile in $(seq -w 1 36); do
  TILE_PATH="$imagBASE/tile${tile}"
  hdfs dfs -mkdir -p $TILE_PATH 
done


echo "==> GRIB tile structure created successfully."
echo "==> Image tile structure created successfully."