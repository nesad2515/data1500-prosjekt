"""
database.py — PostgreSQL-tilkobling og NS 4102-skjemaoperasjoner
Oppgave 10: NS 4102 Regnskapssystem
"""

import logging
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import psycopg2
import psycopg2.extras

from config import DB

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Tilkoblingsadministrasjon
# ─────────────────────────────────────────────────────────────────────────────

@contextmanager
def db_tilkobling():
    """
    Kontekstbehandler for databasetilkoblinger.
    Garanterer COMMIT ved suksess og ROLLBACK ved feil — atomisk.
    """
    conn = psycopg2.connect(DB.dsn)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
        log.debug("Transaksjon COMMIT")
    except Exception as e:
        conn.rollback()
        log.error(f"Transaksjon ROLLBACK: {e}")
        raise
    finally:
        conn.close()


def ny_guid() -> str:
    """Genererer en ny UUID som 32-tegns heksadesimal streng (CHAR(32))."""
    return uuid.uuid4().hex


# ─────────────────────────────────────────────────────────────────────────────
# Skjemainitialisering
# ─────────────────────────────────────────────────────────────────────────────

SKJEMA_SQL = """
-- ============================================================
-- NS 4102 Regnskapssystem — Forenklet skjema for Oppgave 10A
-- Fokus: Valutaer og Valutakurser (prices-tabellen)
-- ============================================================

-- Valutaer (commodities i GnuCash-terminologi)
CREATE TABLE IF NOT EXISTS "Valutaer" (
    guid        CHAR(32)     PRIMARY KEY,
    kode        VARCHAR(10)  NOT NULL UNIQUE,   -- ISO 4217 (NOK, USD, EUR)
    navn        VARCHAR(100) NOT NULL,
    fraksjon    INTEGER      NOT NULL DEFAULT 100,
    er_aktiv    BOOLEAN      NOT NULL DEFAULT TRUE,
    opprettet   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Valutakurser (prices-tabellen i GnuCash)
-- Lagrer historiske kurser mellom to valutaer
CREATE TABLE IF NOT EXISTS "Valutakurser" (
    guid            CHAR(32)     PRIMARY KEY,
    fra_valuta_guid CHAR(32)     NOT NULL REFERENCES "Valutaer"(guid),
    til_valuta_guid CHAR(32)     NOT NULL REFERENCES "Valutaer"(guid),
    kursdato        DATE         NOT NULL,
    kurs_teller     BIGINT       NOT NULL,   -- Brøkrepresentasjon
    kurs_nevner     BIGINT       NOT NULL DEFAULT 1000000,
    kurstype        VARCHAR(20)  NOT NULL DEFAULT 'last'
                    CHECK (kurstype IN ('last', 'bid', 'ask', 'nav', 'transaction')),
    kilde           VARCHAR(50)  NOT NULL DEFAULT 'manuell',
    hentet_tid      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    -- En kurs per valutapar per dato og type
    UNIQUE (fra_valuta_guid, til_valuta_guid, kursdato, kurstype)
);

-- Indekser for ytelse
CREATE INDEX IF NOT EXISTS idx_valutakurser_dato
    ON "Valutakurser" (kursdato DESC);
CREATE INDEX IF NOT EXISTS idx_valutakurser_par
    ON "Valutakurser" (fra_valuta_guid, til_valuta_guid);

-- Kurslogg — sporer alle cache-hendelser (pedagogisk formål)
CREATE TABLE IF NOT EXISTS "Kurslogg" (
    id              SERIAL       PRIMARY KEY,
    valutapar       VARCHAR(20)  NOT NULL,   -- f.eks. 'USD:NOK'
    hendelse        VARCHAR(20)  NOT NULL    -- 'CACHE_HIT', 'CACHE_MISS', 'API_FEIL'
                    CHECK (hendelse IN ('CACHE_HIT', 'CACHE_MISS', 'API_FEIL', 'DB_OPPDATERT')),
    kurs            NUMERIC(18,6),           -- NULL ved feil
    kilde           VARCHAR(100),           -- ← la til denne linjen 2026-04-03
    ttl_sekunder    INTEGER,                 -- Gjenværende TTL ved cache-hit
    responstid_ms   INTEGER,                 -- API-responstid (NULL ved cache-hit)
    tidspunkt       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
"""


def initialiser_skjema():
    """Oppretter tabeller hvis de ikke finnes, og legger til grunnvalutaer."""
    with db_tilkobling() as conn:
        with conn.cursor() as cur:
            cur.execute(SKJEMA_SQL)

            # Legg til grunnvalutaer (INSERT OR IGNORE-mønster)
            valutaer = [
                (ny_guid(), 'NOK', 'Norske kroner',    100),
                (ny_guid(), 'USD', 'Amerikanske dollar', 100),
                (ny_guid(), 'EUR', 'Euro',              100),
                (ny_guid(), 'GBP', 'Britiske pund',     100),
                (ny_guid(), 'SEK', 'Svenske kroner',    100),
                (ny_guid(), 'DKK', 'Danske kroner',     100),
                (ny_guid(), 'CHF', 'Sveitsiske franc',  100),
                (ny_guid(), 'JPY', 'Japanske yen',      1),
            ]
            for guid, kode, navn, fraksjon in valutaer:
                cur.execute("""
                    INSERT INTO "Valutaer" (guid, kode, navn, fraksjon)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (kode) DO NOTHING
                """, (guid, kode, navn, fraksjon))

    log.info("Skjema initialisert og grunnvalutaer lagt til")


# ─────────────────────────────────────────────────────────────────────────────
# Kursoperasjoner
# ─────────────────────────────────────────────────────────────────────────────

