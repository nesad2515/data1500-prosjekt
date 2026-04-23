"""
demo.py — Standalone demonstrasjonsskript for Oppgave 11
Kjøres direkte: python demo.py

Demonstrerer hele ETL-pipelinen:
  1. Initialiserer PostgreSQL og MongoDB
  2. Kjører ETL for 3 verdipapirer (AAPL, MSFT, EQNR.OL)
  3. Viser MongoDB staging-dokumenter
  4. Viser PostgreSQL-kurser
  5. Demonstrerer re-prosessering fra MongoDB
  6. Viser statistikk
"""
import json
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

from database import (
    initialiser_skjema,
    hent_kurshistorikk,
    hent_etl_statistikk
)
from staging import (
    initialiser_collections,
    hent_dokument_for_ticker,
    hent_staging_statistikk,
    hent_ubehandlede_dokumenter,
    mongo_db
)
from etl_pipeline import kjor_etl_for_ticker, OVERVAKEDE_VERDIPAPIRER


def separator(tittel: str = "", bredde: int = 65):
    if tittel:
        print(f"\n{'─' * 5} {tittel} {'─' * (bredde - len(tittel) - 7)}")
    else:
        print("─" * bredde)


def kjor_demonstrasjon():
    print("=" * 65)
    print("  OPPGAVE: MongoDB Staging av Finansielle Dokumenter")
    print("  NS 4102 Regnskapssystem")
    print("=" * 65)

    # ── Steg 1: Initialiser ──────────────────────────────────
    separator("Steg 1: Initialisering")
    print("[1a] Initialiserer PostgreSQL-skjema...")
    initialiser_skjema()
    print("     PostgreSQL ✓")

    print("[1b] Initialiserer MongoDB collections...")
    initialiser_collections()
    print("     MongoDB ✓")

    # Tøm eksisterende testdata for ren demonstrasjon
    db = mongo_db()
    slettet = db["raw_financial_data"].delete_many({}).deleted_count
    if slettet > 0:
        print(f"     Slettet {slettet} eksisterende dokumenter fra MongoDB ✓")

    # ── Steg 2: ETL for hvert verdipapir ─────────────────────
    separator("Steg 2: ETL-pipeline for 3 verdipapirer")
    print(f"  {'Ticker':<12} {'Status':<10} {'Kurser':<10} {'MongoDB ID':<30}")
    print(f"  {'──────':<12} {'──────':<10} {'──────':<10} {'──────────':<30}")

    etl_resultater = []
    for vp in OVERVAKEDE_VERDIPAPIRER:
        ticker = vp["ticker"]
        print(f"  {ticker:<12}", end="", flush=True)

        resultat = kjor_etl_for_ticker(ticker)
        etl_resultater.append(resultat)

        if resultat["suksess"]:
            print(
                f" {'OK':<10} {resultat['antall_lastet']:<10} "
                f"{resultat['mongo_id'][:28]:<30}"
            )
        else:
            print(f" {'FEIL':<10} {0:<10} {resultat['feilmelding'][:28]:<30}")

        # Respekter Alpha Vantage rate limit
        if vp != OVERVAKEDE_VERDIPAPIRER[-1]:
            print(f"  (Venter 13s for rate limit...)", end="\r")
            time.sleep(13)
            print(" " * 40, end="\r")

    # ── Steg 3: Vis MongoDB-dokumenter ───────────────────────
    separator("Steg 3: MongoDB staging-dokumenter")
    for vp in OVERVAKEDE_VERDIPAPIRER:
        ticker = vp["ticker"]
        dokumenter = hent_dokument_for_ticker(ticker, 1)
        if dokumenter:
            dok = dokumenter[0]
            print(f"\n  Ticker:        {dok['ticker_symbol']}")
            print(f"  MongoDB _id:   {dok['_id']}")
            print(f"  Hentet:        {dok['fetch_timestamp']}")
            print(f"  API-kilde:     {dok['api_source']}")
            print(f"  ETL-status:    {dok['etl_status']}")
            print(f"  Antall kurser: {dok.get('antall_kurser', 'N/A')}")

    # ── Steg 4: Vis PostgreSQL-kurser ─────────────────────────
    separator("Steg 4: PostgreSQL-kurser (siste 5 handelsdager)")
    for vp in OVERVAKEDE_VERDIPAPIRER:
        ticker = vp["ticker"]
        kurser = hent_kurshistorikk(ticker, 5)
        if kurser:
            print(f"\n  {ticker}:")
            print(f"  {'Dato':<12} {'Slutt':<10} {'Åpning':<10} {'Høy':<10} {'Lav':<10} {'Volum':<15}")
            print(f"  {'────':<12} {'─────':<10} {'──────':<10} {'───':<10} {'───':<10} {'─────':<15}")
            for k in kurser:
                print(
                    f"  {str(k['kursdato']):<12} "
                    f"{str(k['sluttkurs']):<10} "
                    f"{str(k.get('apning','N/A')):<10} "
                    f"{str(k.get('hoy','N/A')):<10} "
                    f"{str(k.get('lav','N/A')):<10} "
                    f"{str(k.get('volum','N/A')):<15}"
                )
        else:
            print(f"\n  {ticker}: Ingen kurser funnet")

    # ── Steg 5: Demonstrer re-prosessering ───────────────────
    separator("Steg 5: Re-prosessering fra MongoDB")
    print("  Scenario: Anta at PostgreSQL-lasting feilet for AAPL.")
    print("  Vi kan re-prosessere fra MongoDB uten nytt API-kall.\n")

    # Simuler ved å sette etl_status tilbake til STAGED for ett dokument
    aapl_dok = hent_dokument_for_ticker("AAPL", 1)
    if aapl_dok:
        from bson import ObjectId
        db["raw_financial_data"].update_one(
            {"_id": aapl_dok[0]["_id"]},
            {"$set": {"etl_status": "STAGED"}}
        )
        ubehandlede = hent_ubehandlede_dokumenter()
        print(f"  Ubehandlede dokumenter i MongoDB: {len(ubehandlede)}")
        for dok in ubehandlede:
            print(f"    - {dok['ticker_symbol']} ({dok['fetch_timestamp'][:19]})")
        print("\n  (I produksjon: kjør re-prosessering fra /staging/ubehandlet)")
        # Gjenopprett status
        db["raw_financial_data"].update_one(
            {"_id": aapl_dok[0]["_id"]},
            {"$set": {"etl_status": "LASTET"}}
        )

    # ── Steg 6: Statistikk ────────────────────────────────────
    separator("Steg 6: Statistikk")
    print("\n  MongoDB staging-statistikk:")
    print(f"  {'Ticker':<12} {'Totalt':<10} {'Staged':<10} {'Lastet':<10}")
    print(f"  {'──────':<12} {'──────':<10} {'──────':<10} {'──────':<10}")
    for s in hent_staging_statistikk():
        ticker = s.get("_id") or s.get("ticker", "?")
        print(
            f"  {ticker:<12} "
            f"{s['totalt']:<10} "
            f"{s['staged']:<10} "
            f"{s['lastet']:<10}"
        )

    print("\n  PostgreSQL ETL-logg-statistikk:")
    print(f"  {'Ticker':<12} {'OK':<8} {'Feil':<8} {'Totalt lastet':<15} {'Siste kjøring'}")
    print(f"  {'──────':<12} {'──':<8} {'────':<8} {'─────────────':<15} {'─────────────'}")
    for s in hent_etl_statistikk():
        siste = str(s.get("siste_kjoring", ""))[:19] if s.get("siste_kjoring") else "N/A"
        print(
            f"  {s['ticker']:<12} "
            f"{s['vellykkede'] or 0:<8} "
            f"{s['feilede'] or 0:<8} "
            f"{s['totalt_lastet'] or 0:<15} "
            f"{siste}"
        )

    print("\n" + "=" * 65)
    print("  Demonstrasjon fullført!")
    print("=" * 65)


if __name__ == "__main__":
    kjor_demonstrasjon()
