"""
Demonstrasjon av tapt oppdatering (Lost Update) — Oppgave 9
============================================================

ÈN TILNÆRMING:
-------------------
For å demonstrere tapt oppdatering trenger vi implementere parallellitet:

  1. To separate tråder med SEPARATE databasetilkoblinger (psycopg2-tilkoblinger
     er ikke trådsikre og kan ikke deles).

  2. En threading.Barrier(2) som synkroniseringsmekanisme: begge tråder kaller
     barriere.wait() etter LES-steget, og ingen av dem fortsetter til SKRIV
     før begge har lest. Dette garanterer at begge leser SAMME verdi.

  3. En innlagt forsinkelse (time.sleep) mellom LES og SKRIV for å gjøre
     overlapp deterministisk og synlig i output.

RACE CONDITION-MØNSTERET (Les-Beregn-Skriv):
---------------------------------------------
Tid  Tråd A (Ane)                    Tråd B (Bjørn)
 1   LES: saldo = 248 500 kr
 2                                   LES: saldo = 248 500 kr   ← SAMME verdi!
 3   [barriere.wait() — begge klare]
 4   BEREGN: 248 500 + 3 000 = 251 500
 5                                   BEREGN: 248 500 + 1 500 = 250 000
 6   SKRIV: INSERT postering +3 000
 7                                   SKRIV: INSERT postering +1 500
 8   COMMIT → saldo = 251 500
 9                                   COMMIT → saldo = 251 500

I dette tilfellet er det INGEN tapt oppdatering fordi GnuCash-modellen
bruker INSERT-basert regnskap: saldoen beregnes alltid som SUM(posteringer),
ikke som en enkelt oppdaterbar kolonne. Begge INSERT-operasjoner er uavhengige
og kan ikke overskrive hverandre.

VIKTIG PEDAGOGISK POENG:
------------------------
Tapt oppdatering oppstår BARE ved mønsteret:
    LES verdi → BEREGN ny_verdi → UPDATE SET verdi = ny_verdi

I et INSERT-basert regnskapssystem (som GnuCash/NS 4102) er dette mønsteret
eliminert pga. designvalg. Demonstrasjonen viser HVORFOR INSERT er tryggere enn UPDATE.

For å demonstrere tapt oppdatering bruker vi en separat hjelpetabell
"KontoSaldo" med en oppdaterbar saldo-kolonne.

KJØRING:
--------
    python3 oppgave9.py

KRAV:
-----
    python -m venv data1500env # kjør python i egen "sandkasse"
    source data1500env/bin/activate
    pip install psycopg2-binary
    PostgreSQL kjørende med regnskap_test-database
"""

import threading
import time
import psycopg2

# ─────────────────────────────────────────────────────────────────────────────
# Konfigurasjon
# ─────────────────────────────────────────────────────────────────────────────

DSN = "dbname=regnskap user=admin password=admin123 host=postgres port=5432"
KONTONUMMER   = 1920
FORSINKELSE   = 0.3   # sekunder mellom LES og SKRIV
BELOP_ANE     = 300000   # 3 000 kr i øre
BELOP_BJORN   = 150000   # 1 500 kr i øre

# ─────────────────────────────────────────────────────────────────────────────
# Hjelpefunksjoner
# ─────────────────────────────────────────────────────────────────────────────

def ny_tilkobling():
    return psycopg2.connect(DSN)

def hent_konto_guid(kontonummer):
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute('SELECT guid FROM Kontoer WHERE kontonummer=%s', (kontonummer,))
        r = c.fetchone()
    conn.close()
    return r[0] if r else None

def hent_saldo_insert(konto_guid):
    """Saldo som SUM av posteringer — INSERT-basert modell."""
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute('SELECT COALESCE(SUM(belop_teller),0) FROM Posteringer WHERE konto_guid=%s',
                  (konto_guid,))
        v = c.fetchone()[0]
    conn.close()
    return v

def hent_kontekst():
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute('SELECT guid FROM Booker LIMIT 1')
        bok = c.fetchone()[0]
        c.execute('SELECT guid FROM Valutaer WHERE kode=%s', ('NOK',))
        nok = c.fetchone()[0]
        c.execute("""SELECT guid FROM Regnskapsperioder
                     WHERE EXTRACT(MONTH FROM fra_dato)=3
                       AND EXTRACT(YEAR  FROM fra_dato)=2026 LIMIT 1""")
        per = c.fetchone()[0]
    conn.close()
    return {"bok": bok, "nok": nok, "periode": per}

