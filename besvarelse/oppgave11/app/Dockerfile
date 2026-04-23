FROM python:3.11-slim

WORKDIR /app

# Installer systemavhengigheter for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Kopier og installer Python-avhengigheter
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopier kildekode
COPY . .

# Eksponér port for FastAPI
EXPOSE 8001

# Helsekontroll
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/helse || exit 1

# Start applikasjonsserveren
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
