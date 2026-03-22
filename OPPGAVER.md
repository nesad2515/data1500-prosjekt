# Kravspesifikasjon: Prosjektoppgave i Databaser
## Emne: Dobbelt Bokholderi — Datamodellering, SQL, Transaksjoner og NoSQL

**Emne:** Databaser  
**Nivå:** Bachelor, 1. år
**Arbeidsform:** Valgfritt: gruppe på 3 studenter, par (2 studenter) eller individuelt  
**Omfang:** 4–6 uker 
**Innlevering** I Github Classroom (oppgaven inngår i arbeidskravet)
**Innleveringsfrist** søndag 3. Mai 2026

---

## 1. Innledning og faglig kontekst

Dobbelt bokholderi er et av de mest grunnleggende prinsippene i moderne regnskap, og ble første gang formelt beskrevet av den italienske fransiskanermunken **Luca Pacioli** i 1494 i verket *Summa de Arithmetica, Geometria, Proportioni et Proportionalita*.[^1] Metoden er i dag lovpålagt for de fleste regnskapspliktige virksomheter i Norge gjennom bokføringsloven, og danner grunnlaget for alle moderne regnskapssystemer.

Kjernen i dobbelt bokholderi er at enhver finansiell transaksjon registreres på **minst to kontoer** med like store beløp — ett beløp til debet og ett til kredit. Summen av alle debetposteringer skal alltid være lik summen av alle kreditposteringer, slik at regnskapet alltid er i balanse. Dette gjør systemet selvkontrollerende og gir en pålitelig revisjonsspor.

Denne prosjektoppgaven tar et utgangspunkt i datamodellen til **GnuCash**, et åpen kildekode-regnskapsprogram som støtter PostgreSQL, MySQL og SQLite3. GnuCash implementerer dobbelt bokholderi for personlig regnskap. For å illustrere et bedriftsregnskap blir NS 4102[^6] introdusert og brukt som utgangspunkt i denne oppgaven.

---

## 2. Læringsmål

Etter gjennomført prosjekt skal studenten kunne:

- designe og implementere en databasestruktur basert på en gitt kravspesifikasjon
- skrive SQL-spørringer med JOIN, aggregatfunksjoner (SUM, COUNT, AVG), GROUP BY, vindusfuksjoner, og CTE for å generere regnskapsrapporter
- håndtere NULL-verdier og forstå treverdislogikk i SQL
- populere en database med realistiske testdata og verifisere dataintegritet
- forklare transaksjoner og demonstrere hvordan de implementeres i PostgreSQL
- gjøre rede for hva nosql-databaser er og hvor dette benyttes ved hjelp av praktiske eksempler (cache-mekanisme og dokumentdatabase som mellomlager)
---

## 3. Bakgrunn: Dobbelt Bokholderi

### 3.1 Prinsippet

Dobbelt bokholderi bygger på en enkel, men kraftfull idé: enhver transaksjon har to sider. Når en bedrift selger en tjeneste, oppstår det både en inntekt og en fordring. Når den betaler lønn, reduseres bankbeholdningen og en lønnskostnad oppstår. Regnskapsligningen som alltid må holde, er:

> **Eiendeler = Gjeld + Egenkapital**

Utvidet til å inkludere resultatkontoer:

> **Eiendeler − Gjeld = Egenkapital + (Inntekter − Kostnader)**

### 3.2 De fem grunnleggende kontotypene

Alle kontoer i et dobbelt bokholderisystem tilhører én av fem grunnleggende typer. Tabellen nedenfor oppsummerer disse:

| Kontotype | Norsk betegnelse | Beskrivelse | Saldo øker ved | Saldo reduseres ved |
|---|---|---|---|---|
| **Assets** | Eiendeler | Det bedriften eier (penger, utstyr, kundefordringer) | Debet | Kredit |
| **Liabilities** | Gjeld | Det bedriften skylder (lån, leverandørgjeld) | Kredit | Debet |
| **Equity** | Egenkapital | Eiernes andel av bedriften | Kredit | Debet |
| **Income** | Inntekter | Inntekter fra salg av varer og tjenester | Kredit | Debet |
| **Expenses** | Kostnader | Utgifter til drift av virksomheten | Debet | Kredit |

Det er også vanlig å bruke flere typer kontoer, som man kan klassifisere som deltyper av de fem grunnleggende typene, f.eks.  `CASH`, `BANK`, `STOCK`, `CREDIT`, `ACCOUNTS_RECEIVABLE`, `ACCOUNTS_PAYABLE`, `EQUITY`, osv.

### 3.3 T-konto og splits

Den tradisjonelle måten å visualisere dobbelt bokholderi på er gjennom **T-kontoer**, der venstre side er debet og høyre side er kredit. I GnuCash sin datamodell er dette implementert gjennom tabellen `splits`: hver rad i `splits` representerer én side av en transaksjon og er knyttet til én bestemt konto. En transaksjon med to splits tilsvarer en klassisk to-sidig postering; en transaksjon med tre eller flere splits er en sammensatt postering. Det norske navnet for `splits` er `posteringer`.

---

## 4. Brukerscenarioer (NS 4102)

Følgende scenarioer illustrerer hvordan en liten konsulentbedrift, **DATA1500 Konsult AS**, tar i bruk dobbelt bokholderi fra oppstart, med kontoer fra Norsk Standard Kontoplan (NS 4102). Alle kontonumre er i henhold til NS 4102, og alle beløp er i norske kroner (NOK) med mindre annet er angitt. Scenarioene er utformet slik at de dekker alle åtte kontoklassene og de viktigste funksjonene i den norske datamodellen.

**Sentrale begrep**

En `balansekonto` er en konto som viser bedriftens finansielle stilling på et gitt tidspunkt. Saldoen på disse kontoene overføres fra ett regnskapsår til det neste - de "nullstilles" ikke ved årsslutt. Balansekontoer deles inn i to hovedgrupper, - `Eiendeler` (aktiva, dvs. bankinnskudd, varelager, maskiner, kundefordringer) og `Gjeld og egenkapital` (passiva). Kontoklasser 1-2 i NS 4102. 

En `resultatkonto` registrerer bedriftens inntekter og kostnader i løpet av en periode (vanligvis et regnskapsår). Ved periodeslutt nullstilles disse kontoene, og nettoresultatet (overskudd eller underskudd) overføres til egenkapitalen i balansen. Resultatkontoer deles inn i `Inntekter` (salgsinntekter, renteinntekter, gevinster) og `Kostnader` (lønn, husleie, varekostnad, avskrivninger). Kontoklasser 3 (salgsinntekter), 4 (varekostnad), 5-7 (driftskostnader) og 8 (finans og skatt). 

---

### Scenario 1: Stiftelse av selskapet — innskudd av aksjekapital

**Hendelse:** Eieren skyter inn 200 000 kr i aksjekapital ved stiftelse av DATA1500 Konsult AS. Pengene settes inn på bedriftens bankkonto.

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 1920 | Bankinnskudd | 1 — Eiendeler | 200 000 kr | — |
| 2000 | Aksjekapital | 2 — Egenkapital og gjeld | — | 200 000 kr |

**Forklaring:** Bedriften får en eiendel (penger i banken), og eieren har en tilsvarende fordring på selskapet i form av aksjekapital. Balansen er i likevekt: Eiendeler (200 000) = Gjeld (0) + Egenkapital (200 000). Merk at dette er en ren balansetransaksjon — ingen resultatkontoer berøres.

**NS 4102-kobling:** Konto 1920 tilhører klasse 1 (Eiendeler), konto 2000 tilhører klasse 2 (Egenkapital og gjeld). Begge er balansekontoer.

---

### Scenario 2: Kjøp av kontorrekvisita på kreditt (med inngående MVA)

**Hendelse:** DATA1500 Konsult AS kjøper kontorrekvisita for 4 375 kr inkl. 25% MVA fra leverandøren Kontormateriell AS. Fakturaen betales om 30 dager (netto 30).

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 6560 | Rekvisita | 6 — Annen driftskostnad | 3 500 kr | — |
| 2710 | Inngående MVA, høy sats | 2 — Egenkapital og gjeld | 875 kr | — |
| 2400 | Leverandørgjeld | 2 — Egenkapital og gjeld | — | 4 375 kr |

**Forklaring:** En driftskostnad på 3 500 kr (eks. MVA) oppstår og reduserer egenkapitalen indirekte. Bedriften har en fordring på staten for inngående MVA på 875 kr (som vil bli avregnet mot utgående MVA). Leverandøren har en fordring på bedriften for hele beløpet inkl. MVA (4 375 kr). Summen balanserer: 3 500 + 875 = 4 375.

**NS 4102-kobling:** Konto 6560 tilhører klasse 6, konto 2710 og 2400 tilhører klasse 2. `MVA-linjer`-tabellen skal inneholde én rad for denne transaksjonen med grunnlag = 3 500 og MVA-beløp = 875.

---

### Scenario 3: Fakturering av en kunde (med utgående MVA)

**Hendelse:** Bedriften fullfører et konsulentoppdrag for kunden TechNord AS og sender en faktura på 62 500 kr inkl. 25% MVA. Betalingsbetingelse: 30 dager netto.

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 1500 | Kundefordringer | 1 — Eiendeler | 62 500 kr | — |
| 3100 | Salgsinntekt, tjenester | 3 — Salgsinntekter | — | 50 000 kr |
| 2700 | Utgående MVA, høy sats | 2 — Egenkapital og gjeld | — | 12 500 kr |

**Forklaring:** Bedriften har nå en fordring på kunden (en eiendel på 62 500 kr), har opptjent en inntekt på 50 000 kr (som øker egenkapitalen), og skylder staten 12 500 kr i utgående MVA. Summen balanserer: 62 500 = 50 000 + 12 500.

**NS 4102-kobling:** Konto 1500 tilhører klasse 1, konto 3100 tilhører klasse 3, konto 2700 tilhører klasse 2. Dette scenariet involverer `Fakturaer`- og `Fakturalinjer`-tabellene i tillegg til kjerne-transaksjonene.

---

### Scenario 4: Innbetaling fra kunde

**Hendelse:** TechNord AS betaler fakturaen fra Scenario 3 ved forfall.

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 1920 | Bankinnskudd | 1 — Eiendeler | 62 500 kr | — |
| 1500 | Kundefordringer | 1 — Eiendeler | — | 62 500 kr |

**Forklaring:** Fordringen er innfridd. Bankkontoen øker, mens kundefordringen nulles ut. Begge kontoer er eiendeler (klasse 1), så egenkapitalen og resultatet påvirkes ikke — kun sammensetningen av eiendelene endres. Fakturaens status oppdateres til `BETALT`.

---

### Scenario 5: Lønnsutbetaling med forskuddstrekk og arbeidsgiveravgift

