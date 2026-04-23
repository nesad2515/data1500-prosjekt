"""
demo.py — Demonstrasjonsskript for Oppgave 10A
NS 4102 Regnskapssystem — Valutakurs-Cache med Redis

Simulerer 10 påfølgende kall for samme valutapar og logger
om hvert kall resulterte i Cache Hit eller Cache Miss.

Kjøres inne i app-containeren:
    docker compose exec app python demo.py

Eller direkte (krever at Redis og PostgreSQL kjører):
    python demo.py
"""

import logging
import time
from decimal import Decimal

# Sett opp logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

from cache import valuta_cache
from database import initialiser_skjema, hent_cache_statistikk
from kursservice import hent_kurs


def kjor_demonstrasjon():
    """
    Kjører den fullstendige demonstrasjonen som beskrevet i oppgaven:
    10 påfølgende kall for USD/NOK og EUR/NOK.
    """
    print("\n" + "="*65)
    print("  OPPGAVE 10A: Valutakurs-Cache med Redis")
    print("  NS 4102 Regnskapssystem")
    print("="*65)

    # Initialiser skjema
    print("\n[1] Initialiserer PostgreSQL-skjema...")
    initialiser_skjema()
    print("    Skjema klart ✓")

    # Tøm cachen for å starte med blanke ark
    print("\n[2] Tømmer Redis-cache for å starte rent...")
    antall_slettet = valuta_cache.slett_alle_kurser()
    print(f"    Slettet {antall_slettet} nøkler ✓")

    # ── Demonstrasjon 1: USD/NOK ─────────────────────────────────────────────
    print("\n" + "-"*65)
    print("  DEMONSTRASJON 1: 10 kall for USD/NOK")
    print("-"*65)
    print(f"  {'Kall':>4}  {'Status':^12}  {'Kurs':>12}  {'TTL':>8}  {'Tid':>8}")
    print(f"  {'----':>4}  {'------':^12}  {'----':>12}  {'---':>8}  {'---':>8}")

    for i in range(1, 11):
        start = time.monotonic()
        kurs = hent_kurs("USD", "NOK")
        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Sjekk cache-status
        cached, ttl = valuta_cache.hent("USD", "NOK")
        status = "CACHE HIT" if i > 1 else "CACHE MISS"

        kurs_str = f"{float(kurs):.4f} NOK" if kurs else "FEIL"
        ttl_str  = f"{ttl}s" if ttl else "—"
        tid_str  = f"{elapsed_ms}ms"

        print(f"  {i:>4}  {status:^12}  {kurs_str:>12}  {ttl_str:>8}  {tid_str:>8}")

        # Liten pause mellom kall
        time.sleep(0.1)

    # ── Demonstrasjon 2: EUR/NOK ─────────────────────────────────────────────
    print("\n" + "-"*65)
    print("  DEMONSTRASJON 2: 5 kall for EUR/NOK (nytt valutapar)")
    print("-"*65)
    print(f"  {'Kall':>4}  {'Status':^12}  {'Kurs':>12}  {'TTL':>8}")
    print(f"  {'----':>4}  {'------':^12}  {'----':>12}  {'---':>8}")

    for i in range(1, 6):
        kurs = hent_kurs("EUR", "NOK")
        cached, ttl = valuta_cache.hent("EUR", "NOK")
        status = "CACHE HIT" if i > 1 else "CACHE MISS"
        kurs_str = f"{float(kurs):.4f} NOK" if kurs else "FEIL"
        ttl_str  = f"{ttl}s" if ttl else "—"
        print(f"  {i:>4}  {status:^12}  {kurs_str:>12}  {ttl_str:>8}")
        time.sleep(0.1)

    # ── Demonstrasjon 3: Tving API-kall (cache-invalidering) ─────────────────
    print("\n" + "-"*65)
    print("  DEMONSTRASJON 3: Tving API-kall (tvungen_oppdatering=True)")
    print("-"*65)
    kurs_foer = hent_kurs("USD", "NOK")
    print(f"  Kurs FØR tvungen oppdatering: {float(kurs_foer):.6f}")

    kurs_etter = hent_kurs("USD", "NOK", tvungen_oppdatering=True)
    print(f"  Kurs ETTER tvungen oppdatering: {float(kurs_etter):.6f}")
    print(f"  (Ny TTL satt til {valuta_cache.ttl}s)")

    # ── Redis-info ────────────────────────────────────────────────────────────
    print("\n" + "-"*65)
    print("  REDIS-STATUS")
    print("-"*65)
    info = valuta_cache.info()
    print(f"  Versjon:          {info.get('versjon')}")
    print(f"  Brukt minne:      {info.get('brukt_minne_mb')} MB")
    print(f"  Antall nøkler:    {info.get('antall_noekler')}")
    print(f"  Cache-nøkler:     {info.get('cache_noekler')}")

    # ── Cache-statistikk fra PostgreSQL ───────────────────────────────────────
    print("\n" + "-"*65)
    print("  CACHE-STATISTIKK (fra PostgreSQL Kurslogg)")
    print("-"*65)
    stat = hent_cache_statistikk()
    print(f"  Totale kall:      {stat['totalt']}")
    print(f"  Cache Hits:       {stat['cache_hits']}")
    print(f"  Cache Misses:     {stat['cache_miss']}")
    print(f"  Hit-rate:         {stat['hit_rate']}%")

    print("\n" + "="*65)
    print("  Demonstrasjon fullført!")
    print("="*65 + "\n")


if __name__ == "__main__":
    kjor_demonstrasjon()