def gen_guid():
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute("SELECT REPLACE(gen_random_uuid()::TEXT, '-', '')")
        v = c.fetchone()[0]
    conn.close()
    return v

def rydd_test():
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute("""DELETE FROM Posteringer WHERE transaksjon_guid IN
                     (SELECT guid FROM Transaksjoner WHERE bilagsnummer LIKE 'DEMO-%')""")
        c.execute("DELETE FROM Transaksjoner WHERE bilagsnummer LIKE 'DEMO-%'")
        c.execute("DROP TABLE IF EXISTS demo_konto_saldo")
    conn.close()

# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO A — INSERT-basert modell (GnuCash/NS 4102)
# Viser at INSERT-mønsteret er immunt mot tapt oppdatering
# ─────────────────────────────────────────────────────────────────────────────

def insert_innbetaling(navn, belop, konto_guid, kontekst, barriere, resultater):
    """
    Les-beregn-skriv med INSERT. Begge tråder leser samme saldo,
    men skriver uavhengige INSERT-rader — ingen kan overskrive den andre.
    """
    conn = ny_tilkobling()
    try:
        conn.autocommit = False

        # STEG 1: LES saldo
        with conn.cursor() as c:
            c.execute('SELECT COALESCE(SUM(belop_teller),0) FROM Posteringer WHERE konto_guid=%s',
                      (konto_guid,))
            lest = c.fetchone()[0]
        print(f"  [{navn:6}] LES: saldo = {lest/100:,.0f} kr")

        # SYNKRONISERING: vent til begge har lest
        barriere.wait()
        time.sleep(FORSINKELSE)

        # STEG 2: SKRIV ny postering
        tx  = gen_guid()
        pos = gen_guid()
        with conn.cursor() as c:
            c.execute("""INSERT INTO Transaksjoner
                (guid,bok_guid,valuta_guid,bilagsnummer,bilagsdato,posteringsdato,beskrivelse,periode_guid)
                VALUES(%s,%s,%s,%s,CURRENT_DATE,CURRENT_DATE,%s,%s)""",
                (tx, kontekst["bok"], kontekst["nok"],
                 f'DEMO-INS-{navn[:3].upper()}', f'Innbetaling {navn}', kontekst["periode"]))
            c.execute("""INSERT INTO Posteringer
                (guid,transaksjon_guid,konto_guid,tekst,belop_teller,belop_nevner,antall_teller,antall_nevner)
                VALUES(%s,%s,%s,%s,%s,100,1,1)""",
                (pos, tx, konto_guid, f'Innbetaling {navn}', belop))
        conn.commit()

        ny = hent_saldo_insert(konto_guid)
        print(f"  [{navn:6}] COMMIT: ny saldo = {ny/100:,.0f} kr  (+{belop/100:,.0f} kr)")
        resultater[navn] = {"lest": lest, "belop": belop, "ny": ny}
    except Exception as e:
        conn.rollback()
        print(f"  [{navn:6}] FEIL: {e}")
        resultater[navn] = {"feil": str(e)}
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO B — UPDATE-basert modell (anti-mønster)
# Demonstrerer EKTE tapt oppdatering med en oppdaterbar saldo-kolonne
# ─────────────────────────────────────────────────────────────────────────────

def setup_update_tabell(startsaldo):
    """Oppretter en enkel tabell med oppdaterbar saldo-kolonne."""
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute("DROP TABLE IF EXISTS demo_konto_saldo")
        c.execute("""CREATE TABLE demo_konto_saldo (
                        id      SERIAL PRIMARY KEY,
                        navn    TEXT NOT NULL,
                        saldo   BIGINT NOT NULL  -- i øre
                     )""")
        c.execute("INSERT INTO demo_konto_saldo (navn, saldo) VALUES ('Bankinnskudd 1920', %s)",
                  (startsaldo,))
    conn.close()

def hent_saldo_update():
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute("SELECT saldo FROM demo_konto_saldo WHERE id=1")
        v = c.fetchone()[0]
    conn.close()
    return v

