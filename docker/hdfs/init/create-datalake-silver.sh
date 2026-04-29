#!/usr/bin/env bash
set -e

echo "==> Waiting for HDFS..."

gribBASE="/datalake/datos/silver/Clima"

echo "==> Creating CSV tile structure..."

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

echo "==> Creating CSV tile structure..."

imagBASE="/datalake/datos/silver/Imagenes"

imagBASE="/datalake/datos/silver/Imagenes/Produccion"

for tile in $(seq -w 1 36); do
  TILE_PATH="$imagBASE/tile${tile}"
  hdfs dfs -mkdir -p $TILE_PATH 
done

imagBASE="/datalake/datos/silver/Imagenes/Entreno"

hdfs dfs -mkdir -p $imagBASE/test
hdfs dfs -mkdir -p $imagBASE/train_mask
hdfs dfs -mkdir -p $imagBASE/train
hdfs dfs -mkdir -p $imagBASE/train_mask
hdfs dfs -mkdir -p $imagBASE/validate
hdfs dfs -mkdir -p $imagBASE/validate_mask

echo "==> Image structure created successfully."