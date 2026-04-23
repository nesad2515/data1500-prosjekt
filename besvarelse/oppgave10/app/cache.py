"""
cache.py — Redis-cache for valutakurser
Oppgave 10A: NS 4102 Regnskapssystem

Implementerer cache-logikken beskrevet i oppgaven:
  1. Konstruer nøkkel: price:{FRA}:{TIL}
  2. GET fra Redis
     - Cache Hit:  returner verdi umiddelbart
     - Cache Miss: kall API, SET med TTL, oppdater PostgreSQL
"""

import logging
import time
from decimal import Decimal
from typing import Optional

import redis

from config import REDIS

log = logging.getLogger(__name__)


class ValutaCache:
    """
    Redis-basert cache for valutakurser.

    Nøkkelformat:  price:{FRA_KODE}:{TIL_KODE}
    Verdiformat:   Desimaltall som streng, f.eks. "10.523456"
    TTL:           Konfigurerbar (standard 3600 sekunder = 1 time)
    """

    def __init__(self):
        self._klient = redis.Redis(
            host=REDIS.host,
            port=REDIS.port,
            decode_responses=True,   # Returner str, ikke bytes
        )
        self.ttl = REDIS.ttl
        log.info(f"Redis-tilkobling: {REDIS.host}:{REDIS.port} (TTL={self.ttl}s)")

    def _noekkel(self, fra: str, til: str) -> str:
        """Konstruerer en standardisert Redis-nøkkel for et valutapar."""
        return f"price:{fra.upper()}:{til.upper()}"

    def hent(self, fra: str, til: str) -> tuple[Optional[Decimal], Optional[int]]:
        """
        Henter en kurs fra cachen.

        Returnerer:
            (kurs, gjenvaerende_ttl) ved Cache Hit
            (None, None)             ved Cache Miss
        """
        noekkel = self._noekkel(fra, til)
        verdi   = self._klient.get(noekkel)

        if verdi is not None:
            gjenvaerende_ttl = self._klient.ttl(noekkel)
            kurs = Decimal(verdi)
            log.debug(f"CACHE HIT: {noekkel} = {kurs} (TTL: {gjenvaerende_ttl}s)")
            return kurs, gjenvaerende_ttl
        else:
            log.debug(f"CACHE MISS: {noekkel}")
            return None, None

    def sett(self, fra: str, til: str, kurs: Decimal,
             ttl: Optional[int] = None) -> bool:
        """
        Lagrer en kurs i cachen med TTL.

        Args:
            fra:  Fra-valuta (ISO 4217)
            til:  Til-valuta (ISO 4217)
            kurs: Valutakursen som Decimal
            ttl:  Time-To-Live i sekunder (bruker standard hvis None)

        Returnerer True ved suksess.
        """
        noekkel  = self._noekkel(fra, til)
        ttl_verdi = ttl if ttl is not None else self.ttl

        try:
            # SET nøkkel verdi EX ttl_sekunder
            self._klient.set(noekkel, str(kurs), ex=ttl_verdi)
            log.debug(f"CACHE SET: {noekkel} = {kurs} (TTL: {ttl_verdi}s)")
            return True
        except redis.RedisError as e:
            log.error(f"Redis SET feilet for {noekkel}: {e}")
            return False

    def slett(self, fra: str, til: str) -> bool:
        """Sletter en nøkkel fra cachen (f.eks. for manuell invalidering)."""
        noekkel = self._noekkel(fra, til)
        antall  = self._klient.delete(noekkel)
        log.info(f"Cache invalidert: {noekkel} ({antall} nøkler slettet)")
        return antall > 0

    def slett_alle_kurser(self) -> int:
        """Sletter alle price:-nøkler (brukes ved testing)."""
        noekler = self._klient.keys("price:*")
        if noekler:
            antall = self._klient.delete(*noekler)
            log.info(f"Slettet {antall} kursnøkler fra cache")
            return antall
        return 0

    def hent_alle_noekler(self) -> list[str]:
        """Returnerer alle price:-nøkler i cachen."""
        return sorted(self._klient.keys("price:*"))

    def ping(self) -> bool:
        """Sjekker at Redis er tilgjengelig."""
        try:
            return self._klient.ping()
        except redis.RedisError:
            return False

    def info(self) -> dict:
        """Henter Redis-serverinformasjon."""
        try:
            info = self._klient.info()
            return {
                "versjon":          info.get("redis_version"),
                "brukt_minne_mb":   round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "antall_noekler":   self._klient.dbsize(),
                "cache_noekler":    len(self.hent_alle_noekler()),
                "oppetid_sekunder": info.get("uptime_in_seconds"),
                "hits":             info.get("keyspace_hits", 0),
                "misses":           info.get("keyspace_misses", 0),
            }
        except redis.RedisError as e:
            log.error(f"Kunne ikke hente Redis-info: {e}")
            return {}


# Globalt cache-objekt (singleton)
valuta_cache = ValutaCache()
