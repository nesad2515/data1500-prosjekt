"""
database.py — PostgreSQL-tilkobling og NS 4102-skjema
Oppgave 11: MongoDB Staging

Tabeller som opprettes:
  - Valutaer        : ISO 4217-valutaer
  - Verdipapirer    : Aksjer, fond og andre finansielle instrumenter
  - Kurser          : Historiske kurser (OHLCV + sluttkurs)
  - ETL_Logg        : Historikk over ETL-kjøringer fra MongoDB til PostgreSQL
"""
import logging
import hashlib
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import psycopg2
import psycopg2.extras

from config import PG

log = logging.getLogger(__name__)


# ── Hjelpefunksjon ──────────────────────────────────────────
def ny_guid(kilde: str = "") -> str:
    """Genererer en deterministisk GUID basert på innhold, eller tilfeldig."""
    import uuid
    if kilde:
        return hashlib.md5(kilde.encode()).hexdigest()
    return uuid.uuid4().hex


# ── Tilkoblingsbehandler ─────────────────────────────────────
@contextmanager
def db_tilkobling():
    """
    Kontekstbehandler for atomiske PostgreSQL-transaksjoner.
    Kjører COMMIT ved suksess, ROLLBACK ved unntak.
    """
    conn = psycopg2.connect(PG.dsn)
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


# ── Skjemadefinisjon ─────────────────────────────────────────
SKJEMA_SQL = """
-- ============================================================
-- NS 4102 Delskjema for Oppgave 10B
-- Fokus: Verdipapirer og kurser (GnuCash: commodities + prices)
-- ============================================================

-- Valutaer (ISO 4217)
CREATE TABLE IF NOT EXISTS "Valutaer" (
    guid        CHAR(32)     PRIMARY KEY,
    kode        VARCHAR(10)  NOT NULL UNIQUE,
    navn        VARCHAR(100) NOT NULL,
    fraksjon    INTEGER      NOT NULL DEFAULT 100,
    er_aktiv    BOOLEAN      NOT NULL DEFAULT TRUE,
    opprettet   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Verdipapirer (aksjer, fond, ETF, råvarer)
-- Tilsvarer GnuCash commodities med namespace != CURRENCY
CREATE TABLE IF NOT EXISTS "Verdipapirer" (
    guid            CHAR(32)     PRIMARY KEY,
    ticker          VARCHAR(20)  NOT NULL UNIQUE,   -- f.eks. AAPL, EQNR.OL
    navn            VARCHAR(200) NOT NULL,
    bors            VARCHAR(50),                    -- f.eks. NASDAQ, OSE
    isin            VARCHAR(12),                    -- Internasjonal ID
    valuta_guid     CHAR(32)     NOT NULL REFERENCES "Valutaer"(guid),
    instrument_type VARCHAR(30)  NOT NULL DEFAULT 'AKSJE'
                    CHECK (instrument_type IN ('AKSJE', 'FOND', 'ETF', 'RAAVARE', 'OBLIGASJON')),
    er_aktiv        BOOLEAN      NOT NULL DEFAULT TRUE,
    opprettet       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Kurser — historiske priser (OHLCV + sluttkurs)
-- Tilsvarer GnuCash prices-tabellen, utvidet med OHLCV
CREATE TABLE IF NOT EXISTS "Kurser" (
    guid                CHAR(32)     PRIMARY KEY,
    verdipapir_guid     CHAR(32)     NOT NULL REFERENCES "Verdipapirer"(guid),
    kursdato            DATE         NOT NULL,
    -- Brøkrepresentasjon for nøyaktighet (nevner = 10000 → 4 desimaler)
    apning_teller       BIGINT,                     -- Open
    apning_nevner       BIGINT       NOT NULL DEFAULT 10000,
    hoy_teller          BIGINT,                     -- High
    hoy_nevner          BIGINT       NOT NULL DEFAULT 10000,
    lav_teller          BIGINT,                     -- Low
    lav_nevner          BIGINT       NOT NULL DEFAULT 10000,
    slutt_teller        BIGINT       NOT NULL,       -- Close (obligatorisk)
    slutt_nevner        BIGINT       NOT NULL DEFAULT 10000,
    volum               BIGINT,                     -- Antall handlede enheter
    kilde               VARCHAR(50)  NOT NULL DEFAULT 'alpha_vantage',
    mongo_dokument_id   VARCHAR(50),                -- Referanse til rådata i MongoDB
    hentet_tid          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    -- Én kurs per verdipapir per dato
    UNIQUE (verdipapir_guid, kursdato),
    -- Nevnere kan ikke være null eller null
    CHECK (apning_nevner  > 0),
    CHECK (hoy_nevner     > 0),
    CHECK (lav_nevner     > 0),
    CHECK (slutt_nevner   > 0)
);

-- Indekser for ytelse
CREATE INDEX IF NOT EXISTS idx_kurser_dato
    ON "Kurser" (kursdato DESC);
CREATE INDEX IF NOT EXISTS idx_kurser_verdipapir_dato
    ON "Kurser" (verdipapir_guid, kursdato DESC);

-- ETL-logg — sporer alle ETL-kjøringer fra MongoDB til PostgreSQL
CREATE TABLE IF NOT EXISTS "ETL_Logg" (
    id                  SERIAL       PRIMARY KEY,
    ticker              VARCHAR(20)  NOT NULL,
    mongo_dokument_id   VARCHAR(50),                -- _id fra MongoDB
    hendelse            VARCHAR(30)  NOT NULL
                        CHECK (hendelse IN (
                            'EXTRACT_OK', 'EXTRACT_FEIL',
                            'STAGE_OK',   'STAGE_FEIL',
                            'LOAD_OK',    'LOAD_FEIL',
                            'ALLEREDE_LASTET'
                        )),
    antall_rader        INTEGER      DEFAULT 0,     -- Antall kurser lastet
    feilmelding         TEXT,                       -- NULL ved suksess
    tidspunkt           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
"""


