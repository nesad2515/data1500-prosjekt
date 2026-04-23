"""
main.py — FastAPI-applikasjonsserver med APScheduler cron-jobb
Oppgave: MongoDB Staging

REST API-endepunkter:
  GET  /helse                     — Helsekontroll
  GET  /verdipapirer              — Liste over overvåkede verdipapirer
  GET  /kurser/{ticker}           — Siste kurser fra PostgreSQL
  POST /etl/{ticker}              — Kjør ETL manuelt for ett verdipapir
  POST /etl/alle                  — Kjør ETL for alle verdipapirer
  GET  /staging/{ticker}          — Vis MongoDB-dokumenter for ett verdipapir
  GET  /staging/ubehandlet        — Vis ubehandlede MongoDB-dokumenter
  GET  /statistikk/etl            — ETL-statistikk fra PostgreSQL
  GET  /statistikk/staging        — Staging-statistikk fra MongoDB
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException

from config import APP
from database import (
    initialiser_skjema,
    hent_kurshistorikk,
    hent_etl_statistikk
)
from etl_pipeline import (
    kjor_etl_for_ticker,
    kjor_full_etl,
    OVERVAKEDE_VERDIPAPIRER
)
from staging import (
    initialiser_collections,
    hent_dokument_for_ticker,
    hent_ubehandlede_dokumenter,
    hent_staging_statistikk
)

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, APP.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# ── Scheduler ────────────────────────────────────────────────
scheduler = BackgroundScheduler()


# ── Lifespan (oppstart og avslutning) ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Kjøres ved oppstart og avslutning av applikasjonen."""
    log.info("=== Oppgave: MongoDB Staging — Starter ===")

    # Initialiser databaser
    try:
        initialiser_skjema()
        log.info("PostgreSQL-skjema klart")
    except Exception as e:
        log.error(f"PostgreSQL-initialisering feilet: {e}")

    try:
        initialiser_collections()
        log.info("MongoDB collections klare")
    except Exception as e:
        log.error(f"MongoDB-initialisering feilet: {e}")

    # Sett opp cron-jobb
    scheduler.add_job(
        kjor_full_etl,
        "interval",
        seconds=APP.etl_intervall,
        id="full_etl",
        replace_existing=True,
        max_instances=1
    )
    scheduler.start()
    log.info(f"APScheduler startet — ETL kjøres hvert {APP.etl_intervall}s")

    yield  # Applikasjonen kjører

    scheduler.shutdown(wait=False)
    log.info("=== Applikasjon avsluttet ===")


# ── FastAPI-app ───────────────────────────────────────────────
app = FastAPI(
    title="Oppgave 10B: MongoDB Staging",
    description="ETL-pipeline for finansielle kursdata — NS 4102 Regnskapssystem",
    version="1.0.0",
    lifespan=lifespan
)


# ── Endepunkter ───────────────────────────────────────────────

@app.get("/helse", tags=["System"])
def helse():
    return {
        "status":    "OK",
        "tidspunkt": datetime.now().isoformat(),
        "tjeneste":  "Oppgave 10B MongoDB Staging"
    }


@app.get("/verdipapirer", tags=["Verdipapirer"])
def list_verdipapirer():
    """Returnerer listen over overvåkede verdipapirer."""
    return {"verdipapirer": OVERVAKEDE_VERDIPAPIRER}


@app.get("/kurser/{ticker}", tags=["Kurser"])
def hent_kurser(ticker: str, antall: int = 10):
    """Henter de siste N kursene for et verdipapir fra PostgreSQL."""
    kurser = hent_kurshistorikk(ticker.upper(), antall)
    if not kurser:
        raise HTTPException(404, f"Ingen kurser funnet for {ticker}")
    return {"ticker": ticker.upper(), "antall": len(kurser), "kurser": kurser}


@app.post("/etl/{ticker}", tags=["ETL"])
def kjor_etl_manuelt(ticker: str):
    """Kjører ETL-pipelinen manuelt for ett verdipapir."""
    log.info(f"Manuell ETL-kjøring for {ticker}")
    resultat = kjor_etl_for_ticker(ticker.upper())
    if not resultat["suksess"]:
        raise HTTPException(500, resultat["feilmelding"])
    return resultat


@app.post("/etl/alle", tags=["ETL"])
def kjor_etl_alle():
    """Kjører ETL-pipelinen for alle overvåkede verdipapirer."""
    log.info("Manuell full ETL-kjøring startet")
    resultater = kjor_full_etl()
    return {
        "totalt":      len(resultater),
        "vellykkede":  sum(1 for r in resultater if r["suksess"]),
        "resultater":  resultater
    }


@app.get("/staging/{ticker}", tags=["MongoDB Staging"])
def hent_staging_for_ticker(ticker: str, antall: int = 5):
    """Henter de siste N MongoDB-dokumentene for et verdipapir."""
    dokumenter = hent_dokument_for_ticker(ticker.upper(), antall)
    # Konverter ObjectId til streng for JSON-serialisering
    for dok in dokumenter:
        dok["_id"] = str(dok["_id"])
    return {"ticker": ticker.upper(), "antall": len(dokumenter), "dokumenter": dokumenter}


@app.get("/staging/ubehandlet", tags=["MongoDB Staging"])
def hent_ubehandlet():
    """Henter alle MongoDB-dokumenter med etl_status = 'STAGED'."""
    dokumenter = hent_ubehandlede_dokumenter()
    for dok in dokumenter:
        dok["_id"] = str(dok["_id"])
    return {"antall": len(dokumenter), "dokumenter": dokumenter}


@app.get("/statistikk/etl", tags=["Statistikk"])
def etl_statistikk():
    """Henter aggregert ETL-statistikk fra PostgreSQL ETL_Logg."""
    return {"statistikk": hent_etl_statistikk()}


@app.get("/statistikk/staging", tags=["Statistikk"])
def staging_statistikk():
    """Henter aggregert staging-statistikk fra MongoDB."""
    statistikk = hent_staging_statistikk()
    # Konverter ObjectId til streng
    for s in statistikk:
        if "_id" in s:
            s["ticker"] = s.pop("_id")
    return {"statistikk": statistikk}