**Hendelse:** Bedriften utbetaler lønn for mars 2026. Bruttolønn er 45 000 kr. Forskuddstrekk er 12 000 kr. Arbeidsgiveravgift (14,1%) er 6 345 kr.

**Del A — Lønnsutbetaling:**

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 5000 | Lønn til ansatte | 5 — Lønnskostnad | 45 000 kr | — |
| 1920 | Bankinnskudd | 1 — Eiendeler | — | 33 000 kr |
| 2600 | Forskuddstrekk | 2 — Egenkapital og gjeld | — | 12 000 kr |

**Del B — Arbeidsgiveravgift (periodisering):**

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 5400 | Arbeidsgiveravgift | 5 — Lønnskostnad | 6 345 kr | — |
| 2780 | Skyldig arbeidsgiveravgift | 2 — Egenkapital og gjeld | — | 6 345 kr |

**Forklaring:** Lønnskostnaden er 45 000 kr (bruttolønn). Nettolønnen som utbetales er 33 000 kr. Skattetrekket på 12 000 kr er en kortsiktig gjeld til kemneren. Arbeidsgiveravgiften er en separat kostnad og gjeld. Kontoklasse 5 (Lønnskostnad) er her representert av to ulike kontoer.

---

### Scenario 6: Kjøp av utenlandsk verdipapir (flervaluta)

**Hendelse:** Bedriften kjøper 10 aksjer i Apple Inc. (AAPL) for 175 USD per aksje. Valutakursen er 10,50 NOK/USD. Handelen koster totalt 1 750 USD = 18 375 NOK.

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 1350 | Aksjer i utenlandske selskaper | 1 — Eiendeler | 18 375 kr | — |
| 1920 | Bankinnskudd | 1 — Eiendeler | — | 18 375 kr |

**Forklaring:** Dette er en sammensatt flervalutatransaksjon. Posteringen på konto 1350 har `antall_teller = 10` (antall AAPL-aksjer) og `belop_teller = 175000` / `belop_nevner = 100` (1 750 USD). Posteringen på konto 1920 har `belop_teller = 1837500` / `belop_nevner = 100` (18 375 NOK). `Valutakurser`-tabellen inneholder kursen 10,50 NOK/USD for denne datoen. Et `Lot` opprettes for å spore kostprisen for fremtidig gevinstberegning (FIFO).

---

### Scenario 7: Innbetaling av MVA til staten (avregning)

**Hendelse:** Bedriften sender inn MVA-oppgave for 1. termin og betaler netto MVA til Skatteetaten. Utgående MVA er 12 500 kr (fra Scenario 3), inngående MVA er 875 kr (fra Scenario 2). Netto å betale: 11 625 kr.

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 2700 | Utgående MVA, høy sats | 2 — Egenkapital og gjeld | 12 500 kr | — |
| 2710 | Inngående MVA, høy sats | 2 — Egenkapital og gjeld | — | 875 kr |
| 2740 | Oppgjørskonto MVA | 2 — Egenkapital og gjeld | — | 11 625 kr |
| 1920 | Bankinnskudd | 1 — Eiendeler | — | 11 625 kr |

**Forklaring:** MVA-gjelden nulles ut. Netto MVA-beløp betales fra bankkontoen. Dette scenariet demonstrerer verdien av `Regnskapsperioder`-tabellen: perioden for 1. termin kan nå låses (`LAAST`) for å forhindre etterpostering.

---

### Scenario 8: Prosjektfakturering med delvis betaling og valutatap

**Hendelse:** DATA1500 Konsult AS fullfører et prosjekt for den svenske kunden Göteborg Tech AB. Faktura sendes på 50 000 SEK. Kursen ved fakturering er 1,02 NOK/SEK (faktura = 51 000 NOK). Kunden betaler 30 dager senere, men kursen har da falt til 0,98 NOK/SEK (innbetaling = 49 000 NOK).

**Del A — Fakturering:**

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 1500 | Kundefordringer (SEK) | 1 — Eiendeler | 51 000 kr | — |
| 3100 | Salgsinntekt, tjenester | 3 — Salgsinntekter | — | 51 000 kr |

**Del B — Innbetaling (med valutatap):**

| Kontonr | Kontonavn | Kontoklasse | Debet | Kredit |
|---|---|---|---|---|
| 1920 | Bankinnskudd | 1 — Eiendeler | 49 000 kr | — |
| 8160 | Valutatap (disagio) | 8 — Finansposter | 2 000 kr | — |
| 1500 | Kundefordringer (SEK) | 1 — Eiendeler | — | 51 000 kr |

**Forklaring:** Valutatapet på 2 000 kr (51 000 − 49 000) posteres på konto 8160 (klasse 8 — Finansposter). Dette er det eneste scenariet der klasse 8 brukes, og det illustrerer hvordan valutasvingninger påvirker resultatet. `Valutakurser`-tabellen inneholder begge kursene (ved fakturering og ved betaling).

---

## 5. Datamodellen — Entiteter og Attributter

Nedenfor beskrives alle sentrale entiteter med forklaring av essensen og hvert attributt, tilpasset en norsk regnskapskontekst basert på Norsk Standard Kontoplan (NS 4102).

**Kjerne — bok og valuta**

| Entitet (flertall) | Rolle                                          |
| ------------------ | ---------------------------------------------- |
| `Bøker`            | Ankerpunkt for hele regnskapet.                |
| `Valutaer`         | ISO 4217-valutaer (NOK, USD, EUR).             |
| `Valutakurser`     | Historiske vekslingskurser mellom to valutaer. |

**NS 4102-kontostruktur**

| Entitet (flertall) | Rolle                                                                    |
| ------------------ | ------------------------------------------------------------------------ |
| `Kontoklasser`     | Oppslagstabell for de åtte NS 4102-klassene.                             |
| `Kontoer`          | Hierarkisk kontoplan med `kontonummer` (4-sifret) og `kontoklasse` (FK). |

**Transaksjoner og posteringer**

| Entitet (flertall)        | Rolle                                                          |
| ------------------------- | -------------------------------------------------------------- |
| `Regnskapsperioder`       | Åpne/lukkede perioder med status.                              |
| `Transaksjoner`           | Bilagshode med skille mellom `bilagsdato` og `posteringsdato`. |
| `Posteringer`             | Debet/kredit-linjer. Summen skal alltid være null.             |
| `Lot`                     | Kobler kjøp og salg av verdipapirer (FIFO).                    |
| `MVA-koder`               | Norske MVA-koder og -satser.                                   |
| `MVA-linjer`              | Beregnet grunnlag og MVA-beløp per transaksjon.                |
| `Budsjetter`              | Toppnivå for budsjettering.                                    |
| `Budsjettlinjer`          | Budsjettert beløp per konto per periode.                       |
| `Planlagte Transaksjoner` | Maler for gjentakende posteringer.                             |

**Forretningsdel**

| Entitet (flertall)     | Rolle                                                      |
| ---------------------- | ---------------------------------------------------------- |
| `Kunder`               | Kunderegisteret med org.nr. og MVA-kode.                   |
| `Leverandører`         | Leverandørregisteret.                                      |
| `Fakturaer`            | Salgs- og kjøpsfakturaer med status.                       |
| `Fakturalinjer`        | Varelinjer med separate FK til inntekts- og kostnadskonto. |
| `Betalingsbetingelser` | Gjenbrukbare betalingsvilkår.                              |

---

**Primærnøkler og UUID** 

UUID - Universaly Unique IDentifier (GUID - Globally Unique IDentifier)

Noen tall for sannsynlighet for duplikater til for store tall:

| Antall UUID-er | Sannsynlighet for duplikater (betinget) |
| ---------------|-----------------------------------------|
| 2^36=68'719'476'736 |     0.000'000'000'000'000'4 |
| 2^41=2'199'023'255'552 |  0.000'000'000'000'4 |
| 2^46=70'368'744'177'664 | 0.000'000'000'4 |

Årlig sannsynliget for å bli truffet av en meteoritt er 0.000'000'000'06

