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

imagBASE="/datalake/datos/silver/Imagenes"

hdfs dfs -mkdir -p $imagBASE

hdfs dfs -mkdir -p $imagBASE/Entreno/Complex_data
hdfs dfs -mkdir -p $imagBASE/Entreno/Gable_hip_other
hdfs dfs -mkdir -p $imagBASE/Entreno/Bugs
hdfs dfs -mkdir -p $imagBASE/Entreno/Flat_Data

imagBASE="/datalake/datos/silver/Imagenes/Produccion"

for tile in $(seq -w 1 36); do
  TILE_PATH="$imagBASE/tile${tile}"
  hdfs dfs -mkdir -p $TILE_PATH 
done

echo "==> Image structure created successfully."