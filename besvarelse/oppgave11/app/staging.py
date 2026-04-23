"""
staging.py — MongoDB staging-database for rådata fra finansielle API-er
Oppgave: MongoDB Staging

Collections:
  raw_financial_data  — Rå JSON-responser fra Alpha Vantage (OHLCV time series)
  etl_logg            — Historikk over ETL-kjøringer (speilet fra PostgreSQL)
  verdipapirer        — Metadata om overvåkede verdipapirer
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError

from config import MONGO

log = logging.getLogger(__name__)

# ── Tilkobling ───────────────────────────────────────────────
_klient: Optional[MongoClient] = None


def mongo_klient() -> MongoClient:
    """Returnerer en singleton MongoClient-instans."""
    global _klient
    if _klient is None:
        _klient = MongoClient(MONGO.uri, serverSelectionTimeoutMS=5000)
        log.info(f"MongoDB-tilkobling: {MONGO.uri[:40]}...")
    return _klient


def mongo_db():
    """Returnerer finansdata-databasen."""
    return mongo_klient()[MONGO.db]


def initialiser_collections():
    """
    Oppretter collections og indekser i MongoDB.
    MongoDB oppretter collections automatisk ved første innsetting,
    men vi setter opp indekser eksplisitt for ytelse.
    """
    db = mongo_db()

    # raw_financial_data: unik indeks på ticker + hente-tidspunkt
    db["raw_financial_data"].create_index(
        [("ticker_symbol", DESCENDING), ("fetch_timestamp", DESCENDING)],
        name="idx_ticker_timestamp"
    )
    # Indeks for status-feltet (for ETL-spørringer)
    db["raw_financial_data"].create_index(
        [("etl_status", DESCENDING)],
        name="idx_etl_status"
    )

    # etl_logg: indeks på ticker og tidspunkt
    db["etl_logg"].create_index(
        [("ticker", DESCENDING), ("tidspunkt", DESCENDING)],
        name="idx_etl_ticker_tid"
    )

    log.info("MongoDB collections og indekser initialisert")


def stage_radata(ticker: str, api_kilde: str, radata: dict) -> str:
    """
    Lagrer hele JSON-responsen fra et finansielt API som ett dokument
    i raw_financial_data-collectionen.

    Dokumentstrukturen følger oppgavekravet:
      - ticker_symbol    : Verdipapir-ticker (f.eks. "AAPL")
      - fetch_timestamp  : Tidspunkt for henting (ISO 8601 UTC)
      - api_source       : Kilde-API (f.eks. "alpha_vantage")
      - etl_status       : "STAGED" → "LASTET" etter PostgreSQL-oppdatering
      - raw_data         : Den komplette, umodifiserte API-responsen

    Returnerer MongoDB-dokumentets _id som streng.
    """
    db = mongo_db()
    dokument = {
        "ticker_symbol":   ticker,
        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_source":      api_kilde,
        "etl_status":      "STAGED",   # Endres til "LASTET" etter PostgreSQL-oppdatering
        "raw_data":        radata,     # Hele JSON-responsen, umodifisert
        "metadata": {
            "schema_versjon": "1.0",
            "oppgave":        "10B"
        }
    }
    resultat = db["raw_financial_data"].insert_one(dokument)
    mongo_id = str(resultat.inserted_id)
    log.info(f"MongoDB STAGE: {ticker} lagret som dokument {mongo_id}")
    return mongo_id


def marker_som_lastet(mongo_id: str, antall_kurser: int):
    """
    Oppdaterer etl_status til 'LASTET' etter vellykket PostgreSQL-lasting.
    Dette er den viktige koblingen mellom staging og produksjon.
    """
    from bson import ObjectId
    db = mongo_db()
    db["raw_financial_data"].update_one(
        {"_id": ObjectId(mongo_id)},
        {"$set": {
            "etl_status":       "LASTET",
            "lastet_tidspunkt": datetime.now(timezone.utc).isoformat(),
            "antall_kurser":    antall_kurser
        }}
    )
    log.info(f"MongoDB: Dokument {mongo_id} markert som LASTET ({antall_kurser} kurser)")


def hent_ubehandlede_dokumenter(ticker: str = None) -> list:
    """
    Henter alle dokumenter med etl_status = 'STAGED' (ikke lastet til PostgreSQL).
    Brukes for re-prosessering ved feil.
    """
    db = mongo_db()
    filter_dict = {"etl_status": "STAGED"}
    if ticker:
        filter_dict["ticker_symbol"] = ticker
    return list(db["raw_financial_data"].find(
        filter_dict,
        {"raw_data": 0}  # Ekskluder rådata for oversiktens skyld
    ))


def hent_staging_statistikk() -> dict:
    """Henter aggregert statistikk fra MongoDB."""
    db = mongo_db()
    pipeline = [
        {"$group": {
            "_id":           "$ticker_symbol",
            "totalt":        {"$sum": 1},
            "staged":        {"$sum": {"$cond": [{"$eq": ["$etl_status", "STAGED"]}, 1, 0]}},
            "lastet":        {"$sum": {"$cond": [{"$eq": ["$etl_status", "LASTET"]}, 1, 0]}},
            "siste_henting": {"$max": "$fetch_timestamp"}
        }},
        {"$sort": {"_id": 1}}
    ]
    return list(db["raw_financial_data"].aggregate(pipeline))


def hent_dokument_for_ticker(ticker: str, antall: int = 5) -> list:
    """Henter de siste N dokumentene for et verdipapir (uten rådata)."""
    db = mongo_db()
    return list(db["raw_financial_data"].find(
        {"ticker_symbol": ticker},
        {"raw_data": 0}
    ).sort("fetch_timestamp", DESCENDING).limit(antall))
