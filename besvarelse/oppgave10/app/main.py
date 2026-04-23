"""
main.py — FastAPI Applikasjonsserver
Oppgave 10A: NS 4102 Regnskapssystem — Valutakurs-Cache med Redis

Endepunkter:
  GET  /                          Helsestatus
  GET  /kurs/{fra}/{til}          Hent kurs (med cache)
  GET  /kurs/{fra}/{til}/frisk    Hent kurs (tving API-kall)
  GET  /kurser                    Liste alle cachede kurser
  POST /kurs/oppdater             Kjør cron-jobb manuelt
  GET  /statistikk/cache          Cache-ytelsesstatistikk
  GET  /statistikk/redis          Redis-serverinfo
  GET  /historikk/{fra}/{til}     Kurshistorikk fra PostgreSQL
  DELETE /cache                   Tøm hele cachen (for testing)

Cron-jobber (APScheduler):
  - Oppdater alle kurser hvert N sekunder (konfigurerbart)
"""

import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Optional

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from cache import valuta_cache
from config import API
from database import (hent_cache_statistikk, hent_kurshistorikk,
                      initialiser_skjema)
from kursservice import hent_kurs, oppdater_alle_kurser

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# APScheduler — Cron-planlegger
# ─────────────────────────────────────────────────────────────────────────────

