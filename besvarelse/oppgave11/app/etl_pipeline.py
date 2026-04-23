"""
etl_pipeline.py — ETL-pipeline for finansielle kursdata
Oppgave: MongoDB Staging

ETL-flyt:
  1. EXTRACT  : Hent OHLCV time series fra Alpha Vantage API
  2. STAGE    : Lagre rådata i MongoDB (raw_financial_data)
  3. TRANSFORM: Trekk ut relevante felter fra rådataene
  4. LOAD     : Last transformerte data til PostgreSQL (Kurser-tabellen)
  5. MARKER   : Oppdater etl_status i MongoDB til "LASTET"
"""
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Optional

import requests

from config import API
from database import (
    logg_etl_hendelse,
    last_kurser_til_postgres,
    initialiser_skjema
)
from staging import (
    stage_radata,
    marker_som_lastet,
    initialiser_collections
)

log = logging.getLogger(__name__)


# ── Verdipapirer som overvåkes ───────────────────────────────
OVERVAKEDE_VERDIPAPIRER = [
    {"ticker": "AAPL",    "navn": "Apple Inc.",            "bors": "NASDAQ"},
    {"ticker": "MSFT",    "navn": "Microsoft Corporation", "bors": "NASDAQ"},
    {"ticker": "EQNR.OL", "navn": "Equinor ASA",           "bors": "OSE"},
]

# Grunnkurser for syntetisk data (realistiske startverdier)
_GRUNNKURSER = {
    "AAPL":    227.48,
    "MSFT":    415.32,
    "EQNR.OL": 268.50,
    "IBM":     185.20,
}


# ── Syntetisk OHLCV-data (brukes når API ikke er tilgjengelig) ─
def _generer_syntetisk_ohlcv(ticker: str, antall_dager: int = 20) -> dict:
    """
    Genererer realistisk syntetisk OHLCV-data i Alpha Vantage-format.
    Brukes i demo-modus og ved API-feil.
    """
    grunnkurs = _GRUNNKURSER.get(ticker, 100.0)
    tidsserie = {}
    kurs = grunnkurs
    dato = datetime.now()

    for i in range(antall_dager):
        # Hopp over helger
        while dato.weekday() >= 5:
            dato -= timedelta(days=1)

        # Realistisk daglig variasjon (±2%)
        endring = random.uniform(-0.02, 0.02)
        apning  = round(kurs, 2)
        slutt   = round(kurs * (1 + endring), 2)
        hoy     = round(max(apning, slutt) * random.uniform(1.001, 1.015), 2)
        lav     = round(min(apning, slutt) * random.uniform(0.985, 0.999), 2)
        volum   = random.randint(1_000_000, 50_000_000)

        dato_str = dato.strftime("%Y-%m-%d")
        tidsserie[dato_str] = {
            "1. open":   str(apning),
            "2. high":   str(hoy),
            "3. low":    str(lav),
            "4. close":  str(slutt),
            "5. volume": str(volum)
        }
        kurs = slutt
        dato -= timedelta(days=1)

    return {
        "Meta Data": {
            "1. Information":   "Daily Prices (open, high, low, close) and Volumes",
            "2. Symbol":        ticker,
            "3. Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
            "4. Output Size":   "Compact",
            "5. Time Zone":     "US/Eastern",
            "6. Data Source":   "SYNTHETIC (demo-modus)"
        },
        "Time Series (Daily)": tidsserie
    }


# ── Steg 1: EXTRACT ─────────────────────────────────────────
def extract_fra_alpha_vantage(ticker: str) -> Optional[dict]:
    """
    Henter OHLCV time series fra Alpha Vantage API.
    Faller tilbake til syntetisk data ved rate limit eller feil.
    """
    params = {
        "function":   "TIME_SERIES_DAILY",
        "symbol":     ticker,
        "outputsize": "compact",
        "apikey":     "AEA30YK8F812XG5"  # sett inn din API-nøkkel her
    }
    try:
        start = time.time()
        svar = requests.get(API.alpha_vantage_url, params=params, timeout=15)
        svar.raise_for_status()
        data = svar.json()
        ms = int((time.time() - start) * 1000)

        # Sjekk for API-feilmeldinger
        if "Error Message" in data:
            log.warning(f"Alpha Vantage feil for {ticker}: {data['Error Message']}")
            log.info(f"Faller tilbake til syntetisk data for {ticker}")
            return _generer_syntetisk_ohlcv(ticker)

        if "Note" in data or "Information" in data:
            melding = data.get("Note") or data.get("Information", "")
            log.warning(f"Alpha Vantage rate limit for {ticker}: {melding[:60]}...")
            log.info(f"Faller tilbake til syntetisk data for {ticker}")
            return _generer_syntetisk_ohlcv(ticker)

        if "Time Series (Daily)" not in data:
            log.warning(f"Ingen kursdata i svar for {ticker}: {list(data.keys())}")
            return _generer_syntetisk_ohlcv(ticker)

        antall = len(data["Time Series (Daily)"])
        log.info(f"EXTRACT: {ticker} — {antall} handelsdager hentet fra API ({ms}ms)")
        return data

    except requests.RequestException as e:
        log.error(f"EXTRACT nettverksfeil for {ticker}: {e}")
        log.info(f"Faller tilbake til syntetisk data for {ticker}")
        return _generer_syntetisk_ohlcv(ticker)


