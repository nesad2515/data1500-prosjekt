"""
config.py — Konfigurasjon fra miljøvariabler
Oppgave 11: MongoDB Staging
"""
import os
from dataclasses import dataclass


@dataclass
class PostgresKonfig:
    host:    str = os.getenv("DB_HOST",     "")
    port:    int = int(os.getenv("DB_PORT", "5432"))
    navn:    str = os.getenv("DB_NAME",     "regnskap_oppgave11")
    bruker:  str = os.getenv("DB_USER",     "ubuntu")
    passord: str = os.getenv("DB_PASSWORD", "")

    @property
    def dsn(self) -> str:
        if not self.host:
            base = f"dbname={self.navn} user={self.bruker}"
            return base + (f" password={self.passord}" if self.passord else "")
        base = f"host={self.host} port={self.port} dbname={self.navn} user={self.bruker}"
        return base + (f" password={self.passord}" if self.passord else "")


@dataclass
class MongoKonfig:
    uri:    str = os.getenv("MONGO_URI",  "mongodb://localhost:27017/finansdata")
    db:     str = os.getenv("MONGO_DB",   "finansdata")


@dataclass
class APIKonfig:
    alpha_vantage_key: str = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
    alpha_vantage_url: str = "https://www.alphavantage.co/query"
    valuta_api_url:    str = os.getenv("VALUTA_API_URL", "https://open.er-api.com/v6/latest")


@dataclass
class AppKonfig:
    etl_intervall: int = int(os.getenv("ETL_INTERVALL_SEKUNDER", "3600"))
    log_level:     str = os.getenv("LOG_LEVEL", "INFO")


# Singleton-instanser
PG    = PostgresKonfig()
MONGO = MongoKonfig()
API   = APIKonfig()
APP   = AppKonfig()