def usikker_update(navn, belop, barriere, resultater):
    """
    Klassisk les-beregn-skriv med UPDATE SET saldo = lest_saldo + belop.
    Uten låsing vil den siste COMMIT overskrive den første.
    """
    conn = ny_tilkobling()
    try:
        conn.autocommit = False
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

        # STEG 1: LES saldo
        with conn.cursor() as c:
            c.execute("SELECT saldo FROM demo_konto_saldo WHERE id=1")
            lest = c.fetchone()[0]
        print(f"  [{navn:6}] LES: saldo = {lest/100:,.0f} kr")

        # SYNKRONISERING: vent til begge har lest SAMME verdi
        barriere.wait()
        time.sleep(FORSINKELSE)

        # STEG 2: BEREGN og SKRIV — overskriver det den andre tråden nettopp lagret!
        ny_saldo = lest + belop
        with conn.cursor() as c:
            c.execute("UPDATE demo_konto_saldo SET saldo=%s WHERE id=1", (ny_saldo,))
        conn.commit()

        faktisk = hent_saldo_update()
        print(f"  [{navn:6}] COMMIT: satte saldo = {ny_saldo/100:,.0f} kr  "
              f"(lest {lest/100:,.0f} + {belop/100:,.0f})  |  faktisk nå: {faktisk/100:,.0f} kr")
        resultater[navn] = {"lest": lest, "belop": belop, "skrevet": ny_saldo}
    except Exception as e:
        conn.rollback()
        print(f"  [{navn:6}] FEIL: {e}")
        resultater[navn] = {"feil": str(e)}
    finally:
        conn.close()

def sikker_update_for_update(navn, belop, barriere, resultater):
    """
    Les-beregn-skriv med SELECT FOR UPDATE.
    Den andre tråden blokkeres inntil den første committer.
    """
    conn = ny_tilkobling()
    try:
        conn.autocommit = False

        # STEG 1: LES med lås
        with conn.cursor() as c:
            c.execute("SELECT saldo FROM demo_konto_saldo WHERE id=1 FOR UPDATE")
            lest = c.fetchone()[0]
        print(f"  [{navn:6}] LES+LÅS: saldo = {lest/100:,.0f} kr")

        # Ingen Barrier her — låsen er synkroniseringsmekanismen
        time.sleep(FORSINKELSE)

        ny_saldo = lest + belop
        with conn.cursor() as c:
            c.execute("UPDATE demo_konto_saldo SET saldo=%s WHERE id=1", (ny_saldo,))
        conn.commit()

        faktisk = hent_saldo_update()
        print(f"  [{navn:6}] COMMIT+FRIGJØR LÅS: saldo = {faktisk/100:,.0f} kr  "
              f"(lest {lest/100:,.0f} + {belop/100:,.0f})")
        resultater[navn] = {"lest": lest, "belop": belop, "skrevet": ny_saldo}
    except Exception as e:
        conn.rollback()
        print(f"  [{navn:6}] FEIL: {e}")
        resultater[navn] = {"feil": str(e)}
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────────
# Kjørehjelper
# ─────────────────────────────────────────────────────────────────────────────

def kjor_to_tradder(funksjon_a, args_a, funksjon_b, args_b):
    t1 = threading.Thread(target=funksjon_a, args=args_a)
    t2 = threading.Thread(target=funksjon_b, args=args_b)
    t1.start(); t2.start()
    t1.join();  t2.join()

