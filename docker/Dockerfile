FROM python:3.11-slim

# Instalamos dependencias del sistema mínimas (GDAL y compresiones por si acaso)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiamos el requirements del proyecto
COPY requirements.txt /app/requirements.txt

# Instalamos las librerías Python
RUN pip install --no-cache-dir -r /app/requirements.txt

# Por defecto solo entra a bash (el comando real lo pondrá docker compose)
CMD ["bash"]