def initialiser_skjema():
    """Oppretter tabeller og legger til grunndata."""
    with db_tilkobling() as conn:
        with conn.cursor() as cur:
            cur.execute(SKJEMA_SQL)

            # Grunnvalutaer
            valutaer = [
                (ny_guid("NOK"), "NOK", "Norske kroner",    100),
                (ny_guid("USD"), "USD", "US Dollar",         100),
                (ny_guid("EUR"), "EUR", "Euro",              100),
                (ny_guid("GBP"), "GBP", "Britiske pund",    100),
                (ny_guid("SEK"), "SEK", "Svenske kroner",   100),
            ]
            cur.executemany("""
                INSERT INTO "Valutaer" (guid, kode, navn, fraksjon)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (kode) DO NOTHING
            """, valutaer)

            # Grunnverdipapirer (3 stk som oppgaven krever)
            usd_guid = ny_guid("USD")
            nok_guid = ny_guid("NOK")
            verdipapirer = [
                (ny_guid("AAPL"),    "AAPL",    "Apple Inc.",           "NASDAQ", "US0378331005", usd_guid, "AKSJE"),
                (ny_guid("MSFT"),    "MSFT",    "Microsoft Corporation","NASDAQ", "US5949181045", usd_guid, "AKSJE"),
                (ny_guid("EQNR.OL"),"EQNR.OL", "Equinor ASA",          "OSE",    "NO0010096985", nok_guid, "AKSJE"),
            ]
            cur.executemany("""
                INSERT INTO "Verdipapirer"
                    (guid, ticker, navn, bors, isin, valuta_guid, instrument_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker) DO NOTHING
            """, verdipapirer)

    log.info("PostgreSQL-skjema initialisert med grunndata")


