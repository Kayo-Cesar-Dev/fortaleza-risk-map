# Usar Python 3.12 (compatível com pandas + geopandas)
FROM python:3.12-slim

# Instalar dependências de sistema para geopandas/fiona/shapely
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Criar pasta do app
WORKDIR /app

# Copiar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar restante do projeto
COPY . .

# Expor porta
EXPOSE 10000

# Comando para executar no Render
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