# ─────────────────────────────────────────────────────────────────────────────
# Hovedprogram (skal IKKE implementeres av studenten(-e))
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "█"*62)
    print("  DEMONSTRASJON: TAPT OPPDATERING (LOST UPDATE)")
    print("  Oppgave 9 — Samtidige transaksjoner i PostgreSQL")
    print("█"*62)
    print(f"  Forsinkelse LES→SKRIV: {FORSINKELSE}s  |  "
          f"Ane: +{BELOP_ANE/100:,.0f} kr  |  Bjørn: +{BELOP_BJORN/100:,.0f} kr\n")

    rydd_test()
    kontekst   = hent_kontekst()
    konto_guid = hent_konto_guid(KONTONUMMER)
    STARTSALDO = 24850000   # 248 500 kr i øre

    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO A1: INSERT-basert — usikker (viser INGEN tapt oppdatering)
    # ══════════════════════════════════════════════════════════════════════════
    print("═"*62)
    print("  SCENARIO A: INSERT-basert modell (GnuCash/NS 4102)")
    print("  Begge tråder leser samme saldo, men skriver uavhengige INSERT-rader.")
    print("  Resultat: INGEN tapt oppdatering — INSERT er immunt by design.")
    print("─"*62)
    saldo_for = hent_saldo_insert(konto_guid)
    forventet = saldo_for + BELOP_ANE + BELOP_BJORN
    print(f"  Saldo FØR: {saldo_for/100:,.0f} kr  |  Forventet: {forventet/100:,.0f} kr")
    print("─"*62)

    res_a = {}
    bar_a = threading.Barrier(2)
    kjor_to_tradder(
        insert_innbetaling, ("Ane",   BELOP_ANE,   konto_guid, kontekst, bar_a, res_a),
        insert_innbetaling, ("Bjørn", BELOP_BJORN, konto_guid, kontekst, bar_a, res_a)
    )
    saldo_etter_a = hent_saldo_insert(konto_guid)
    avvik_a = saldo_etter_a - forventet
    print("─"*62)
    print(f"  Saldo ETTER: {saldo_etter_a/100:,.0f} kr  |  Forventet: {forventet/100:,.0f} kr  |  "
          + ("⚠️  TAPT!" if avvik_a else "✓ Korrekt"))

    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO B1: UPDATE-basert — USIKKER (demonstrerer EKTE tapt oppdatering)
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "═"*62)
    print("  SCENARIO B1: UPDATE-basert — USIKKER (anti-mønster)")
    print("  Begge tråder leser SAMME saldo, beregner ny verdi og")
    print("  overskriver hverandre med UPDATE. Den siste vinner.")
    print("─"*62)
    setup_update_tabell(STARTSALDO)
    forventet_b = STARTSALDO + BELOP_ANE + BELOP_BJORN
    print(f"  Saldo FØR: {STARTSALDO/100:,.0f} kr  |  Forventet: {forventet_b/100:,.0f} kr")
    print("─"*62)

    res_b1 = {}
    bar_b1 = threading.Barrier(2)
    kjor_to_tradder(
        usikker_update, ("Ane",   BELOP_ANE,   bar_b1, res_b1),
        usikker_update, ("Bjørn", BELOP_BJORN, bar_b1, res_b1)
    )
    saldo_etter_b1 = hent_saldo_update()
    avvik_b1 = saldo_etter_b1 - forventet_b
    print("─"*62)
    print(f"  Saldo ETTER: {saldo_etter_b1/100:,.0f} kr  |  Forventet: {forventet_b/100:,.0f} kr  |  "
          + (f"⚠️  TAPT OPPDATERING: {abs(avvik_b1)/100:,.0f} kr gikk tapt!" if avvik_b1 else "✓ Korrekt"))

    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO B2: UPDATE-basert — SIKKER med SELECT FOR UPDATE
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "═"*62)
    print("  SCENARIO B2: UPDATE-basert — SIKKER (SELECT FOR UPDATE)")
    print("  Den første tråden låser raden. Den andre venter til låsen frigis.")
    print("  Ingen Barrier nødvendig — låsen er synkroniseringsmekanismen.")
    print("─"*62)
    setup_update_tabell(STARTSALDO)
    print(f"  Saldo FØR: {STARTSALDO/100:,.0f} kr  |  Forventet: {forventet_b/100:,.0f} kr")
    print("─"*62)

    res_b2 = {}
    # Ingen Barrier — trådene starter samtidig, men låsen serialiserer dem
    kjor_to_tradder(
        sikker_update_for_update, ("Ane",   BELOP_ANE,   None, res_b2),
        sikker_update_for_update, ("Bjørn", BELOP_BJORN, None, res_b2)
    )
    saldo_etter_b2 = hent_saldo_update()
    avvik_b2 = saldo_etter_b2 - forventet_b
    print("─"*62)
    print(f"  Saldo ETTER: {saldo_etter_b2/100:,.0f} kr  |  Forventet: {forventet_b/100:,.0f} kr  |  "
          + (f"⚠️  TAPT: {abs(avvik_b2)/100:,.0f} kr" if avvik_b2 else "✓ Korrekt"))

    # ══════════════════════════════════════════════════════════════════════════
    # SAMMENDRAG
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "═"*62)
    print("  SAMMENDRAG")
    print("─"*62)
    print(f"  {'Scenario':<48} {'Avvik':>10}")
    print(f"  {'─'*48} {'─'*10}")
    for tittel, avvik in [
        ("A:  INSERT-basert (GnuCash/NS 4102) — ingen låsing", avvik_a),
        ("B1: UPDATE-basert — USIKKER (les-beregn-skriv)",     avvik_b1),
        ("B2: UPDATE-basert — SIKKER  (SELECT FOR UPDATE)",    avvik_b2),
    ]:
        status = f"{avvik/100:+,.0f} kr" if avvik else "0 kr ✓"
        print(f"  {tittel:<48} {status:>10}")
    print("═"*62)
    print()

    rydd_test()