def logg_etl_hendelse(ticker: str, hendelse: str, mongo_id: str = None,
                       antall: int = 0, feilmelding: str = None):
    """Registrerer en ETL-hendelse i ETL_Logg-tabellen."""
    with db_tilkobling() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "ETL_Logg"
                    (ticker, mongo_dokument_id, hendelse, antall_rader, feilmelding)
                VALUES (%s, %s, %s, %s, %s)
            """, (ticker, mongo_id, hendelse, antall, feilmelding))


def last_kurser_til_postgres(ticker: str, kurser: list, mongo_id: str) -> int:
    """
    Laster transformerte OHLCV-kurser fra MongoDB-staging til PostgreSQL.
    Kjøres innenfor én atomisk transaksjon.
    Returnerer antall rader lastet.
    """
    with db_tilkobling() as conn:
        with conn.cursor() as cur:
            # Hent verdipapir-GUID
            cur.execute(
                'SELECT guid FROM "Verdipapirer" WHERE ticker = %s', (ticker,)
            )
            rad = cur.fetchone()
            if not rad:
                raise ValueError(f"Verdipapir ikke funnet: {ticker}")
            verdipapir_guid = rad[0]

            antall_lastet = 0
            for kurs in kurser:
                # Konverter desimaltall til brøk (nevner = 10000)
                nevner = 10000

                def til_teller(verdi):
                    if verdi is None:
                        return None
                    return int(Decimal(str(verdi)) * nevner)

                cur.execute("""
                    INSERT INTO "Kurser" (
                        guid, verdipapir_guid, kursdato,
                        apning_teller, apning_nevner,
                        hoy_teller,   hoy_nevner,
                        lav_teller,   lav_nevner,
                        slutt_teller, slutt_nevner,
                        volum, kilde, mongo_dokument_id
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    ON CONFLICT (verdipapir_guid, kursdato)
                    DO UPDATE SET
                        slutt_teller      = EXCLUDED.slutt_teller,
                        apning_teller     = EXCLUDED.apning_teller,
                        hoy_teller        = EXCLUDED.hoy_teller,
                        lav_teller        = EXCLUDED.lav_teller,
                        volum             = EXCLUDED.volum,
                        mongo_dokument_id = EXCLUDED.mongo_dokument_id,
                        hentet_tid        = NOW()
                """, (
                    ny_guid(f"{ticker}:{kurs['dato']}"),
                    verdipapir_guid,
                    kurs["dato"],
                    til_teller(kurs.get("apning")),  nevner,
                    til_teller(kurs.get("hoy")),     nevner,
                    til_teller(kurs.get("lav")),     nevner,
                    til_teller(kurs["slutt"]),        nevner,
                    kurs.get("volum"),
                    "alpha_vantage",
                    mongo_id
                ))
                antall_lastet += 1

    log.info(f"PostgreSQL: {antall_lastet} kurser lastet for {ticker}")
    return antall_lastet


def hent_kurshistorikk(ticker: str, antall_dager: int = 10) -> list:
    """Henter de siste N kursene for et verdipapir fra PostgreSQL."""
    with db_tilkobling() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    k.kursdato,
                    ROUND(k.slutt_teller::numeric / k.slutt_nevner, 4) AS sluttkurs,
                    ROUND(k.apning_teller::numeric / NULLIF(k.apning_nevner,0), 4) AS apning,
                    ROUND(k.hoy_teller::numeric   / NULLIF(k.hoy_nevner,0),   4) AS hoy,
                    ROUND(k.lav_teller::numeric   / NULLIF(k.lav_nevner,0),   4) AS lav,
                    k.volum,
                    k.mongo_dokument_id
                FROM "Kurser" k
                JOIN "Verdipapirer" v ON v.guid = k.verdipapir_guid
                WHERE v.ticker = %s
                ORDER BY k.kursdato DESC
                LIMIT %s
            """, (ticker, antall_dager))
            return [dict(r) for r in cur.fetchall()]


def hent_etl_statistikk() -> dict:
    """Henter aggregert ETL-statistikk fra ETL_Logg."""
    with db_tilkobling() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    ticker,
                    COUNT(*) FILTER (WHERE hendelse = 'LOAD_OK')    AS vellykkede,
                    COUNT(*) FILTER (WHERE hendelse = 'LOAD_FEIL')  AS feilede,
                    COUNT(*) FILTER (WHERE hendelse = 'EXTRACT_FEIL') AS api_feil,
                    SUM(antall_rader) FILTER (WHERE hendelse = 'LOAD_OK') AS totalt_lastet,
                    MAX(tidspunkt)                                   AS siste_kjoring
                FROM "ETL_Logg"
                GROUP BY ticker
                ORDER BY ticker
            """)
            return [dict(r) for r in cur.fetchall()]
