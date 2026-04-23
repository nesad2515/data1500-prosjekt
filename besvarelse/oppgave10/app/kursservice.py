"""
kursservice.py — Valutakurstjeneste med Redis-cache
Oppgave 10A: NS 4102 Regnskapssystem

Implementerer den fullstendige cache-logikken:
  1. Sjekk Redis (Cache Hit → returner umiddelbart)
  2. Cache Miss → kall eksternt API
  3. Lagre i Redis med TTL
  4. Lagre i PostgreSQL (atomisk transaksjon)
"""

import logging
import time
from decimal import Decimal
from typing import Optional

import requests

from cache import valuta_cache
from config import API
from database import lagre_kurs_atomisk, logg_cache_hendelse

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Ekstern API-integrasjon
# ─────────────────────────────────────────────────────────────────────────────

def hent_kurs_fra_api(fra_kode: str, til_kode: str) -> Optional[Decimal]:
    """
    Henter valutakurs fra ExchangeRate-API (ingen API-nøkkel nødvendig).

    URL-format: https://open.er-api.com/v6/latest/{FRA_KODE}
    Returnerer kursen som Decimal, eller None ved feil.
    """
    url = f"{API.valuta_url}/{fra_kode.upper()}"
    start = time.monotonic()

    try:
        respons = requests.get(url, timeout=10)
        responstid_ms = int((time.monotonic() - start) * 1000)
        respons.raise_for_status()

        data = respons.json()

        if data.get("result") != "success":
            log.warning(f"API returnerte ikke suksess: {data.get('result')}")
            return None

        kurser = data.get("rates", {})
        kurs_verdi = kurser.get(til_kode.upper())

        if kurs_verdi is None:
            log.warning(f"Kurs ikke funnet for {til_kode} i API-respons")
            return None

        kurs = Decimal(str(kurs_verdi))
        log.info(f"API-kurs hentet: {fra_kode}/{til_kode} = {kurs:.6f} "
                 f"({responstid_ms}ms)")
        return kurs

    except requests.Timeout:
        log.error(f"API-kall tidsavbrutt for {fra_kode}/{til_kode}")
        return None
    except requests.RequestException as e:
        log.error(f"API-kall feilet for {fra_kode}/{til_kode}: {e}")
        return None


def hent_kurser_fra_norges_bank(valutakoder: list[str]) -> dict[str, Decimal]:
    """
    Henter offisielle norske valutakurser fra Norges Bank sitt åpne data-API.
    Returnerer en dict med valutakode → kurs mot NOK.

    API-dokumentasjon: https://www.norges-bank.no/en/topics/statistics/open-data/
    Eksempel:
    http://data.norges-bank.no/api/data/EXR/
    B.USD.NOK.SP
    ?format=sdmx-json
    &startPeriod=2026-03-13
    &endPeriod=2026-03-13
    &detail=dataonly
    &locale=no

    format kan også være excel-both, f.eks.
    """
    kurser = {}

    for kode in valutakoder:
        url = (
            f"{API.norges_bank_url}/B.{kode.upper()}.NOK.SP"
            f"?startPeriod={_dagens_dato()}&endPeriod={_dagens_dato()}"
            f"&format=sdmx-json&detail=dataonly&locale=no"
        )
        try:
            respons = requests.get(url, timeout=10)
            if respons.status_code == 200:
                data = respons.json()
                # Naviger SDMX-JSON-strukturen
                serier = (data.get("data", {})
                              .get("dataSets", [{}])[0]
                              .get("series", {}))
                if serier:
                    observasjoner = list(serier.values())[0].get("observations", {})
                    if observasjoner:
                        siste_verdi = list(observasjoner.values())[0][0]
                        kurser[kode] = Decimal(str(siste_verdi))
                        log.info(f"Norges Bank: {kode}/NOK = {kurser[kode]:.4f}")
        except Exception as e:
            log.warning(f"Norges Bank API feilet for {kode}: {e}")

    return kurser


def _dagens_dato() -> str:
    from datetime import date
    return date.today().isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Hoved-cache-logikk
