# ============================================================
# Dockerfile — Python 3.11 Applikasjonsserver
# Oppgave 10A: NS 4102 Regnskapssystem
# ============================================================

FROM python:3.11-slim

# Sett arbeidskatalog
WORKDIR /app

# Installer systemavhengigheter (psycopg2 trenger libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Kopier og installer Python-avhengigheter
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopier applikasjonskode
COPY . .

# Eksponér FastAPI-porten
EXPOSE 8000

# Start applikasjonen
CMD ["python", "-u", "main.py"]
