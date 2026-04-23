# Oppgave 11: Staging av Finansielle Dokumenter med MongoDB

**Dere skal ikke implementere denne oppgaven selv.**

Koden er gitt i mappen `oppgave11`.

**Mål:** Eksperimentere med en dokumentdatabase som et mellomlager for komplekse, semi-strukturerte API-responser.

**Teknologi:** **MongoDB** (Dokumentdatabase)

## Introduksjon

Løsningen demonstrerer en klassisk ETL-pipeline (Extract, Transform, Load) der MongoDB brukes som et **staging-område** for semi-strukturerte JSON-data fra et eksternt API, før dataene transformeres og lastes inn i en strukturert PostgreSQL-database.


## ETL-pipeline

Tjenesten skal implementere følgende ETL-logikk (Extract, Transform, Load):

1.  **Extract:** Hent detaljert kurshistorikk for et verdipapir fra **Alpha Vantage**.
2.  **Load (rådata):** Lagre hele JSON-responsen som ett dokument i MongoDB-collectionen `raw_financial_data`. Hvert dokument skal inneholde feltene `ticker_symbol`, `fetch_timestamp` og `api_source` i tillegg til de rå API-dataene.
3.  **Transform & Load (SQL):** Trekk ut de relevante feltene (siste kurs og dato) og oppdater `Kurser`-tabellen i SQL-databasen **innenfor en transaksjon**.

## Om implementasjon

**Krav til implementasjon:**
- Hent og lagre data for minst 3 ulike verdipapirer i MongoDB. **dette er implementert**

## Arkitektur og Komponenter

Løsningen er bygget som en mikrotjenestearkitektur med tre containere, definert i `docker-compose.yml`.

| Tjeneste | Image | Rolle |
|---|---|---|
| `db` | `postgres:15-alpine` | **Relasjonell database (produksjon):** Lagrer de endelige, strukturerte kursdataene i NS 4102-skjemaet. Inneholder tabellene `Valutaer`, `Verdipapirer`, `Kurser` og `ETL_Logg`. |
| `mongo` | `mongo:7` | **Dokumentdatabase (staging):** Lagrer rå, ustrukturerte JSON-responser fra Alpha Vantage API i en `raw_financial_data`-collection. Hvert dokument inneholder metadata som `etl_status` ("STAGED"/"LASTET"). |
| `app` | Python 3.11 (bygget lokalt) | **Applikasjonsserver:** Kjører ETL-pipelinen, tilbyr et REST API (FastAPI) for interaksjon, og har en innebygd cron-jobb (APScheduler) for periodisk datahenting. |

## Instruksjoner for utføreslse av demo

API-nøkkel kan hentes fra https://www.alphavantage.co/documentation/ (usikker på hva er grensen for antall tilkoblinger).

API-nøkkel skal settes inn på linje 109 i filen `oppgave11/app/etl_pipeline.py`.

Uten API-nøkkel blir en syntetisk fallback-mekanismen aktivert.
```bash
cd oppgave11

# 2. Start alle tjenester (PostgreSQL, MongoDB, App)
docker compose up -d

# 3. Kjør demonstrasjonsskriptet
docker compose exec app python demo.py

# 4. Utforsk REST API-et
open http://localhost:8001/docs
``` 

## Dokumenteres i rapporten
- Vis hvordan SQL-databasen oppdateres korrekt. **dette kan du vise i rapporten**
- Diskuter i rapporten: Hva er fordelen med å beholde rådataene i MongoDB selv etter at SQL-databasen er oppdatert? (Hint: tenk på feilsøking, historikk og muligheten for å re-prosessere data.) **dette skal besvares i rapporten***
