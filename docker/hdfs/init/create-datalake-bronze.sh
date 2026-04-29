#!/usr/bin/env bash
set -e

echo "==> Waiting for HDFS..."

gribBASE="/datalake/datos/bronze/grib"
csvBASE="/datalake/datos/bronze/csv"
imagBASE="/datalake/datos/bronze/imagenes"

echo "==> Creating GRIB tile structure..."

hdfs dfs -mkdir -p "$gribBASE"

for i in $(seq 1 36); do
  tile=$(printf "%02d" "$i")
  TILE_PATH="$gribBASE/tile${tile}"
  hdfs dfs -mkdir -p "$TILE_PATH"

  for year in $(seq 2000 2025); do
    YEAR_PATH="$TILE_PATH/$year"
    hdfs dfs -mkdir -p "$YEAR_PATH"
  done
done

echo "==> Creating CSV tile structure..."

hdfs dfs -mkdir -p "$csvBASE"

for i in $(seq 1 36); do
  tile=$(printf "%02d" "$i")
  TILE_PATH="$csvBASE/tile${tile}"
  hdfs dfs -mkdir -p "$TILE_PATH"

  for year in $(seq 2000 2025); do
    YEAR_PATH="$TILE_PATH/$year"
    hdfs dfs -mkdir -p "$YEAR_PATH"
  done
done

echo "==> Creating image tile structure..."

hdfs dfs -mkdir -p "$imagBASE"

for i in $(seq 1 36); do
  tile=$(printf "%02d" "$i")
  TILE_PATH="$imagBASE/tile${tile}"
  hdfs dfs -mkdir -p "$TILE_PATH"
done

echo "==> GRIB tile structure created successfully."
echo "==> CSV tile structure created successfully."
echo "==> Image tile structure created successfully."