planlegger = BackgroundScheduler(timezone="Europe/Oslo")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Oppstart- og avslutningslogikk for FastAPI."""
    # ── Oppstart ────────────────────────────────────────────────────────────
    log.info("=== NS 4102 Regnskapssystem starter ===")

    # 1. Initialiser PostgreSQL-skjema
    log.info("Initialiserer PostgreSQL-skjema...")
    initialiser_skjema()

    # 2. Sjekk Redis-tilkobling
    if valuta_cache.ping():
        log.info("Redis: tilkoblet ✓")
    else:
        log.warning("Redis: ikke tilgjengelig ✗")

    # 3. Kjør første kursoppdatering ved oppstart
    log.info("Kjører initial kursoppdatering...")
    oppdater_alle_kurser()

    # 4. Sett opp cron-jobb for periodisk oppdatering
    intervall = API.kurs_intervall
    planlegger.add_job(
        oppdater_alle_kurser,
        trigger='interval',
        seconds=intervall,
        id='kurs_oppdatering',
        name=f'Valutakursoppdatering (hvert {intervall}s)',
        replace_existing=True,
    )
    planlegger.start()
    log.info(f"Cron-jobb startet: oppdaterer kurser hvert {intervall}s")
    log.info("=== Applikasjonsserver klar ===")

    yield  # Applikasjonen kjører

    # ── Avslutning ──────────────────────────────────────────────────────────
    planlegger.shutdown()
    log.info("=== NS 4102 Regnskapssystem avsluttet ===")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI-applikasjon
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NS 4102 Regnskapssystem — Valutakurs-Cache",
    description=(
        "Oppgave 10A: Redis-cache for valutakurser med PostgreSQL-persistens. "
        "Demonstrerer Cache Hit/Miss-logikk, TTL og atomiske SQL-transaksjoner."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# Endepunkter
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", summary="Helsestatus")
def rot():
    """Returnerer helsestatus for alle tjenester."""
    redis_ok = valuta_cache.ping()
    return {
        "tjeneste": "NS 4102 Valutakurs-Cache",
        "status":   "ok",
        "redis":    "tilkoblet" if redis_ok else "ikke tilgjengelig",
        "cron":     "aktiv" if planlegger.running else "stoppet",
    }


@app.get("/kurs/{fra}/{til}", summary="Hent valutakurs (med cache)")
def hent_valutakurs(fra: str, til: str):
    """
    Henter valutakurs for et par med full cache-logikk.

    - **Cache Hit:** Returnerer umiddelbart fra Redis.
    - **Cache Miss:** Kaller eksternt API, oppdaterer Redis og PostgreSQL.
    """
    kurs = hent_kurs(fra, til)
    if kurs is None:
        raise HTTPException(
            status_code=503,
            detail=f"Kunne ikke hente kurs for {fra}/{til}"
        )

    # Sjekk om det var cache hit
    cached, ttl = valuta_cache.hent(fra, til)
    return {
        "fra":        fra.upper(),
        "til":        til.upper(),
        "kurs":       float(kurs),
        "cache":      "HIT" if cached else "MISS",
        "ttl":        ttl,
        "valutapar":  f"{fra.upper()}:{til.upper()}",
    }


@app.get("/kurs/{fra}/{til}/frisk", summary="Hent kurs (tving API-kall)")
def hent_frisk_kurs(fra: str, til: str):
    """
    Henter valutakurs direkte fra API, ignorerer cachen.
    Oppdaterer Redis og PostgreSQL med ny verdi.
    """
    kurs = hent_kurs(fra, til, tvungen_oppdatering=True)
    if kurs is None:
        raise HTTPException(
            status_code=503,
            detail=f"API-kall feilet for {fra}/{til}"
        )
    _, ttl = valuta_cache.hent(fra, til)
    return {
        "fra":       fra.upper(),
        "til":       til.upper(),
        "kurs":      float(kurs),
        "cache":     "OPPDATERT",
        "ttl":       ttl,
        "kilde":     "api_frisk",
    }


@app.get("/kurser", summary="Liste alle cachede kurser")
def liste_kurser():
    """Returnerer alle valutakurser som er lagret i Redis-cachen."""
    noekler = valuta_cache.hent_alle_noekler()
    kurser  = []
    for noekkel in noekler:
        deler = noekkel.split(":")
        if len(deler) == 3:
            fra, til = deler[1], deler[2]
            kurs, ttl = valuta_cache.hent(fra, til)
            if kurs is not None:
                kurser.append({
                    "valutapar": f"{fra}:{til}",
                    "kurs":      float(kurs),
                    "ttl":       ttl,
                })
    return {"antall": len(kurser), "kurser": kurser}


@app.post("/kurs/oppdater", summary="Kjør kursoppdatering manuelt")
def manuell_oppdatering():
    """Kjører cron-jobben for kursoppdatering manuelt (for testing)."""
    resultat = oppdater_alle_kurser()
    return {
        "melding":  "Kursoppdatering fullført",
        "suksess":  resultat["suksess"],
        "feil":     resultat["feil"],
    }


@app.get("/statistikk/cache", summary="Cache-ytelsesstatistikk")
def cache_statistikk():
    """
    Returnerer cache-ytelsesstatistikk fra PostgreSQL sin Kurslogg-tabell.
    Viser antall Cache Hits, Cache Misses og beregnet hit-rate.
    """
    return hent_cache_statistikk()


@app.get("/statistikk/redis", summary="Redis-serverinformasjon")
def redis_info():
    """Returnerer teknisk informasjon om Redis-serveren."""
    return valuta_cache.info()


@app.get("/historikk/{fra}/{til}", summary="Kurshistorikk fra PostgreSQL")
def kurshistorikk(fra: str, til: str, dager: int = 30):
    """
    Henter historiske valutakurser fra PostgreSQL.
    Viser hvordan kursene har utviklet seg over tid.
    """
    historikk = hent_kurshistorikk(fra, til, dager)
    return {
        "valutapar": f"{fra.upper()}:{til.upper()}",
        "dager":     dager,
        "antall":    len(historikk),
        "historikk": historikk,
    }


@app.delete("/cache", summary="Tøm cachen (for testing)")
def toem_cache():
    """Sletter alle valutakurser fra Redis-cachen. Kun for testformål."""
    antall = valuta_cache.slett_alle_kurser()
    return {
        "melding": f"Slettet {antall} nøkler fra Redis-cachen",
        "antall":  antall,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Oppstart
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,   # Sett True for utvikling med hot-reload
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