Alle primærnøklene skal være UUID (Universally Unique identifier (eller GUID som man ofte finner i applikasjoner for Microsoft), https://en.wikipedia.org/wiki/Universally_unique_identifier), og dermed *surrogatnøkler*.

Datatype som skal brukes for UUID er `CHAR(32)` i stedet for en auto-inkrementerende `SERIAL`. Dette er et bevisst valg arvet fra GnuCash-modellen med tre fordeler: 
1. GUIDs kan genereres på klientsiden uten å kontakte databasen, 
2. de er globalt unike (nyttig ved sammenslåing av databaser), og 
3. de avslører ikke antall rader i tabellen. 

Ulempen er at de tar mer plass og er tregere å indeksere enn heltall.

### 5.1 Kjerne — bok og valuta

#### Bøker 

En bok er den øverste beholderen for alle andre entiteter i systemet. Den representerer ett fullstendig regnskapssystem for én virksomhet.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator (UUID) for boken. Primærnøkkel. |
| `navn` | TEXT | Navnet på regnskapsboken, f.eks. "DATA1500 Konsult AS Regnskap". Ikke NULL. |
| `organisasjonsnr` | TEXT | Virksomhetens 9-sifrede organisasjonsnummer. |
| `adresse` | TEXT | Virksomhetens forretningsadresse. |
| `rot_konto_guid` | CHAR(32) | Peker til rotkontoen i kontohierarkiet. Fremmednøkkel til `Kontoer`. Legges inn etter opprettelse av Kontoer|
| `regnskapsaar` | DATE | Startdatoen for gjeldende regnskapsår. |

**Essens:** `Bøker` er ankerpunktet for hele regnskapet. Uten en bok finnes det ingen kontoer, transaksjoner eller andre data. Tabellen inneholder metadata om virksomheten som fører regnskapet.

---

#### Valutaer 

Inneholder alle typer omsettelige valutaer som brukes i regnskapet, primært basert på ISO 4217-standarden.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `kode` | TEXT | ISO 4217-koden, f.eks. `NOK`, `USD`, `EUR`. Ikke NULL og unik.|
| `navn` | TEXT | Fullt navn, f.eks. `Norske kroner`. Ikke NULL.|
| `desimaler` | INTEGER | Antall desimaler valutaen opererer med (f.eks. 2 for NOK). Ikke NULL. Standardverdi 100. Sjekk at verdien er over 0.|
| `hent_kurs_flag` | INTEGER | Boolsk flagg (1/0): om systemet skal forsøke å hente kurser automatisk. Ikke NULL. Standardverdi 0. Sjekk at verdien er enten 0 eller 1. |
| `kurs_kilde` | TEXT | Standard kilde for automatisk kurshenting, f.eks. `norges-bank`, `ecb`.|

**Essens:** `Valutaer` definerer de monetære enhetene som brukes. Alle kontoer og transaksjoner er knyttet til en valuta.

---

#### Valutakurser

Lagrer historiske vekslingskurser mellom to valutaer på et gitt tidspunkt.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `fra_valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: valutaen som prises. Ikke NULL.|
| `til_valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: valutaen prisen er uttrykt i (basisvaluta, typisk NOK). Ikke NULL.|
| `dato` | TIMESTAMP | Tidspunktet kursen gjelder for. Ikke NULL. Standardverdien er tidspunktet når raden settes inn / oppdateres. |
| `kilde` | TEXT | Kilden til kursen, f.eks. `norges-bank`, `manuell`. |
| `type` | TEXT | Type kurs: `last` (siste), `bid` (kjøp), `ask` (salg), `nav` (for fond). Sjekk at verdiene er en av disse, - 'last', 'bid', 'ask', 'nav'.|
| `kurs_teller` | BIGINT | Teller for kursverdien (brøkrepresentasjon). Ikke NULL.|
| `kurs_nevner` | BIGINT | Nevner for kursverdien. Kurs = `kurs_teller / kurs_nevner`. Ikke NULL. Standardverdien er 100. Sjekke at verdien er større enn 0, for å unngå divisjon med 0.|

I tillegg legge inn en betingelse for at `fra_valuta_guid` er ikke lik `til_valuta_guid`. 

**Essens:** `Valutakurser` muliggjør korrekt bokføring og rapportering av transaksjoner i utenlandsk valuta.

---

#### Kontoklasser

En oppslagstabell som definerer de åtte hovedklassene i Norsk Standard Kontoplan (NS 4102).

| Attributt | Type | Forklaring |
|---|---|---|
| `klasse_nr` | INTEGER | 1–8. Primærnøkkel. |
| `navn` | TEXT | Navnet på klassen, f.eks. `Eiendeler`, `Varekostnad`. Ikke NULL og unik.|
| `type` | TEXT | `BALANSE` eller `RESULTAT`. Ikke NULL. Sjekk at verdien er enten 'BALANSE' eller 'RESULTAT'. |
| `normal_saldo` | TEXT | `DEBET` eller `KREDIT`. Angir hvilken side som øker saldoen. Ikke NULL. Sjekk at verdien er enten 'DEBET' eller 'KREDIT'.|
| `beskrivelse` | TEXT | Kort forklaring av klassens formål. |

**Essens:** `Kontoklasser` formaliserer strukturen i NS 4102 og gjør det mulig å validere kontoplanen og forenkle rapportering.

---

#### Kontoer

Implementerer den fullstendige, hierarkiske kontoplanen for virksomheten, tilpasset NS 4102.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. Ikke NULL.|
| `overordnet_guid` | CHAR(32) | Fremmednøkkel til `Kontoer` (selvhenvisning) for å bygge hierarki. |
| `valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: valutaen kontoen er denominert i. Ikke NULL. |
| `kontonummer` | INTEGER | Det 4-sifrede kontonummeret fra NS 4102, f.eks. 1920. Unik. Sjekk at verdien er mellom 1000 og 9999.|
| `kontoklasse` | INTEGER | Fremmednøkkel til `Kontoklasser` (1–8). Ikke NULL.|
| `gnucash_type` | TEXT | Den underliggende GnuCash-typen, f.eks. `BANK`, `EXPENSE`. |
| `navn` | TEXT | Kontonavnet, f.eks. `Bankinnskudd`. Ikke NULL.|
| `beskrivelse` | TEXT | Valgfri, utdypende beskrivelse. |
| `er_placeholder` | INTEGER | Boolsk flagg (1/0): om kontoen kun er en beholder for underkontoer. Ikke NULL. Standardverdien er `FALSE`.|
| `er_skjult` | INTEGER | Boolsk flagg (1/0): om kontoen skal skjules i brukergrensesnittet. Ikke NULL. Standardverdien er `FALSE`.|
| `mva_pliktig` | INTEGER | Boolsk flagg (1/0): om transaksjoner på denne kontoen normalt er MVA-pliktige. Ikke NULL. Standardverdien er `FALSE`.|
| `mva_kode_guid` | CHAR(32) | Fremmednøkkel til `MVA-koder`: standard MVA-kode for denne kontoen. *FK legges til etter opprettelse av MVA-koder*. |

**Essens:** `Kontoer` er selve kontoplanen. Kombinasjonen av `kontonummer` og `kontoklasse` sikrer samsvar med norsk standard, mens `overordnet_guid` gir hierarkisk struktur for rapportering. 

For å løse den sirkulære avhengigheten mellom `Bøker` og `Kontoer` bruk

```sql
ALTER TABLE "Bøker" 
ADD CONSTRAINT fk_rot_konto 
FOREIGN KEY (rot_konto_guid)
REFERENCES "Kontoer"(guid)
ON DELETE RESTRICT;
```

`ON DELETE RESTRICT` tolkes som at raden i `Kontoer` kan ikke slettes, hvis `Bøker.rot_konto_guid` peker på (har lik verdi i) `Kontoer.guid`. For å unngå at det pekes på fra bøker til kontoer på en konto som ikke lenger eksisterer (er slettet).

---

#### Transaksjoner

Representerer én finansiell hendelse (et bilag). Den er en overskrift som samler alle tilhørende posteringer.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. Ikke NULL. |
| `valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: transaksjonens hovedvaluta. Ikke NULL.|
| `bilagsnummer` | TEXT | Bilagsnummer fra eksternt dokument (faktura, kvittering). Ikke NULL.|
| `bilagsdato` | DATE | Datoen på det eksterne dokumentet. |
| `posteringsdato` | TIMESTAMP | Datoen transaksjonen skal regnskapsføres på. Ikke NULL. Standardverdien skal være tidspunktet for innsetting/oppdatering av raden.|
| `registreringsdato` | TIMESTAMP | Tidspunktet transaksjonen ble registrert i systemet. Ikke NULL. Standardverdien skal være tidspunktet for innsetting/oppdatering av raden.|
| `beskrivelse` | TEXT | Fritekstbeskrivelse av hendelsen. Ikke NULL. |
| `kilde` | TEXT | Hvordan transaksjonen ble opprettet: `manuell`, `import`, `planlagt`. Standardverdien skal være 'manuell'. Sjekk at verdien er en av 'manuell', 'import', 'planlagt'.|
| `periode_guid` | CHAR(32) | Fremmednøkkel til `Regnskapsperioder`. Ikke NULL.|

**Essens:** `Transaksjoner` er hendelsesloggen. Skillet mellom `bilagsdato` og `posteringsdato` er et sentralt krav i bokføringsloven.

---

#### Posteringer

Hjertet i dobbelt bokholderi. Hver postering representerer én linje på én konto i en transaksjon.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `transaksjon_guid` | CHAR(32) | Fremmednøkkel til `Transaksjoner`. Ikke NULL.|
| `konto_guid` | CHAR(32) | Fremmednøkkel til `Kontoer`. Ikke NULL.|
| `tekst` | TEXT | Notat spesifikt for denne posteringslinjen. |
| `handling` | TEXT | Handlingstype, f.eks. `Kjøp`, `Salg`, `Lønn`. |
| `avstemmingsstatus` | TEXT | `n` (ikke avstemt), `c` (klarert), `y` (avstemt mot bank). Ikke NULL. Standardverdien skal være 'n'. Sjekk at verdien er en av 'n', 'c', 'y'.|
| `avstemmingsdato` | DATE | Dato for bankavstemming. |
| `belop_teller` | BIGINT | Beløp i transaksjonens valuta (teller). Positivt = debet, negativt = kredit. Ikke NULL.|
| `belop_nevner` | BIGINT | Nevner for beløpet. Ikke NULL. Standardverdi 100. Sjekk at verdien er større enn 0. |
| `antall_teller` | BIGINT | Antall enheter (for aksjer/varer). Ikke NULL. Standardverdien skal være 0.|
| `antall_nevner` | BIGINT | Nevner for antall. Ikke NULL. Standardverdien skal være 1. Sjekk at verdrien er større enn 0.|
| `lot_guid` | CHAR(32) | Fremmednøkkel til `Lot` (for verdipapirer). |

**Essens:** `Posteringer` implementerer debet/kredit-prinsippet. Summen av `belop_teller` for alle posteringer i en transaksjon må være null.

---

#### Regnskapsperioder

Definerer regnskapsperioder (typisk måneder) og deres status.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. Ikke NULL.|
| `navn` | TEXT | Navn på perioden, f.eks. `Januar 2026`. Ikke NULL.|
| `fra_dato` | DATE | Periodens startdato. Ikke NULL.|
| `til_dato` | DATE | Periodens sluttdato. Ikke NULL.|
| `status` | TEXT | `AAPEN`, `LUKKET`, `LAAST`. Styrer hvor posteringer kan gjøres. Ikke NULL. Standardverdiene skal være 'AAPEN'. Sjekk at verdien er en av `AAPEN`, `LUKKET`, `LAAST`.|

**Essens:** `Regnskapsperioder` er avgjørende for periodisering og korrekt rapportering (f.eks. MVA-terminer).

---

#### MVA-koder

Definerer de ulike MVA-kodene og -satsene som brukes i Norge.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `kode` | TEXT | Standard MVA-kode, f.eks. `1`, `11`, `31`. Ikke NULL og unik.|
| `navn` | TEXT | Beskrivelse, f.eks. `Utgående MVA, høy sats (25%)`. Ikke NULL.|
| `type` | TEXT | `UTGAAENDE`, `INNGAAENDE`, `INGEN`. Ikke NULL. Sjekk for at verdien er en av 'UTGAAENDE', 'INNGAAENDE', 'INGEN'.|
| `sats_teller` | BIGINT | Sats i prosent (teller). Ikke NULL.|
| `sats_nevner` | BIGINT | Nevner (alltid 100 for prosent). Standardverdien skal være 100. Sjekk at verdien er større enn 0.|
| `mva_konto_guid` | CHAR(32) | Fremmednøkkel til `Kontoer`: kontoen MVA-beløpet skal posteres på. Ikke NULL.|
| `aktiv` | INTEGER | Boolsk flagg (1/0): om koden er i aktiv bruk. Ikke NULL. Standardverdien skal være 'TRUE'.|

**Essens:** `MVA-koder` sentraliserer MVA-logikken og kobler satser til spesifikke MVA-kontoer i kontoplanen.

For å definerer fremmednøkkelen i `Kontoer` mot `MVA-koder`:

```sql
ALTER TABLE "Kontoer"
ADD CONSTRAINT fk_mva_kode
FOREIGN KEY (mva_kode_guid)
REFERENCES "MVA-koder"(guid)
ON DELETE RESTRICT;
``` 

`ON DELETE RESTRICT` tolkes som at raden i `MVA-koder` kan ikke slettes, hvis `Kontoer.mva_kode_guid` peker på (har lik verdi i) `MVA-koder.guid`. For å unngå at det pekes på fra kontoer til MVA koder på rad i `MVA-linjer` som ikke lenger eksisterer (er slettet).

---

#### MVA-linjer

Lagrer beregnet MVA-grunnlag og -beløp for hver transaksjon.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `transaksjon_guid` | CHAR(32) | Fremmednøkkel til `Transaksjoner`. Ikke NULL.|
| `mva_kode_guid` | CHAR(32) | Fremmednøkkel til `MVA-koder`. Ikke NULL.|
| `grunnlag_teller` | BIGINT | MVA-grunnlaget (beløpet MVA beregnes av). Ikke NULL.|
| `grunnlag_nevner` | BIGINT | Nevner for grunnlaget. Ikke NULL. Standardverdien er 100. Sjekk at verdien er større enn 0.|
| `mva_belop_teller` | BIGINT | Det beregnede MVA-beløpet. Ikke NULL.|
| `mva_belop_nevner` | BIGINT | Nevner for MVA-beløpet. Ikke NULL. Standardverdien er 100. Sjekk at verdien er større enn 0.|

**Essens:** `MVA-linjer` gir et detaljert revisjonsspor for all MVA-beregning og er grunnlaget for MVA-oppgaven.

---

#### Lot

Brukes til å gruppere kjøps- og salgstransaksjoner for verdipapirer for å beregne realisert gevinst/tap.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `konto_guid` | CHAR(32) | Fremmednøkkel til `Kontoer` (en verdipapirkonto). |
| `beskrivelse` | TEXT | Valgfri beskrivelse av lottet. |
| `er_lukket` | INTEGER | Boolsk flagg (1/0): om alle enhetene i lottet er solgt. |

**Essens:** `Lot` er en mekanisme for å spore kostpris og gevinst for investeringer i henhold til skatteregler (FIFO-prinsippet).

---
#### Budsjetter

Toppnivå-entitet for budsjettering.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. |
| `navn` | TEXT | Navn på budsjettet, f.eks. `Årsbudsjett 2026`. |
| `beskrivelse` | TEXT | Valgfri, utdypende beskrivelse. |
| `antall_perioder` | INTEGER | Antall perioder i budsjettet (f.eks. 12 for et årsbudsjett). |

---

#### Budsjettlinjer

Inneholder de faktiske budsjetterte beløpene per konto per periode.

| Attributt | Type | Forklaring |
|---|---|---|
| `id` | INTEGER | Auto-inkrementerende primærnøkkel. |
| `budsjett_guid` | CHAR(32) | Fremmednøkkel til `Budsjetter`. |
| `konto_guid` | CHAR(32) | Fremmednøkkel til `Kontoer`. |
| `periode_nr` | INTEGER | Periodenummer (f.eks. 1 for januar, 12 for desember). |
| `belop_teller` | BIGINT | Budsjettert beløp (teller). |
| `belop_nevner` | BIGINT | Nevner for beløpet. |

**Essens:** `Budsjetter` og `Budsjettlinjer` muliggjør avviksanalyse mellom planlagte og faktiske resultater.

---

#### Planlagte Transaksjoner

Maler for gjentakende transaksjoner som husleie, lønn eller faste avdrag.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. |
| `navn` | TEXT | Navn på den planlagte transaksjonen. |
| `aktiv` | INTEGER | Boolsk flagg (1/0). |
| `startdato` | DATE | Dato for første forekomst. |
| `sluttdato` | DATE | Dato for siste forekomst (NULL for evigvarende). |
| `gjentakelse_type` | TEXT | `MAANED`, `UKE`, `DAG`, `AAR`. |
| `gjentakelse_mult` | INTEGER | Multiplikator (f.eks. 2 for annenhver måned). |
| `auto_opprett` | INTEGER | Boolsk flagg (1/0): om transaksjonen skal opprettes automatisk. |
| `sist_opprettet` | DATE | Dato for siste gang transaksjonen ble generert. |

**Essens:** `Planlagte Transaksjoner` automatiserer rutinemessig bokføring og reduserer manuelle feil.

---

#### Kunder

Register over virksomhetens kunder.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. |
| `kundenummer` | TEXT | Internt, unikt kundenummer. |
| `navn` | TEXT | Kundens navn. |
| `organisasjonsnr` | TEXT | Kundens organisasjonsnummer (hvis bedrift). |
| `adresse` | TEXT | Fakturaadresse. |
| `epost` | TEXT | E-postadresse for fakturering. |
| `valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: foretrukket fakturavaluta. |
| `betalingsbetingelse_guid` | CHAR(32) | Fremmednøkkel til `Betalingsbetingelser`. |
| `mva_kode_guid` | CHAR(32) | Fremmednøkkel til `MVA-koder`: standard MVA-behandling for kunden. |
| `aktiv` | INTEGER | Boolsk flagg (1/0). |

---

#### Leverandører

Register over virksomhetens leverandører.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. |
| `leverandornummer` | TEXT | Internt, unikt leverandørnummer. |
| `navn` | TEXT | Leverandørens navn. |
| `organisasjonsnr` | TEXT | Leverandørens organisasjonsnummer. |
| `adresse` | TEXT | Postadresse. |
| `epost` | TEXT | E-postadresse for kontakt. |
| `valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: foretrukket betalingsvaluta. |
| `betalingsbetingelse_guid` | CHAR(32) | Fremmednøkkel til `Betalingsbetingelser`. |
| `aktiv` | INTEGER | Boolsk flagg (1/0). |

---

#### Fakturaer

Representerer salgsfakturaer, inngående fakturaer og utgiftsbilag.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. |
| `fakturanummer` | TEXT | Eksternt fakturanummer (unikt per leverandør/salg). |
| `type` | TEXT | `SALG`, `KJOP`, `UTGIFT`. |
| `kunde_guid` | CHAR(32) | Fremmednøkkel til `Kunder` (for salgsfakturaer). |
| `leverandor_guid` | CHAR(32) | Fremmednøkkel til `Leverandører` (for kjøpsfakturaer). |
| `valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`. |
| `fakturadato` | DATE | Datoen på fakturaen. |
| `forfallsdato` | DATE | Betalingsfrist. |
| `posteringsdato` | TIMESTAMP | Dato fakturaen ble bokført. |
| `status` | TEXT | `UTKAST`, `SENDT`, `BETALT`, `KREDITERT`. |
| `betalingsbetingelse_guid` | CHAR(32) | Fremmednøkkel til `Betalingsbetingelser`. |
| `transaksjon_guid` | CHAR(32) | Fremmednøkkel til `Transaksjoner` (kobler til betalingstransaksjonen). |

---

#### Fakturalinjer

Representerer én linje på en faktura.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `faktura_guid` | CHAR(32) | Fremmednøkkel til `Fakturaer`. |
| `beskrivelse` | TEXT | Varetekst eller tjenestebeskrivelse. |
| `antall_teller` | BIGINT | Antall enheter (teller). |
| `antall_nevner` | BIGINT | Nevner for antall. |
| `enhetspris_teller` | BIGINT | Pris per enhet (teller). |
| `enhetspris_nevner` | BIGINT | Nevner for enhetspris. |
| `inntekt_konto_guid` | CHAR(32) | Fremmednøkkel til `Kontoer` (en inntektskonto i klasse 3). |
| `kostnad_konto_guid` | CHAR(32) | Fremmednøkkel til `Kontoer` (en kostnadskonto i klasse 4-7). |
| `mva_kode_guid` | CHAR(32) | Fremmednøkkel til `MVA-koder`. |
| `mva_inkludert` | INTEGER | Boolsk flagg (1/0): om enhetsprisen er oppgitt inkludert MVA. |
| `rabatt_teller` | BIGINT | Rabatt i prosent (teller). |
| `rabatt_nevner` | BIGINT | Nevner for rabatt. |

---

#### Betalingsbetingelser

Definerer betalingsbetingelser som kan gjenbrukes på tvers av kunder, leverandører og fakturaer.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `navn` | TEXT | Navn, f.eks. `30 dager netto`. |
| `type` | TEXT | `DAGER` (antall dager) eller `PROXIMO` (fast dag i måneden). |
| `forfallsdager` | INTEGER | Antall dager til forfall. |
| `kontantrabatt_dager` | INTEGER | Antall dager for å oppnå kontantrabatt. |
| `rabatt_teller` | BIGINT | Kontantrabatt i prosent (teller). |
| `rabatt_nevner` | BIGINT | Nevner for rabatt. |

**Essens:** `Kunder`, `Leverandører`, `Fakturaer`, `Fakturalinjer` og `Betalingsbetingelser` utgjør et komplett fakturerings- og reskontrosystem som er tett integrert med kjerne-regnskapet. En faktura er ikke bare et dokument, men en hendelse som direkte påvirker regnskapskontoer som `Kundefordringer` og `Salgsinntekter`. 

**Eksempel: Forhold mellom entiteter** 

Her er noen punkter som kan hjelpe å komme i gang med mermaid diagrammet for regnskapsmodellen.

- En bok (`Bøker`) **inneholder** ingen eller mange transaksjoner (`Transaksjoner`); omvendt, - en transaksjon hører til i nøyaktig en bok. En bok **inneholder** også ingen eller mange kontoer og **definerer** ingen eller mange regnskapsperioder. 
- En bok **har** ingen eller mange kunder, fakturaer, leverandører, budsjetter, planlagte transaksjoner. 
- En transaksjon har ingen eller mange mva-linjer. 
- Resten kan kartlegges basert på beskrivelsene av enitetene i dette kapittelet (kapittel 5). 
- Eksempel på mermaid kode for forholdene som `Bøker`, `Kontoklasser` og `Kontoer` er involvert i. 
```bash
# eksempel på 
BØKER ||--o{ KONTOER                 : "inneholder"
BØKER ||--o{ TRANSAKSJONER           : "inneholder"
BØKER ||--o{ BUDSJETTER              : "har"
BØKER ||--o{ REGNSKAPSPERIODER       : "definerer"
BØKER ||--o{ PLANLAGTE_TRANSAKSJONER : "har"
BØKER ||--o{ KUNDER                  : "har"
BØKER ||--o{ LEVERANDORER            : "har"
BØKER ||--o{ FAKTURAER               : "inneholder"

KONTOKLASSER ||--o{ KONTO     : "klassifiserer"
KONTOER      ||--o{ KONTO     : "er overordnet" # for å implementere hierarki av kontoer
KONTOER      }o--|| VALUTAER  : "denominert i"
KONTOER      }o--o| MVA_KODER : "bruker"
POSTERINGER  }o--|| KONTOER   : "berører"
LOT.         }o--|| KONTOER   : "tilhører"
```


## 6. Prosjektoppgaver (NS 4102)

### Oppgave 1: Implementasjon av datamodellen og mermaid-diagrammet

Skriv et SQL-skript (`oppgave1.sql`) som oppretter følgende tabeller med korrekte datatyper, primærnøkler og fremmednøkler i PostgreSQL:

- `Bøker`, `Valutaer`, `Valutakurser`
- `Kontoklasser`, `Kontoer`
- `Regnskapsperioder`
- `Transaksjoner`, `Posteringer`
- `MVA_koder`, `MVA_linjer`

Lag et diagramm i mermaid.live. 

**Krav til skjemaet:**

- `Kontoer.overordnet_guid` skal være en selvhenvisende fremmednøkkel med `ON DELETE RESTRICT`.
- `Kontoer.kontoklasse` skal være en fremmednøkkel til `Kontoklasser.klasse_nr`.
- `Posteringer.transaksjon_guid` skal ha `ON DELETE CASCADE`.
- `Posteringer.konto_guid` skal ha `ON DELETE RESTRICT`.
- `CHECK`-betingelse på `Regnskapsperioder.status`: kun `'AAPEN'`, `'LUKKET'` eller `'LAAST'`.
- `CHECK`-betingelse på `Posteringer.avstemmingsstatus`: kun `'n'`, `'c'` eller `'y'`.
- `CHECK`-betingelse på `Kontoer.kontonummer`: mellom 1000 og 8999.
- Alle `belop_nevner`- og `antall_nevner`-felt skal ha `CHECK (... > 0)` for å forhindre divisjon med null.

**Ytelsesindekser**

- Indekser opprettes på kolonner som hyppig brukes i WHERE-betingelser og JOIN-operasjoner. PostgreSQL bruker B-tre-indekser som standard. Primærnøkler (guid) indekseres automatisk.
- Følgende 9 ytelsesindekser skal defineres (bruk de navn som er foreslått):

```sql 
   Tabell      |            Indeksnavn             
---------------+----------------------------------
 Kontoer       | idx_kontoer_bok_guid
 Kontoer       | idx_kontoer_kontonummer
 Kontoer       | idx_kontoer_overordnet_guid
 MVA-linjer    | idx_mva_linjer_transaksjon_guid
 Posteringer   | idx_posteringer_konto_guid
 Posteringer   | idx_posteringer_transaksjon_guid
 Transaksjoner | idx_transaksjoner_bok_guid
 Transaksjoner | idx_transaksjoner_periode_guid
 Transaksjoner | idx_transaksjoner_posteringsdato
``` 

**Kommentarer i databaseskjema** 

- Bruk `COMMENT ON TABLE ... IS` for å legge inn kommentarer på en tabell (entitet) og `COMMENT ON COLUMN ... IS` for å legge inn kommentarer på en kolonne (attributt).
- Se eksempel for opprettelse av tabellen `Kontoer` (se kravspesifikasjon for alle tabellene i  :


```sql 
CREATE TABLE "Kontoer" (
    guid            CHAR(32)    PRIMARY KEY,
    bok_guid        CHAR(32)    NOT NULL
                                REFERENCES "Bøker"(guid) ON DELETE RESTRICT,
    overordnet_guid CHAR(32)    REFERENCES "Kontoer"(guid) ON DELETE RESTRICT,
    valuta_guid     CHAR(32)    NOT NULL
                                REFERENCES "Valutaer"(guid) ON DELETE RESTRICT,
    kontonummer     INTEGER     UNIQUE
                                CHECK (kontonummer BETWEEN 1000 AND 9999),
    kontoklasse     INTEGER     NOT NULL
                                REFERENCES "Kontoklasser"(klasse_nr) ON DELETE RESTRICT,
    gnucash_type    TEXT,
    navn            TEXT        NOT NULL,
    beskrivelse     TEXT,
    er_placeholder  BOOLEAN     NOT NULL DEFAULT FALSE,
    er_skjult       BOOLEAN     NOT NULL DEFAULT FALSE,
    mva_pliktig     BOOLEAN     NOT NULL DEFAULT FALSE,
    mva_kode_guid   CHAR(32)    -- FK legges til etter opprettelse av MVA-koder
);

COMMENT ON TABLE  "Kontoer"                 IS 'Hierarkisk kontoplan. Kombinasjon av kontonummer og kontoklasse sikrer NS 4102-samsvar.';
COMMENT ON COLUMN "Kontoer".overordnet_guid IS 'Selvhenvisende FK. NULL = rotkonto. Bygger trestrukturen.';
COMMENT ON COLUMN "Kontoer".kontonummer     IS '4-sifret NS 4102-kontonummer (1000-9999). NULL for placeholder-kontoer.';
COMMENT ON COLUMN "Kontoer".er_placeholder  IS 'TRUE: kontoen er kun en beholder for underkontoer, kan ikke posteres på.';
COMMENT ON COLUMN "Kontoer".mva_pliktig     IS 'TRUE: transaksjoner på denne kontoen er normalt MVA-pliktige.';
``` 

Hvordan ser det ut i en kjørende instans av PostgreSQL? Legg merke til bruken av `\d+` kommandoen i psql-shell for å kunne vise kommentarer (`Description`) lagt til med `COMMENT ON COLUMN`. `ON DELETE RESTRICT` forhindrer utilsiktet sletting av data i andre tabeller som er i aktiv bruk.

```sql 
regnskap=# \d+ "Kontoer"
                                                                               Table "public.Kontoer"
     Column      |     Type      | Collation | Nullable | Default | Storage  | Compression | Stats target |                               Description                                
-----------------+---------------+-----------+----------+---------+----------+-------------+--------------+--------------------------------------------------------------------------
 guid            | character(32) |           | not null |         | extended |             |              | 
 bok_guid        | character(32) |           | not null |         | extended |             |              | 
 overordnet_guid | character(32) |           |          |         | extended |             |              | Selvhenvisende FK. NULL = rotkonto. Bygger trestrukturen.
 valuta_guid     | character(32) |           | not null |         | extended |             |              | 
 kontonummer     | integer       |           |          |         | plain    |             |              | 4-sifret NS 4102-kontonummer (1000-9999). NULL for placeholder-kontoer.
 kontoklasse     | integer       |           | not null |         | plain    |             |              | 
 gnucash_type    | text          |           |          |         | extended |             |              | 
 navn            | text          |           | not null |         | extended |             |              | 
 beskrivelse     | text          |           |          |         | extended |             |              | 
 er_placeholder  | boolean       |           | not null | false   | plain    |             |              | TRUE: kontoen er kun en beholder for underkontoer, kan ikke posteres på.
 er_skjult       | boolean       |           | not null | false   | plain    |             |              | 
 mva_pliktig     | boolean       |           | not null | false   | plain    |             |              | TRUE: transaksjoner på denne kontoen er normalt MVA-pliktige.
 mva_kode_guid   | character(32) |           |          |         | extended |             |              | 
Indexes:
    "Kontoer_pkey" PRIMARY KEY, btree (guid)
    "Kontoer_kontonummer_key" UNIQUE CONSTRAINT, btree (kontonummer)
    "idx_kontoer_bok_guid" btree (bok_guid)
    "idx_kontoer_kontonummer" btree (kontonummer)
    "idx_kontoer_overordnet_guid" btree (overordnet_guid)
Check constraints:
    "Kontoer_kontonummer_check" CHECK (kontonummer >= 1000 AND kontonummer <= 9999)
Foreign-key constraints:
    "Kontoer_bok_guid_fkey" FOREIGN KEY (bok_guid) REFERENCES "Bøker"(guid) ON DELETE RESTRICT
    "Kontoer_kontoklasse_fkey" FOREIGN KEY (kontoklasse) REFERENCES "Kontoklasser"(klasse_nr) ON DELETE RESTRICT
    "Kontoer_overordnet_guid_fkey" FOREIGN KEY (overordnet_guid) REFERENCES "Kontoer"(guid) ON DELETE RESTRICT
    "Kontoer_valuta_guid_fkey" FOREIGN KEY (valuta_guid) REFERENCES "Valutaer"(guid) ON DELETE RESTRICT
    "fk_mva_kode" FOREIGN KEY (mva_kode_guid) REFERENCES "MVA-koder"(guid) ON DELETE RESTRICT
Referenced by:
    TABLE ""Kontoer"" CONSTRAINT "Kontoer_overordnet_guid_fkey" FOREIGN KEY (overordnet_guid) REFERENCES "Kontoer"(guid) ON DELETE RESTRICT
    TABLE ""MVA-koder"" CONSTRAINT "MVA-koder_mva_konto_guid_fkey" FOREIGN KEY (mva_konto_guid) REFERENCES "Kontoer"(guid) ON DELETE RESTRICT
    TABLE ""Posteringer"" CONSTRAINT "Posteringer_konto_guid_fkey" FOREIGN KEY (konto_guid) REFERENCES "Kontoer"(guid) ON DELETE RESTRICT
    TABLE ""Bøker"" CONSTRAINT "fk_rot_konto" FOREIGN KEY (rot_konto_guid) REFERENCES "Kontoer"(guid) ON DELETE RESTRICT
Access method: heap
``` 
---

### Oppgave 2: Populering med testdata

Skriv et SQL-skript (`oppgave2.sql`) som implementerer alle åtte brukerscenarioene fra kapittel 4. Dataene skal inkludere:

- Valutaer: NOK, USD, SEK.
- Valutakurser: USD/NOK og SEK/NOK for relevante datoer.
- Alle åtte kontoklasser med korrekte `type` og `normal_saldo`.
- Kontoer for alle kontonumre som er brukt i scenarioene.
- Én regnskapsperiode per termin (6 terminer for 2026).
- Alle åtte transaksjonene med tilhørende posteringer.
- MVA-koder for utgående (25%) og inngående (25%) MVA, samt tilhørende MVA-linjer.

**Verifisering:** Etter populering skal følgende spørring returnere null rader (alle transaksjoner balanserer):

```sql
SELECT t.guid, t.beskrivelse, SUM(p.belop_teller::numeric / p.belop_nevner) AS saldo
FROM Transaksjoner t
JOIN Posteringer p ON p.transaksjon_guid = t.guid
GROUP BY t.guid, t.beskrivelse
HAVING ABS(SUM(p.belop_teller::numeric / p.belop_nevner)) > 0.001;
```

#### Spesifikke krav til Oppgave 2

**`DO $$...$$`-blokk for Transaksjoner og Posteringer**

Alle transaksjoner og posteringer skal opprettes i én anonym PL/pgSQL-blokk (`DO $$...$$`). Dette gjør det mulig å bruke lokale variabler (`tx_guid`, `bok_guid` osv.) som holder GUIDs mellom INSERT-setninger. Alternativet er å bruke delspørringer for dette men det kan gjore koden svært vanskelig å lese.

`plpgsql`-utvidelsen er vanligvis installert i PostgreSQL som er i Docker imagen. PL/pgSQL er et prosedyrespråk for PostgreSQL-databasesystemet. Se https://www.postgresql.org/docs/current/plpgsql-overview.html for flere detaljer.

**Brøkrepresentasjon i praksis**

Alle beløp lagres med `belop_nevner = 100` (standard), slik at beløp i øre lagres i `belop_teller`. Eksempel: 200 000 kr lagres som `belop_teller = 20000000` (to hundre millioner øre). Dette er konsistent med GnuCash-modellen og brukes i regnskapessystemer for å unngå desimalfeil.

| Beløp i kr | `belop_teller` | `belop_nevner` | Beregning |
|---|---|---|---|
| 200 000,00 | 20 000 000 | 100 | 20 000 000 / 100 = 200 000 |
| 4 375,00 | 437 500 | 100 | 437 500 / 100 = 4 375 |
| 875,00 | 87 500 | 100 | 87 500 / 100 = 875 |
| 62 500,00 | 6 250 000 | 100 | 6 250 000 / 100 = 62 500 |

**Fortegnskonvensjon (positiv = debet, negativ = kredit)**

GnuCash-modellen bruker en enkel fortegnskonvensjon: **positivt beløp = debet**, **negativt beløp = kredit**. Dobbelt bokholderi-prinsippet håndheves av at summen av alle `belop_teller`-verdier for én transaksjon alltid skal være **0**. Dette er den eneste integritetsregelen som ikke kan håndheves med en enkel `CHECK`-betingelse — den krever en aggregatspørring over `Posteringer` gruppert på `transaksjon_guid`.

**Hierarkisk kontoplan med placeholder-kontoer**

Kontoplanen bygges i tre nivåer:
1. **Rotkonto** — én enkelt placeholder som er overordnet alt.
2. **Klassekontoer** — åtte placeholder-kontoer, én per NS 4102-klasse.
3. **Driftskontoer** — de faktiske kontoene med 4-sifrede kontonumre.

Placeholder-kontoer (`er_placeholder = TRUE`) kan ikke posteres på direkte — de er kun beholdere i hierarkiet. Dette muliggjør rekursive spørringer med `WITH RECURSIVE` i Oppgave 3.

**Scenario 7 — MVA-avregning uten `2740`-postering**

I scenario 7 er `2740 Oppgjørskonto MVA` utelatt fra posteringene. Scenarioteksten viser kontoen, men i praksis er det vanlig å postere direkte fra `2700`/`2710` til `1920` uten å gå via en oppgjørskonto. Begge tilnærminger er korrekte — oppgjørskontoen er nyttig for revisjonsspor, men ikke strengt nødvendig. Man kan velge hvilken variant man bruker, så lenge transaksjonen balanserer.

---

### Oppgave 3: Hierarkisk Kontoplan med `WITH RECURSIVE` (obligatorisk)

#### Del A — Rekursiv traversering

Skriv en rekursiv CTE-spørring som henter hele kontoplanen og presenterer den med innrykk for å vise hierarkiet. Resultatet skal vise kontonummer, kontonavn, dybdenivå og en `sti`-kolonne som viser hele veien fra rot til konto.

```sql
-- forventet output første  5 linjer 
 nivaa | kontonr  |                navn                |                              sti                               
-------+----------+------------------------------------+----------------------------------------------------------------
     0 | —        | Rotkonto                           | Rotkonto
     1 |   —      |   Annen driftskostnad              | Rotkonto > Annen driftskostnad
     2 |     6560 |     Rekvisita                      | Rotkonto > Annen driftskostnad > Rekvisita
     1 |   —      |   Egenkapital og gjeld             | Rotkonto > Egenkapital og gjeld
     2 |     2000 |     Aksjekapital                   | Rotkonto > Egenkapital og gjeld > Aksjekapital
     ...
```

#### Del B — Aggregert saldo oppover i hierarkiet

Utvid spørringen fra Del A. Bruk en CTE (Common Table Expression) til å først beregne saldoen for hver enkelt konto (basert på `Posteringer`). Deretter, i den rekursive delen, aggreger saldoene oppover slik at overordnede kontoer summerer saldoene til alle sine underkontoer. Presenter en fullstendig saldobalanse for alle balansekontoer (klasse 1 og 2), sortert etter kontonummer.

---

### Oppgave 4: Ytelsesanalyse med `EXPLAIN ANALYZE` og `MATERIALIZED VIEW` (obligatorisk)

#### Del A — Opprett et komplekst `VIEW`

Lag et `VIEW` kalt `v_salgsrapport` som joiner `Fakturaer`, `Fakturalinjer`, `Kunder`, `Kontoer` (for inntektskonto) og `MVA_koder` for å vise en detaljert salgsrapport. Viewet skal inneholde: kundenavn, fakturanummer, fakturadato, varebeskrivelse, antall, enhetspris (eks. MVA), MVA-sats og totalbeløp inkl. MVA.

#### Del B — Analyser med `EXPLAIN ANALYZE`

Kjør følgende kommando og lim inn det fullstendige resultatet i prosjektrapporten:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT * FROM v_salgsrapport;
```

Analyser resultatet og svar på følgende spørsmål i rapporten:

- Hvilken join-algoritme valgte PostgreSQL (f.eks. `Hash Join`, `Nested Loop`)?
- Hva er den totale estimerte og faktiske kjøretiden?
- Identifiser den operasjonen som bruker mest tid (høyest `actual time`).

#### Del C — Implementer `MATERIALIZED VIEW`

Opprett et `MATERIALIZED VIEW` kalt `mv_salgsrapport` med nøyaktig samme spørring:

```sql
CREATE MATERIALIZED VIEW mv_salgsrapport AS
SELECT * FROM v_salgsrapport;
```

Kjør `EXPLAIN ANALYZE SELECT * FROM mv_salgsrapport;` og sammenlign kjøretiden med Del B.

#### Del D — Diskusjon

Forklar i rapporten:

- Hvorfor er det materialiserte viewet raskere for lesing?
- Hva er den fundamentale ulempen (stikkord: datakonsistens, `REFRESH MATERIALIZED VIEW`)?
- I hvilke situasjoner er et `MATERIALIZED VIEW` uegnet, og hva kan brukes i stedet?

---

### Oppgave 5: Flerdimensjonal Analyse med `ROLLUP` og `CUBE` (obligatorisk)

#### Del A — Kostnadsanalyse med `ROLLUP`

Skriv en spørring som viser total kostnad per kontoklasse og per konto for alle resultatkontoer (klasse 3–8). Bruk `GROUP BY ROLLUP(klasse_navn, konto_navn)` for å få subtotaler per klasse og en totalsum for alle kontoer.

Det forventede resultatet skal ha tre typer rader:
- Én rad per konto med faktisk kostnad.
- Én subtotalrad per kontoklasse (der `konto_navn IS NULL`).
- Én totalrad for alle klasser (der både `klasse_navn` og `konto_navn` er `NULL`).

Forklar i rapporten hva `NULL` betyr i de to siste radtypene, og knytt dette til treverdislogikk i SQL.

#### Del B — MVA-analyse med `CUBE`

Skriv en spørring som analyserer `MVA_linjer` og viser totalt MVA-beløp gruppert på `MVA_koder.type` og `MVA_koder.kode`. Bruk `GROUP BY CUBE(type, kode)` for å generere alle mulige subtotaler.

Resultatet skal inneholde:
- Beløp per type og kode (f.eks. `UTGAAENDE` + kode `1`).
- Subtotal per type (f.eks. totalt `UTGAAENDE` MVA, der `kode IS NULL`).
- Subtotal per kode på tvers av type (der `type IS NULL`).
- Totalsum for all MVA (der begge er `NULL`).

Forklar forskjellen mellom `ROLLUP` og `CUBE` med utgangspunkt i disse to eksemplene.

---

### Oppgave 6: Databaseadministrasjon og Tilgangskontroll (obligatorisk)

**Læringsmål:**

-   Forstå rollen som databaseadministrator (DBA).
-   Opprette brukere og roller i PostgreSQL.
-   Tildele rettigheter med `GRANT` og `REVOKE`.
-   Forstå og anvende prinsippet om minste rettighet (Principle of Least Privilege).
-   Implementere finkornet tilgangskontroll med Row Level Security (RLS).

**Scenario:**

Norsk Konsult AS har vokst og trenger en mer robust tilgangskontroll til regnskapsdatabasen. Du har fått i oppgave, i rollen som DBA, å implementere en sikkerhetsmodell som skiller mellom ulike ansvarsområder.

#### Del A: Opprett Roller og Brukere

Skriv et SQL-skript som oppretter følgende fire roller og fire brukere:

| Type | Navn | Beskrivelse |
|---|---|---|
| **Rolle** | `regnskap_admin` | Skal ha fulle rettigheter til å endre og administrere alle tabeller. |
| **Rolle** | `revisor` | Skal kun ha lesetilgang (`SELECT`) til alle tabeller. |
| **Rolle** | `regnskapsforer` | Skal kunne lese alle tabeller, men kun sette inn og oppdatere transaksjonsdata (`Transaksjoner`, `Posteringer`, `MVA-linjer`). Skal **ikke** kunne slette. |
| **Rolle** | `les_tilgang` | Svært begrenset rolle som kun kan lese oppslagstabeller (`Kontoer`, `Kontoklasser`, `Valutaer`). |
| **Bruker** | `dba_ola` | En DBA som skal tildeles `regnskap_admin`-rollen. |
| **Bruker** | `revisor_kari` | En intern revisor som skal tildeles `revisor`-rollen. |
| **Bruker** | `bokforer_per` | En regnskapsmedarbeider som skal tildeles `regnskapsforer`-rollen. |
| **Bruker** | `ekstern_revisor` | En ekstern konsulent som kun skal ha den mest begrensede tilgangen (`les_tilgang`). |

#### Del B: Tildel Rettigheter (`GRANT`)

Bruk `GRANT`-kommandoer for å tildele de nødvendige rettighetene til hver av de fire rollene, og deretter tildel rollene til de respektive brukerne.

#### Del C: Verifisering og Testing

1.  Skriv en spørring mot `information_schema.role_table_grants` for å verifisere at rettighetene er tildelt korrekt.
2.  Bruk `SET ROLE`-kommandoen for å teste tilgangskontrollen. Vis med konkrete SQL-kall at:
    -   `bokforer_per` **ikke** kan slette fra `Transaksjoner`.
    -   `ekstern_revisor` **ikke** kan lese fra `Transaksjoner`.
    -   `ekstern_revisor` **kan** lese fra `Kontoer`.

#### Del D: Row Level Security (RLS)

Som en ekstra sikkerhetsmekanisme skal du implementere en policy som begrenser hvilke rader en regnskapsfører kan se.

1.  Aktiver RLS på `Transaksjoner`-tabellen.
2.  Opprett en policy kalt `policy_aar_filter` som sikrer at brukere med `regnskapsforer`-rollen kun kan se transaksjoner der `bilagsdato` er i inneværende år.
3.  Opprett en policy kalt `policy_revisor_alt` som sikrer at `revisor`-rollen fortsatt kan se alle transaksjoner (ellers vil de også bli begrenset av standard `DENY`-policyen).

#### Del E: Diskusjon

Forklar i rapporten:

-   Hva er forskjellen på en `ROLE` og en `USER` i PostgreSQL?
-   Hvorfor er det god praksis å tildele rettigheter til roller i stedet for direkte til brukere?
-   Hvilken fordel gir Row Level Security sammenlignet med å kun bruke `GRANT`? Gi et konkret eksempel fra regnskapsmodellen.

---


## 7. Transaksjoner og NoSQL

### 7.1 Innledning

Den opprinnelige prosjektoppgaven etablerer en solid relasjonsdatabase for dobbelt bokholderi. Denne reviderte spesifikasjonen utvider prosjektet i to viktige retninger:

For det første introduseres **dybde i SQL-databasen** gjennom obligatoriske oppgaver som dekker avansert transaksjonsbehandling, feilhåndtering og samtidighetskontroll. Disse temaene er avgjørende for å bygge systemer som er pålitelige nok til å håndtere finansielle data — der en feil kan bety at penger "forsvinner" fra systemet.

For det andre introduseres **bredde i arkitektur** gjennom en utvidelse som krever at studentene bygger en ekstern mikrotjeneste. Denne tjenesten integrerer en NoSQL-database med den eksisterende SQL-databasen og henter sanntidsdata fra åpne finansielle API-er. Formålet er å gi studentene praktisk erfaring med **polyglot persistens**, der ulike databaseteknologier brukes til det de er best egnet for.

### 7.2 Bakgrunn: Transaksjoner i Dobbelt Bokholderi

I dobbelt bokholderi er en regnskapstransaksjon (f.eks. "betal leverandør 5000 kr") alltid en sammensatt operasjon: én rad settes inn i `Transaksjoner`-tabellen, og minst to rader settes inn i `Posteringer`-tabellen — én for debet og én for kredit. Summen av alle `belop_teller`-verdier i `Posteringer` for én transaksjon skal alltid være null.

Denne sammensatte operasjonen er et klassisk eksempel på en situasjon der **atomisitet** er absolutt nødvendig. Hvis systemet krasjer etter at `Transaksjoner`-raden er satt inn, men før `Posteringer`-radene er skrevet, vil databasen inneholde en "halvferdig" transaksjon som bryter med det grunnleggende prinsippet i dobbelt bokholderi. Det er nettopp for å forhindre slike situasjoner at DBHS-er implementerer transaksjonsbehandling med ACID-egenskapene.

> **ACID** er et akronym for **Atomicity** (atomisitet), **Consistency** (konsistens), **Isolation** (isolasjon) og **Durability** (varighet). Disse fire egenskapene garanterer at databasetransaksjoner behandles pålitelig.

---

### Oppgave 7: Atomisk Regnskapspostering (K10.1, K10.2)

**Mål:** Implementere og demonstrere at en regnskapspostering i dobbelt bokholderi er en udelelig (atomisk) operasjon.

**Læringsutbytte:** Studenten forstår og kan anvende `DO`-blokk, `BEGIN`, `COMMIT` og `ROLLBACK` for å sikre dataintegritet.

#### Implementasjonskrav

Løsningen skal bruke en anonym `DO`-blokk i PostgreSQL, som er en enkel måte å kjøre prosedyrisk kode på uten å måtte definere en permanent funksjon. Hele blokken kjøres innenfor en `BEGIN`/`COMMIT`-transaksjon.

Det er to måter å `DO`-blokk direkte i psql (eller utføre som skript):

1. Når du kjører `DO` direkte i psql uten en forutgående `BEGIN`, oppretter PostgreSQL automatisk en ny transaksjon for hele `DO`-setningen. I dette tilfellet er det tillatt å bruke transaksjonskommandoer som `COMMIT` og `ROLLBACK` inni `DO`-blokken, fordi blokken "eier" sin egen transaksjonskontekst.

```sql
DO $$
BEGIN
    INSERT INTO "Transaksjoner" (...) VALUES (...);
    COMMIT;   -- ✓ Tillatt her
    INSERT INTO "Posteringer" (...) VALUES (...);
    COMMIT;   -- ✓ Tillatt her
END;
$$;
```

2. Når du kjører `DO` etter en `BEGIN`-setning, er transaksjonen allerede startet av den ytre BEGIN. `DO`-blokken arver denne transaksjonen og kan ikke bruke `COMMIT` eller `ROLLBACK` inni seg — fordi det ville forstyrre den ytre transaksjonens kontroll.

```sql 
BEGIN;
    DO $$
    BEGIN
        INSERT INTO "Transaksjoner" (guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato,
         posteringsdato, beskrivelse, periode_guid) VALUES (...);
        COMMIT; -- Ikke tillatt her
    END;
    $$;
COMMIT;
```

Det anbefales å bruke `DO`-blokk på måten (2).


#### Demonstrasjonskrav

Studenten skal demonstrere to scenarier:

**Scenario A — Vellykket postering:** En gyldig transaksjon der debet og kredit balanserer. Vis at begge tabellene (`Transaksjoner` og `Posteringer`) er korrekt oppdatert etter `COMMIT`.

Følgende er gitt:
- Transaksjon: Kjøp av kontorrekvisita 2 000 kr + 25% MVA = 2 500 kr
- Debet: 6560 Rekvisita           2 000 kr  (+200000 øre)
- Debet: 2710 Inngående MVA         500 kr  ( +50000 øre)
- Kredit: 2400 Leverandørgjeld    2 500 kr  (-250000 øre)
- Balanse: 200000 + 50000 - 250000 = 0   (skal sjekkes etter at transaksjonen er gjennomført)

**Scenario B — Mislykket postering:** Forsøk å postere til en konto-GUID som ikke finnes i `Kontoer`-tabellen. Vis at `ROLLBACK` utføres og at databasen er uendret — verken `Transaksjoner`-raden eller noen `Posteringer`-rader er satt inn.

Bruk av `exception`-struktur i PL/pgSQL: 
```sql 
BEGIN

DO $$
DECLARE
    -- Bevisst ugyldig: 32 tegn, men finnes ikke i Kontoer-tabellen
	v_ugyldig_guid CHAR(32) := 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF';
	-- de andre guid som man trenger for INSERT
	-- v_book_guid CHAR(32)
	-- ...
BEGIN
-- Bruker select for å finne de nødvendige guid-er	
-- Bruk STRICT for å unngå feil hvis `select` returnerer ingen rader
-- SELECT guid INTO STRICT v_bok_guid FROM "Bøker" LIMIT 1; 
-- ...	
-- INSERT INTO "Transaksjoner" (guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato,
--         posteringsdato, beskrivelse, periode_guid) VALUES (...);
-- INSERT INTO "Posteringer"
--        (guid, transaksjon_guid, konto_guid, tekst,
--         belop_teller, belop_nevner, antall_teller, antall_nevner)
--    VALUES (...);

-- En anbefalt måte å takle feil på i PostgreSQL
EXCEPTION
    -- Når man bruker STRICT i SELECT INTO som brukes videre i INSERT er det viktig
    -- å fange tilfeller hvor SELECT returnerer ingen rader
	WHEN NO_DATA_FOUND THEN
        RAISE NOTICE 'FEIL: Et nødvendig oppslag returnerte ingen rad (konto, valuta eller periode mangler).';
        RAISE;  -- Re-kast → ytre transaksjon markeres ABORTED
    -- Prøver å fange en spesifikk unntak/feil
    WHEN foreign_key_violation THEN
        RAISE NOTICE 'FEIL FANGET: Fremmednøkkelbrudd — konto_guid "%" finnes ikke i Kontoer.', v_ugyldig_guid;
        RAISE NOTICE 'ROLLBACK vil utføres automatisk for hele transaksjonen.';
        RAISE;  -- Re-kast unntaket for å trigge ROLLBACK
    -- Alle andre feil blir også behandlet og feilmelding fra postgreSQL vist
    -- SQLSTATE inneholer PostgreSQL sin feiltypekode, f.eks. 23503 for FK-brudd
    -- https://www.postgresql.org/docs/current/errcodes-appendix.html
    -- SQLERRM inneholder feilmeldingsteksten 
    WHEN OTHERS THEN
        RAISE NOTICE 'UVENTET FEIL: SQLSTATE=%, MELDING=%', SQLSTATE, SQLERRM;
        RAISE; -- Re-kast unntaket for å trigge ROLLBACK
END $$

ROLLBACK;

\echo '--- Verifisering etter ROLLBACK ---'
-- Bekreft at den feilede transaksjonen IKKE finnes
SELECT
    CASE WHEN COUNT(*) = 0
         THEN 'OK: B-2026-FEIL finnes IKKE i databasen (ROLLBACK virket)'
         ELSE 'FEIL: B-2026-FEIL ble lagret til tross for ROLLBACK!'
    END AS rollback_status
FROM "Transaksjoner"
WHERE bilagsnummer = 'B-2026-FEIL';
``` 

- For feilkoder og unntaksnavn (som `foreign_key_violation`) i PostgreSQL se https://www.postgresql.org/docs/current/errcodes-appendix.html




#### Rapportkrav

Diskuter i rapporten:
- Hva ville ha skjedd uten transaksjonsbehandling dersom systemet krasjet mellom innsetting av `Transaksjoner`-raden og `Posteringer`-radene?
- Forklar hvilken av ACID-egenskapene som er mest kritisk for dobbelt bokholderi, og begrunn svaret.

---

### Oppgave 8: Feilhåndtering og Gjenoppbygging (K10.3, K10.4, K10.5, K10.6)

**Mål:** Forstå hvordan et DBHS bruker transaksjonsloggen til å gjenoppbygge en konsistent tilstand etter feil.

**Læringsutbytte:** Studenten kan forklare forskjellen mellom UNDO og REDO, og forstår rollen til sjekkpunkter og sikkerhetskopiering.

#### 8a: Teoretisk Oppgave

Gitt følgende forenklete transaksjonslogg for et regnskapssystem:

| Log-sekvensnr. | Hendelse | Transaksjon | Detalj |
|---|---|---|---|
| 1 | `BEGIN` | T1 | — |
| 2 | `WRITE` | T1 | Sett inn i `Transaksjoner` (guid = 'A1') |
| 3 | `BEGIN` | T2 | — |
| 4 | `WRITE` | T2 | Sett inn i `Transaksjoner` (guid = 'B1') |
| 5 | `CHECKPOINT` | — | — |
| 6 | `WRITE` | T1 | Sett inn i `Posteringer` (tx_guid = 'A1', konto = 'Kasse') |
| 7 | `COMMIT` | T1 | — |
| 8 | `WRITE` | T2 | Sett inn i `Posteringer` (tx_guid = 'B1', konto = 'Bank') |
| 9 | `CRASH` | — | Systemfeil |

Besvar følgende spørsmål i rapporten:
1.  Hvilke transaksjoner skal **REDO**-es etter krasjet, og hvilke skal **UNDO**-es? Begrunn svaret.
2.  Forklar rollen til **sjekkpunktet** (linje 5) i gjenoppbyggingsprosessen. Hva ville ha vært annerledes uten det?
3.  Forklar forskjellen mellom en **instansfeil** (f.eks. strømbrudd) og en **mediefeil** (f.eks. diskkrasj), og hvilken rolle **sikkerhetskopiering** spiller for sistnevnte.

#### 8b: Praktisk Oppgave

Bruk databasesystemets innebygde funksjoner for å demonstrere at en `ROLLBACK` faktisk angrer alle endringer:

```sql
BEGIN;

INSERT INTO "Transaksjoner" (guid, ...) VALUES ('test-guid-123', ...);
INSERT INTO "Posteringer" (guid, tx_guid, ...) VALUES ('split-guid-1', 'test-guid-123', ...);

-- Verifiser at dataene er synlige innenfor transaksjonen
SELECT * FROM "Transaksjoner" WHERE guid = 'test-guid-123'; -- Skal returnere 1 rad

ROLLBACK;

-- Verifiser at dataene er borte etter ROLLBACK
SELECT * FROM "Transaksjoner" WHERE guid = 'test-guid-123'; -- Skal returnere 0 rader
```

---

### Oppgave 9: Samtidighetsproblemer og Låsing (K10.7, K10.8, K10.9, K10.10, K10.11)

**Mål:** Forstå, demonstrere og løse "tapt oppdatering" (lost update) — et klassisk samtidighetsproblem i flerbrukerdatabaser.

**Læringsutbytte:** Studenten kan forklare les-beregn-skriv-syklusen, forstår behovet for låsing, og kan implementere korrekte løsninger.

#### Scenario: Dobbel Betaling

To regnskapsmedarbeidere, Ane og Bjørn, jobber samtidig mot den samme bedriftskontoen (en konto av typen `BANK` i `Kontoer`-tabellen). Kontoen har en saldo på 10 000 kr, representert som summen av alle tilknyttede `Posteringer`.

-   **Ane (Prosess A):** Skal registrere en utbetaling på 3 000 kr.
-   **Bjørn (Prosess B):** Skal registrere en innbetaling på 1 500 kr.

Korrekt sluttresultat: 10 000 − 3 000 + 1 500 = **8 500 kr**.

#### Demonstrer Problemet (Tapt Oppdatering)

*GnuCash/NS 4102-modellen* er immun mot tapt oppdatering slik den er designet, fordi at den aldri bruker `UPDATE SET saldo = ny_verdi`. Saldoen beregnes alltid som SUM("Posteringer".belop_teller). I Oppgave 7 skulle dere lage en løsning, som garanterte at oppdateringer av `Transaksjoner` og `Posteringer` blir alltid oppdatert eller angret innenfor en transaksjon. For å demonstrere ekte tapt oppdatering må man bruke en separat tabell med en oppdaterbar saldo-kolonne. 

Dere skal bruke Python programmeringsspråk for å simulerer "samtidighet", dvs. at Ana og Bjørn kobler seg til databasen med to separate Psycopg2-koblinger (hvor Psycopg2 er en mye brukt adapter for Python programmeringsspråket; https://www.psycopg.org/), som da utføres i to separate *tråder* i Python (`threading` modulen). 

Ta utgangspunkt i Python programmet i filen ´oppgave9.py´ hvor funksjoner for alle operasjoner mot databasen og samtidighet som simulerer den usikre *les-beregn-skriv*-syklusen er implementert. 

Skriv python kode som genererer følgende output. 

### Programmeringsoppgaver: Integrasjon med Ekstern Tjeneste og NoSQL

#### Relevante Eksterne API-er

Det finnes flere relevante tjenester som man kan utforske. 

| Tjeneste | Datatype | Bruksområde i GnuCash-modellen | Fordeler for prosjektet |
|---|---|---|---|
| **Norges Bank API** [^7] | Valutakurser, renter | Automatisk oppdatering av `prices`-tabellen for NOK mot andre valutaer. | Offisiell, pålitelig kilde. Enkel REST API med SDMX-JSON-format. Ingen API-nøkkel nødvendig. |
| **Alpha Vantage** [^8] | Aksjekurser, valuta, krypto | Oppdatering av `prices` for et bredt spekter av `commodities`. | Svært omfattende. Gratis API-nøkkel. |
| **ExchangeRate-API** [^9] | Valutakurser | Enklere alternativ for global valutakursdata. | Krever ingen API-nøkkel for grunnleggende bruk. |
| **CoinGecko** [^10] | Kryptovaluta-kurser | Spesialisert for kryptovalutaer som `commodities`. | Bransjestandard for kryptodata. |
| **OpenFIGI** [^11] | Finansielle identifikatorer | Mapping mellom ticker-symboler og globale FIGI-identifikatorer. | Introduserer en reell problemstilling innen finansiell datahåndtering. |

**Norges Bank API** og **Alpha Vantage** skal brukes i oppgaveløsningene.

#### Arkitektur for oppgaver 10 og 11

Studentene skal implementere en frittstående tjeneste (f.eks. et Python-skript) som:

1.  Kommuniserer med det valgte eksterne API-et.
2.  Bruker en NoSQL-database for mellomlagring eller staging av rådata.
3.  Oppdaterer den sentrale SQL-databasen med prosesserte data, **alltid innenfor en SQL-transaksjon** (jf. Oppgave 5).

Det siste punktet er en bevisst kobling til transaksjonsoppgavene: selv den eksterne tjenesten må sikre at oppdateringer av `Verdipapirer` og `Kurser` er atomiske.

#### Oppgave 10: Sanntids Valutakurs-Cache med Redis

**Mål:** Implementere en effektiv cache-mekanisme for å redusere antall kall mot et eksternt API.

**Teknologi:** **Redis** (Key-Value Store)

Tjenesten skal implementere følgende cache-logikk:

1.  Konstruer en unik nøkkel for valutaparet, f.eks. `price:USD:NOK`.
2.  Sjekk om nøkkelen finnes i Redis (`GET price:USD:NOK`).
    -   **Cache Hit:** Returner den lagrede verdien umiddelbart uten å kalle API-et.
    -   **Cache Miss:** Kall det eksterne API-et (**Norges Bank API**), lagre resultatet i Redis med en TTL på 1 time (`SET price:USD:NOK 9.65 EX 3600`), og oppdater `prices`-tabellen i SQL-databasen **innenfor en transaksjon**.

**TTL** - `time to live` eller `hop limit` er en mekanisme som begrenser *livstid* til data i en datamaskin eller i et nettverk.

**Krav til implementasjon:**
- Skriv et skript som simulerer 10 påfølgende kall for samme valutapar og logger om hvert kall resulterte i Cache Hit eller Cache Miss.
- Diskuter i rapporten: Hva er konsekvensen for datakonsistens dersom Redis-cachen inneholder en foreldet kurs og en bruker registrerer en transaksjon basert på den? Hvordan kan dette håndteres?

#### Oppgave 11: Staging av Finansielle Dokumenter med MongoDB

**Mål:** Bruke en dokumentdatabase som et mellomlager for komplekse, semi-strukturerte API-responser.

**Teknologi:** **MongoDB** (Dokumentdatabase)

Tjenesten skal implementere følgende ETL-logikk (Extract, Transform, Load):

1.  **Extract:** Hent detaljert kurshistorikk for et verdipapir fra **Alpha Vantage**.
2.  **Load (rådata):** Lagre hele JSON-responsen som ett dokument i MongoDB-collectionen `raw_financial_data`. Hvert dokument skal inneholde feltene `ticker_symbol`, `fetch_timestamp` og `api_source` i tillegg til de rå API-dataene.
3.  **Transform & Load (SQL):** Trekk ut de relevante feltene (siste kurs og dato) og oppdater `Kurser`-tabellen i SQL-databasen **innenfor en transaksjon**.

**Krav til implementasjon:**
- Hent og lagre data for minst 3 ulike verdipapirer i MongoDB.
- Vis hvordan SQL-databasen oppdateres korrekt.
- Diskuter i rapporten: Hva er fordelen med å beholde rådataene i MongoDB selv etter at SQL-databasen er oppdatert? (Hint: tenk på feilsøking, historikk og muligheten for å re-prosessere data.)


---


## A. Vurdering

Følgende vil bli lagt vekt på i vurdering:
- Riktige datatyper, primærnøkler, fremmednøkler og integritetsregler er implementert korrekt. 
- Det er generert korrekte testdata. Alle scenarioer er korrekt implementert og alle transaksjoner balanserer.
- Spørringene gir korrekte resultater.
- Det er gitt en klar forklaring av designvalg. 
- En forståelse av NULL-verdier og treverdilogikken i forbindelse med datamodellen for dobbel bokholderi er vist. 
- En kjørbar løsning i Python er presentert for oppgaver 10 og 11 basert på en start-kode, som vil bli gjennomgått på forelesninger.


---

## B. Referanser

[^1]: GnuCash Wiki. *SQL — GnuCash*. Tilgjengelig: https://wiki.gnucash.org/wiki/SQL

[^2]: Wikipedia. *Dobbelt bokholderi*. Tilgjengelig: https://no.wikipedia.org/wiki/Dobbelt_bokholderi

[^3]: GnuCash Documentation. *Accounts — GnuCash Tutorial and Concepts Guide*. Tilgjengelig: https://gnucash-docs-rst.readthedocs.io/en/latest/guide/C/ch_accts.html

[^4]: GnuCash Documentation. *Basic Accounting Concepts*. Tilgjengelig: https://lists.gnucash.org/docs/C/gnucash-guide/accts-concepts1.html

[^5]: Store Norske Leksikon. *Dobbel bokføring*. Tilgjengelig: https://snl.no/dobbel_bokf%C3%B8ring

[^6]: Norsk Standard Kontoplan. *NS 4102*. Tilgjengelig: https://standard.no/fagomrader/kontoplan-for-regnskap/

[^7]: Norges Bank. *Data warehouse for open data*. Tilgjengelig: https://www.norges-bank.no/en/topics/statistics/open-data/

[^8]: Alpha Vantage. *API Documentation*. Tilgjengelig: https://www.alphavantage.co/documentation/

[^9]: ExchangeRate-API. *Free Currency Converter API*. Tilgjengelig: https://www.exchangerate-api.com/

[^10]: CoinGecko. *Crypto Data API*. Tilgjengelig: https://www.coingecko.com/en/api

[^11]: OpenFIGI. *Open Financial Instrument Global Identifier*. Tilgjengelig: https://www.openfigi.com/