def hent_valuta_guid(kode: str) -> Optional[str]:
    """Henter GUID for en valuta basert på ISO 4217-kode."""
    with db_tilkobling() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT guid FROM "Valutaer" WHERE kode = %s',
                (kode.upper(),)
            )
            rad = cur.fetchone()
            return rad[0] if rad else None


def lagre_kurs_atomisk(fra_kode: str, til_kode: str,
                        kurs: Decimal, kilde: str = 'api') -> bool:
    """
    Lagrer en valutakurs i PostgreSQL innenfor en atomisk transaksjon.
    Bruker INSERT ... ON CONFLICT DO UPDATE for idempotens.

    Returnerer True ved suksess, False ved feil.
    """
    try:
        with db_tilkobling() as conn:
            with conn.cursor() as cur:
                # Hent GUIDs for begge valutaer
                cur.execute(
                    'SELECT guid FROM "Valutaer" WHERE kode = %s',
                    (fra_kode.upper(),)
                )
                fra_rad = cur.fetchone()

                cur.execute(
                    'SELECT guid FROM "Valutaer" WHERE kode = %s',
                    (til_kode.upper(),)
                )
                til_rad = cur.fetchone()

                if not fra_rad or not til_rad:
                    log.warning(f"Ukjent valutakode: {fra_kode} eller {til_kode}")
                    return False

                fra_guid = fra_rad[0]
                til_guid = til_rad[0]

                # Brøkrepresentasjon: kurs * 1_000_000 / 1_000_000
                nevner = 1_000_000
                teller = int(kurs * nevner)

                # Atomisk upsert — INSERT eller UPDATE hvis dato+type allerede finnes
                cur.execute("""
                    INSERT INTO "Valutakurser"
                        (guid, fra_valuta_guid, til_valuta_guid,
                         kursdato, kurs_teller, kurs_nevner, kurstype, kilde)
                    VALUES (%s, %s, %s, %s, %s, %s, 'last', %s)
                    ON CONFLICT (fra_valuta_guid, til_valuta_guid, kursdato, kurstype)
                    DO UPDATE SET
                        kurs_teller  = EXCLUDED.kurs_teller,
                        kilde        = EXCLUDED.kilde,
                        hentet_tid   = NOW()
                """, (ny_guid(), fra_guid, til_guid,
                      date.today(), teller, nevner, kilde))

                # Logg hendelsen
                cur.execute("""
                    INSERT INTO "Kurslogg" (valutapar, hendelse, kurs, kilde)
                    VALUES (%s, 'DB_OPPDATERT', %s, %s)
                """, (f"{fra_kode}:{til_kode}", float(kurs), kilde))

        log.info(f"Kurs lagret atomisk: {fra_kode}/{til_kode} = {kurs:.6f}")
        return True

    except Exception as e:
        log.error(f"Feil ved lagring av kurs {fra_kode}/{til_kode}: {e}")
        return False


def logg_cache_hendelse(valutapar: str, hendelse: str,
                         kurs: Optional[float] = None,
                         ttl: Optional[int] = None,
                         responstid_ms: Optional[int] = None):
    """Registrerer en cache-hendelse i Kurslogg-tabellen."""
    try:
        with db_tilkobling() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO "Kurslogg"
                        (valutapar, hendelse, kurs, ttl_sekunder, responstid_ms)
                    VALUES (%s, %s, %s, %s, %s)
                """, (valutapar, hendelse, kurs, ttl, responstid_ms))
    except Exception as e:
        log.warning(f"Kunne ikke logge cache-hendelse: {e}")


def hent_kurshistorikk(fra_kode: str, til_kode: str,
                        antall_dager: int = 30) -> list[dict]:
    """Henter kurshistorikk for et valutapar fra PostgreSQL."""
    with db_tilkobling() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    vk.kursdato,
                    vk.kurs_teller::numeric / vk.kurs_nevner AS kurs,
                    vk.kilde,
                    vk.hentet_tid
                FROM "Valutakurser" vk
                JOIN "Valutaer" fra ON fra.guid = vk.fra_valuta_guid
                JOIN "Valutaer" til ON til.guid = vk.til_valuta_guid
                WHERE fra.kode = %s
                  AND til.kode = %s
                  AND vk.kursdato >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY vk.kursdato DESC
            """, (fra_kode.upper(), til_kode.upper(), antall_dager))
            return [dict(r) for r in cur.fetchall()]


def hent_cache_statistikk() -> dict:
    """Henter statistikk over cache-ytelse fra Kurslogg."""
    with db_tilkobling() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    hendelse,
                    COUNT(*)                        AS antall,
                    AVG(responstid_ms)              AS snitt_responstid_ms,
                    MIN(tidspunkt)                  AS foerste,
                    MAX(tidspunkt)                  AS siste
                FROM "Kurslogg"
                GROUP BY hendelse
                ORDER BY hendelse
            """)
            rader = cur.fetchall()

            # Beregn cache hit rate
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE hendelse = 'CACHE_HIT')  AS hits,
                    COUNT(*) FILTER (WHERE hendelse = 'CACHE_MISS') AS misses
                FROM "Kurslogg"
                WHERE hendelse IN ('CACHE_HIT', 'CACHE_MISS')
            """)
            hm = cur.fetchone()
            total = (hm['hits'] or 0) + (hm['misses'] or 0)
            hit_rate = (hm['hits'] / total * 100) if total > 0 else 0

            return {
                "detaljer":   [dict(r) for r in rader],
                "hit_rate":   round(hit_rate, 1),
                "totalt":     total,
                "cache_hits": hm['hits'] or 0,
                "cache_miss": hm['misses'] or 0,
            }
