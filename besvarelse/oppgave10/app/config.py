"""
config.py — Konfigurasjon for NS 4102 Regnskapssystem
Henter innstillinger fra miljøvariabler (satt i docker-compose.yml)
"""

import os
from dataclasses import dataclass


@dataclass
class DatabaseKonfig:
    host:     str = os.getenv("DB_HOST",     "localhost")
    port:     int = int(os.getenv("DB_PORT", "5432"))
    navn:     str = os.getenv("DB_NAME",     "regnskap")
    bruker:   str = os.getenv("DB_USER",     "regnskap_user")
    passord:  str = os.getenv("DB_PASSWORD", "regnskap_pass")

    @property
    def dsn(self) -> str:
        # Hvis host er tom, bruk Unix socket (ingen host= i DSN)
        if not self.host:
            base = f"dbname={self.navn} user={self.bruker}"
            return base + (f" password={self.passord}" if self.passord else "")
        base = f"host={self.host} port={self.port} dbname={self.navn} user={self.bruker}"
        return base + (f" password={self.passord}" if self.passord else "")


@dataclass
class RedisKonfig:
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    ttl:  int = int(os.getenv("CACHE_TTL_SEKUNDER", "3600"))  # 1 time


@dataclass
class ApiKonfig:
    valuta_url:      str = os.getenv("VALUTA_API_URL",
                                     "https://open.er-api.com/v6/latest")
    norges_bank_url: str = os.getenv("NORGES_BANK_API_URL",
                                     "https://data.norges-bank.no/api/data/EXR")
    kurs_intervall:  int = int(os.getenv("KURS_OPPDATERING_INTERVALL", "3600"))


# Globale konfigurasjonsobjekter
DB    = DatabaseKonfig()
REDIS = RedisKonfig()
API   = ApiKonfig()