# ─────────────────────────────────────────────────────────────────────────────

def hent_kurs(fra_kode: str, til_kode: str,
              tvungen_oppdatering: bool = False) -> Optional[Decimal]:
    """
    Henter valutakurs med cache-logikk:

    1. Sjekk Redis (Cache Hit → returner umiddelbart)
    2. Cache Miss → kall eksternt API
    3. Lagre i Redis med TTL
    4. Lagre i PostgreSQL (atomisk transaksjon)

    Args:
        fra_kode:            Fra-valuta (ISO 4217)
        til_kode:            Til-valuta (ISO 4217)
        tvungen_oppdatering: Ignorer cache og hent fra API

    Returnerer kursen som Decimal, eller None ved feil.
    """
    valutapar = f"{fra_kode.upper()}:{til_kode.upper()}"

    # ── Steg 1: Sjekk Redis ────────────────────────────────────────────────
    if not tvungen_oppdatering:
        kurs, gjenvaerende_ttl = valuta_cache.hent(fra_kode, til_kode)

        if kurs is not None:
            log.info(f"CACHE HIT: {valutapar} = {kurs:.6f} "
                     f"(TTL: {gjenvaerende_ttl}s)")
            logg_cache_hendelse(
                valutapar, "CACHE_HIT",
                kurs=float(kurs),
                ttl=gjenvaerende_ttl
            )
            return kurs

    # ── Steg 2: Cache Miss — kall eksternt API ─────────────────────────────
    log.info(f"CACHE MISS: {valutapar} — kaller eksternt API")
    start = time.monotonic()
    kurs = hent_kurs_fra_api(fra_kode, til_kode)
    responstid_ms = int((time.monotonic() - start) * 1000)

    if kurs is None:
        log.error(f"API-kall feilet for {valutapar}")
        logg_cache_hendelse(valutapar, "API_FEIL")
        return None

    # ── Steg 3: Lagre i Redis med TTL ─────────────────────────────────────
    valuta_cache.sett(fra_kode, til_kode, kurs)
    log.info(f"CACHE SET: {valutapar} = {kurs:.6f} (TTL: {REDIS.ttl}s)")

    # ── Steg 4: Lagre i PostgreSQL (atomisk) ──────────────────────────────
    suksess = lagre_kurs_atomisk(fra_kode, til_kode, kurs, kilde='api_cache')
    if suksess:
        log.info(f"PostgreSQL oppdatert atomisk: {valutapar} = {kurs:.6f}")

    logg_cache_hendelse(
        valutapar, "CACHE_MISS",
        kurs=float(kurs),
        responstid_ms=responstid_ms
    )

    return kurs


# ─────────────────────────────────────────────────────────────────────────────
# Cron-jobb: periodisk oppdatering av alle kurser
# ─────────────────────────────────────────────────────────────────────────────

OVERVAKEDE_VALUTAPAR = [
    ("USD", "NOK"),
    ("EUR", "NOK"),
    ("GBP", "NOK"),
    ("SEK", "NOK"),
    ("DKK", "NOK"),
    ("CHF", "NOK"),
    ("JPY", "NOK"),
    ("NOK", "USD"),
    ("NOK", "EUR"),
]


def oppdater_alle_kurser():
    """
    Cron-jobb: oppdaterer alle overvåkede valutapar.
    Kjøres periodisk av APScheduler (konfigurerbart intervall).
    Bruker tvungen_oppdatering=True for å ignorere eksisterende cache.
    """
    log.info(f"=== Cron-jobb: Oppdaterer {len(OVERVAKEDE_VALUTAPAR)} valutapar ===")
    suksess = 0
    feil    = 0

    for fra, til in OVERVAKEDE_VALUTAPAR:
        kurs = hent_kurs(fra, til, tvungen_oppdatering=True)
        if kurs is not None:
            suksess += 1
        else:
            feil += 1

    log.info(f"=== Cron-jobb ferdig: {suksess} suksess, {feil} feil ===")
    return {"suksess": suksess, "feil": feil}


# Import her for å unngå sirkulær import
from config import REDIS
