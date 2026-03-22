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
 1   LES: saldo = 24 850 000 kr
 2                                   LES: saldo = 24 850 000 kr   ← SAMME verdi!
 3   [barriere.wait() — begge klare]
 4   BEREGN: 10 000 + 3 000 = 13 000
 5                                   BEREGN: 10 000 + 1 500 = 11 500
 6   SKRIV: INSERT postering +3 000
 7                                   SKRIV: INSERT postering +1 500
 8   COMMIT → saldo = 13 000
 9                                   COMMIT → saldo = 14 500

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

DSN = "dbname=regnskap user=admin password=admin123 host=localhost port=5492"
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
        c.execute('SELECT guid FROM "Kontoer" WHERE kontonummer=%s', (kontonummer,))
        r = c.fetchone()
    conn.close()
    return r[0] if r else None

def hent_saldo_insert(konto_guid):
    """Saldo som SUM av posteringer — INSERT-basert modell."""
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute('SELECT COALESCE(SUM(belop_teller),0) FROM "Posteringer" WHERE konto_guid=%s',
                  (konto_guid,))
        v = c.fetchone()[0]
    conn.close()
    return v

def hent_kontekst():
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute('SELECT guid FROM "Bøker" LIMIT 1')
        bok = c.fetchone()[0]
        c.execute('SELECT guid FROM "Valutaer" WHERE kode=%s', ('NOK',))
        nok = c.fetchone()[0]
        c.execute("""SELECT guid FROM "Regnskapsperioder"
                     WHERE EXTRACT(MONTH FROM fra_dato)=3
                       AND EXTRACT(YEAR  FROM fra_dato)=2026 LIMIT 1""")
        per = c.fetchone()[0]
    conn.close()
    return {"bok": bok, "nok": nok, "periode": per}

def gen_guid():
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute("SELECT generate_guid()")
        v = c.fetchone()[0]
    conn.close()
    return v

def rydd_test():
    conn = ny_tilkobling(); conn.autocommit = True
    with conn.cursor() as c:
        c.execute("""DELETE FROM "Posteringer" WHERE transaksjon_guid IN
                     (SELECT guid FROM "Transaksjoner" WHERE bilagsnummer LIKE 'DEMO-%')""")
        c.execute("DELETE FROM \"Transaksjoner\" WHERE bilagsnummer LIKE 'DEMO-%'")
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
            c.execute('SELECT COALESCE(SUM(belop_teller),0) FROM "Posteringer" WHERE konto_guid=%s',
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
            c.execute("""INSERT INTO "Transaksjoner"
                (guid,bok_guid,valuta_guid,bilagsnummer,bilagsdato,posteringsdato,beskrivelse,periode_guid)
                VALUES(%s,%s,%s,%s,CURRENT_DATE,CURRENT_DATE,%s,%s)""",
                (tx, kontekst["bok"], kontekst["nok"],
                 f'DEMO-INS-{navn[:3].upper()}', f'Innbetaling {navn}', kontekst["periode"]))
            c.execute("""INSERT INTO "Posteringer"
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
# Hovedprogram (skal implementeres av studenten(-e))
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "█"*62)
    print("  DEMONSTRASJON: TAPT OPPDATERING (LOST UPDATE)")
    print("  Oppgave 9 — Samtidige transaksjoner i PostgreSQL")
    print("█"*62)
    print(f"  Forsinkelse LES→SKRIV: {FORSINKELSE}s  |  "
          f"Ane: +{BELOP_ANE/100:,.0f} kr  |  Bjørn: +{BELOP_BJORN/100:,.0f} kr\n")

# Skriv din kode her