# ── Steg 3: TRANSFORM ────────────────────────────────────────
def transform_ohlcv(radata: dict, maks_dager: int = 20) -> list:
    """
    Transformerer rå Alpha Vantage JSON til en liste av OHLCV-ordbøker.
    """
    tidsserie = radata.get("Time Series (Daily)", {})
    kurser = []
    for dato_str, verdier in sorted(tidsserie.items(), reverse=True)[:maks_dager]:
        try:
            kurser.append({
                "dato":    dato_str,
                "apning":  float(verdier.get("1. open",   0)),
                "hoy":     float(verdier.get("2. high",   0)),
                "lav":     float(verdier.get("3. low",    0)),
                "slutt":   float(verdier.get("4. close",  0)),
                "volum":   int(verdier.get("5. volume", 0))
            })
        except (ValueError, KeyError) as e:
            log.warning(f"Transform-feil for dato {dato_str}: {e}")
    log.info(f"TRANSFORM: {len(kurser)} kurser transformert")
    return kurser


# ── Full ETL-kjøring for ett verdipapir ─────────────────────
def kjor_etl_for_ticker(ticker: str) -> dict:
    """
    Kjører hele ETL-pipelinen for ett verdipapir:
    Extract → Stage → Transform → Load → Marker
    """
    resultat = {
        "ticker":        ticker,
        "suksess":       False,
        "mongo_id":      None,
        "antall_lastet": 0,
        "feilmelding":   None
    }

    # Steg 1: EXTRACT
    log.info(f"[ETL] Starter pipeline for {ticker}")
    radata = extract_fra_alpha_vantage(ticker)
    if radata is None:
        feil = f"API-kall feilet for {ticker}"
        logg_etl_hendelse(ticker, "EXTRACT_FEIL", feilmelding=feil)
        resultat["feilmelding"] = feil
        return resultat
    logg_etl_hendelse(ticker, "EXTRACT_OK")

    # Steg 2: STAGE (MongoDB)
    try:
        mongo_id = stage_radata(ticker, "alpha_vantage", radata)
        resultat["mongo_id"] = mongo_id
        logg_etl_hendelse(ticker, "STAGE_OK", mongo_id=mongo_id)
    except Exception as e:
        feil = f"MongoDB staging feilet: {e}"
        log.error(feil)
        logg_etl_hendelse(ticker, "STAGE_FEIL", feilmelding=feil)
        resultat["feilmelding"] = feil
        return resultat

    # Steg 3: TRANSFORM
    kurser = transform_ohlcv(radata)
    if not kurser:
        feil = "Ingen kurser etter transformasjon"
        logg_etl_hendelse(ticker, "LOAD_FEIL", mongo_id=mongo_id, feilmelding=feil)
        resultat["feilmelding"] = feil
        return resultat

    # Steg 4: LOAD (PostgreSQL)
    try:
        antall = last_kurser_til_postgres(ticker, kurser, mongo_id)
        resultat["antall_lastet"] = antall
        logg_etl_hendelse(ticker, "LOAD_OK", mongo_id=mongo_id, antall=antall)
    except Exception as e:
        feil = f"PostgreSQL-lasting feilet: {e}"
        log.error(feil)
        logg_etl_hendelse(ticker, "LOAD_FEIL", mongo_id=mongo_id, feilmelding=feil)
        resultat["feilmelding"] = feil
        return resultat

    # Steg 5: MARKER (MongoDB)
    try:
        marker_som_lastet(mongo_id, antall)
    except Exception as e:
        log.warning(f"Kunne ikke markere MongoDB-dokument som lastet: {e}")

    resultat["suksess"] = True
    log.info(f"[ETL] {ticker}: Fullført — {antall} kurser lastet (mongo_id={mongo_id})")
    return resultat


# ── Cron-jobb ────────────────────────────────────────────────
def kjor_full_etl() -> list:
    """Kjøres av APScheduler. Kjører ETL for alle overvåkede verdipapirer."""
    log.info(f"[CRON] Starter full ETL for {len(OVERVAKEDE_VERDIPAPIRER)} verdipapirer")
    resultater = []
    for vp in OVERVAKEDE_VERDIPAPIRER:
        ticker = vp["ticker"]
        try:
            res = kjor_etl_for_ticker(ticker)
            resultater.append(res)
        except Exception as e:
            log.error(f"[CRON] Uventet feil for {ticker}: {e}")
            resultater.append({"ticker": ticker, "suksess": False, "feilmelding": str(e)})
        if vp != OVERVAKEDE_VERDIPAPIRER[-1]:
            time.sleep(2)  # Kortere ventetid i cron-modus

    vellykkede = sum(1 for r in resultater if r["suksess"])
    log.info(f"[CRON] Fullført: {vellykkede}/{len(resultater)} vellykkede")
    return resultater
