# Oppgave 10: Sanntids Valutakurs-Cache med Redis

**Mål:** OBS! Dette er endret fra den opprinnelige oppgaveteksten.

Eksperimentere med en effektiv cache-mekanisme for å redusere antall kall mot et eksternt API. Oppnå en forståelse av hvordan NoSQL-systemer og relasjonsdatabasesystemer kan brukes sammen for å implementere en stabil tjeneste. 

**Teknologi:** **Redis** (Key-Value Store)

Tjenesten har følgende cache-logikk:

1.  En unik nøkkel for valutaparet, f.eks. `price:USD:NOK`.
2.  Nøkkelen finnes i Redis (sjekk med `GET price:USD:NOK`).
    -   **Cache Hit:** Returner den lagrede verdien umiddelbart uten å kalle API-et.
    -   **Cache Miss:** Kaller det eksterne API-et (**Norges Bank API**), lagrer resultatet i Redis med en TTL på 1 time (`SET price:USD:NOK 9.65 EX 3600`), og oppdaterer `prices`-tabellen i SQL-databasen **innenfor en transaksjon**.

**TTL** - `time to live` eller `hop limit` er en mekanisme som begrenser *livstid* til data i en datamaskin eller i et nettverk.

**Diskuter i rapporten:**
- Utfør skriptet `demo.py` som simulerer 10 påfølgende kall for samme valutapar og logger om hvert kall resulterte i Cache Hit eller Cache Miss. Forklar resultatet!
- Finn ut hva som lagres i PostgreSQL (vis gjerne med spørringer) og forklar!
- Hva er konsekvensen for datakonsistens dersom Redis-cachen inneholder en foreldet kurs og en bruker registrerer en transaksjon basert på den? Hvordan kan dette håndteres?

## Arkitektur

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                  │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  PostgreSQL  │◄───│  app         │───►│  Redis    │  │
│  │  (port 5432) │    │  (port 8000) │    │ (port 6379│  │
│  │              │    │              │    │           │  │
│  │  NS 4102     │    │  FastAPI     │    │  Cache    │  │
│  │  Skjema      │    │  APScheduler │    │  TTL=1h   │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
│                             │                           │
│                             ▼                           │
│                    ┌──────────────────┐                 │
│                    │  Eksternt API    │                 │
│                    │  ExchangeRate-API│                 │
│                    │  Norges Bank API │                 │
│                    └──────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

## Cache-logikk

```
hent_kurs(fra, til)
    │
    ├─► Redis GET price:{FRA}:{TIL}
    │       │
    │       ├─► Cache HIT  → returner umiddelbart (0-5ms)
    │       │
    │       └─► Cache MISS
    │               │
    │               ├─► Kall eksternt API (~200-500ms)
    │               ├─► Redis SET price:{FRA}:{TIL} {kurs} EX 3600
    │               └─► PostgreSQL INSERT (atomisk transaksjon)
    │
    └─► returner kurs
```

## Hurtigstart

```bash
# Start stacken
cd oppgave10
docker-compose up -d

# Sjekk at alle tjenester er oppe
docker-compose ps

# Kjør demonstrasjonsskriptet
docker-compose exec app python demo.py

# Åpne API-dokumentasjon
open http://localhost:8000/docs
```

## API-endepunkter

| Metode | URL | Beskrivelse |
|---|---|---|
| `GET` | `/` | Helsestatus |
| `GET` | `/kurs/{fra}/{til}` | Hent kurs (med cache) |
| `GET` | `/kurs/{fra}/{til}/frisk` | Hent kurs (tving API) |
| `GET` | `/kurser` | Liste alle cachede kurser |
| `POST` | `/kurs/oppdater` | Kjør cron-jobb manuelt |
| `GET` | `/statistikk/cache` | Cache-ytelsesstatistikk |
| `GET` | `/statistikk/redis` | Redis-serverinfo |
| `GET` | `/historikk/{fra}/{til}` | Kurshistorikk fra PostgreSQL |
| `DELETE` | `/cache` | Tøm cachen (testing) |

## Nyttige kommandoer

```bash
# Se logger fra applikasjonsserveren
docker-compose logs -f app

# Koble til Redis direkte
docker-compose exec redis redis-cli

# Se alle cachede kurser i Redis
docker-compose exec redis redis-cli KEYS "price:*"

# Se TTL for en spesifikk nøkkel
docker-compose exec redis redis-cli TTL "price:USD:NOK"

# Koble til PostgreSQL direkte
docker-compose exec db psql -U regnskap_user -d regnskap

# Se kurslogg
docker-compose exec db psql -U regnskap_user -d regnskap \
  -c 'SELECT * FROM "Kurslogg" ORDER BY tidspunkt DESC LIMIT 20;'

# Stopp stacken
docker compose down

# Stopp og slett alle data
docker compose down -v
```
