# Datamodellen (kapittel 5 fra OPPGAVE.md)

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
| `navn` | TEXT | Navnet på regnskapsboken, f.eks. "DATA1500 Konsult AS Regnskap". |
| `organisasjonsnr` | TEXT | Virksomhetens 9-sifrede organisasjonsnummer. |
| `adresse` | TEXT | Virksomhetens forretningsadresse. |
| `rot_konto_guid` | CHAR(32) | Peker til rotkontoen i kontohierarkiet. Fremmednøkkel til `Kontoer`. |
| `regnskapsaar` | DATE | Startdatoen for gjeldende regnskapsår. |

**Essens:** `Bøker` er ankerpunktet for hele regnskapet. Uten en bok finnes det ingen kontoer, transaksjoner eller andre data. Tabellen inneholder metadata om virksomheten som fører regnskapet.

---

#### Valutaer 

Inneholder alle typer omsettelige valutaer som brukes i regnskapet, primært basert på ISO 4217-standarden.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `kode` | TEXT | ISO 4217-koden, f.eks. `NOK`, `USD`, `EUR`. |
| `navn` | TEXT | Fullt navn, f.eks. `Norske kroner`. |
| `desimaler` | INTEGER | Antall desimaler valutaen opererer med (f.eks. 2 for NOK). |
| `hent_kurs_flag` | INTEGER | Boolsk flagg (1/0): om systemet skal forsøke å hente kurser automatisk. |
| `kurs_kilde` | TEXT | Standard kilde for automatisk kurshenting, f.eks. `norges-bank`, `ecb`. |

**Essens:** `Valutaer` definerer de monetære enhetene som brukes. Alle kontoer og transaksjoner er knyttet til en valuta.

---

#### Valutakurser

Lagrer historiske vekslingskurser mellom to valutaer på et gitt tidspunkt.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `fra_valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: valutaen som prises. |
| `til_valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: valutaen prisen er uttrykt i (basisvaluta, typisk NOK). |
| `dato` | TIMESTAMP | Tidspunktet kursen gjelder for. |
| `kilde` | TEXT | Kilden til kursen, f.eks. `norges-bank`, `manuell`. |
| `type` | TEXT | Type kurs: `last` (siste), `bid` (kjøp), `ask` (salg), `nav` (for fond). |
| `kurs_teller` | BIGINT | Teller for kursverdien (brøkrepresentasjon). |
| `kurs_nevner` | BIGINT | Nevner for kursverdien. Kurs = `kurs_teller / kurs_nevner`. |

**Essens:** `Valutakurser` muliggjør korrekt bokføring og rapportering av transaksjoner i utenlandsk valuta.

---

#### Kontoklasser

En oppslagstabell som definerer de åtte hovedklassene i Norsk Standard Kontoplan (NS 4102).

| Attributt | Type | Forklaring |
|---|---|---|
| `klasse_nr` | INTEGER | 1–8. Primærnøkkel. |
| `navn` | TEXT | Navnet på klassen, f.eks. `Eiendeler`, `Varekostnad`. |
| `type` | TEXT | `BALANSE` eller `RESULTAT`. |
| `normal_saldo` | TEXT | `DEBET` eller `KREDIT`. Angir hvilken side som øker saldoen. |
| `beskrivelse` | TEXT | Kort forklaring av klassens formål. |

**Essens:** `Kontoklasser` formaliserer strukturen i NS 4102 og gjør det mulig å validere kontoplanen og forenkle rapportering.

---

#### Kontoer

Implementerer den fullstendige, hierarkiske kontoplanen for virksomheten, tilpasset NS 4102.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. |
| `overordnet_guid` | CHAR(32) | Fremmednøkkel til `Kontoer` (selvhenvisning) for å bygge hierarki. |
| `valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: valutaen kontoen er denominert i. |
| `kontonummer` | INTEGER | Det 4-sifrede kontonummeret fra NS 4102, f.eks. 1920. |
| `kontoklasse` | INTEGER | Fremmednøkkel til `Kontoklasser` (1–8). |
| `gnucash_type` | TEXT | Den underliggende GnuCash-typen, f.eks. `BANK`, `EXPENSE`. |
| `navn` | TEXT | Kontonavnet, f.eks. `Bankinnskudd`. |
| `beskrivelse` | TEXT | Valgfri, utdypende beskrivelse. |
| `er_placeholder` | INTEGER | Boolsk flagg (1/0): om kontoen kun er en beholder for underkontoer. |
| `er_skjult` | INTEGER | Boolsk flagg (1/0): om kontoen skal skjules i brukergrensesnittet. |
| `mva_pliktig` | INTEGER | Boolsk flagg (1/0): om transaksjoner på denne kontoen normalt er MVA-pliktige. |
| `mva_kode_guid` | CHAR(32) | Fremmednøkkel til `MVA-koder`: standard MVA-kode for denne kontoen. |

**Essens:** `Kontoer` er selve kontoplanen. Kombinasjonen av `kontonummer` og `kontoklasse` sikrer samsvar med norsk standard, mens `overordnet_guid` gir hierarkisk struktur for rapportering.

---

#### Transaksjoner

Representerer én finansiell hendelse (et bilag). Den er en overskrift som samler alle tilhørende posteringer.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. |
| `valuta_guid` | CHAR(32) | Fremmednøkkel til `Valutaer`: transaksjonens hovedvaluta. |
| `bilagsnummer` | TEXT | Bilagsnummer fra eksternt dokument (faktura, kvittering). |
| `bilagsdato` | DATE | Datoen på det eksterne dokumentet. |
| `posteringsdato` | TIMESTAMP | Datoen transaksjonen skal regnskapsføres på. |
| `registreringsdato` | TIMESTAMP | Tidspunktet transaksjonen ble registrert i systemet. |
| `beskrivelse` | TEXT | Fritekstbeskrivelse av hendelsen. |
| `kilde` | TEXT | Hvordan transaksjonen ble opprettet: `manuell`, `import`, `planlagt`. |
| `periode_guid` | CHAR(32) | Fremmednøkkel til `Regnskapsperioder`. |

**Essens:** `Transaksjoner` er hendelsesloggen. Skillet mellom `bilagsdato` og `posteringsdato` er et sentralt krav i bokføringsloven.

---

#### Posteringer

Hjertet i dobbelt bokholderi. Hver postering representerer én linje på én konto i en transaksjon.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `transaksjon_guid` | CHAR(32) | Fremmednøkkel til `Transaksjoner`. |
| `konto_guid` | CHAR(32) | Fremmednøkkel til `Kontoer`. |
| `tekst` | TEXT | Notat spesifikt for denne posteringslinjen. |
| `handling` | TEXT | Handlingstype, f.eks. `Kjøp`, `Salg`, `Lønn`. |
| `avstemmingsstatus` | TEXT | `n` (ikke avstemt), `c` (klarert), `y` (avstemt mot bank). |
| `avstemmingsdato` | DATE | Dato for bankavstemming. |
| `belop_teller` | BIGINT | Beløp i transaksjonens valuta (teller). Positivt = debet, negativt = kredit. |
| `belop_nevner` | BIGINT | Nevner for beløpet. |
| `antall_teller` | BIGINT | Antall enheter (for aksjer/varer). |
| `antall_nevner` | BIGINT | Nevner for antall. |
| `lot_guid` | CHAR(32) | Fremmednøkkel til `Lot` (for verdipapirer). |

**Essens:** `Posteringer` implementerer debet/kredit-prinsippet. Summen av `belop_teller` for alle posteringer i en transaksjon må være null.

---

#### Regnskapsperioder

Definerer regnskapsperioder (typisk måneder) og deres status.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `bok_guid` | CHAR(32) | Fremmednøkkel til `Bøker`. |
| `navn` | TEXT | Navn på perioden, f.eks. `Januar 2026`. |
| `fra_dato` | DATE | Periodens startdato. |
| `til_dato` | DATE | Periodens sluttdato. |
| `status` | TEXT | `AAPEN`, `LUKKET`, `LAAST`. Styrer hvor posteringer kan gjøres. |

**Essens:** `Regnskapsperioder` er avgjørende for periodisering og korrekt rapportering (f.eks. MVA-terminer).

---

#### MVA-koder

Definerer de ulike MVA-kodene og -satsene som brukes i Norge.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `kode` | TEXT | Standard MVA-kode, f.eks. `1`, `11`, `31`. |
| `navn` | TEXT | Beskrivelse, f.eks. `Utgående MVA, høy sats (25%)`. |
| `type` | TEXT | `UTGAAENDE`, `INNGAAENDE`, `INGEN`. |
| `sats_teller` | BIGINT | Sats i prosent (teller). |
| `sats_nevner` | BIGINT | Nevner (alltid 100 for prosent). |
| `mva_konto_guid` | CHAR(32) | Fremmednøkkel til `Kontoer`: kontoen MVA-beløpet skal posteres på. |
| `aktiv` | INTEGER | Boolsk flagg (1/0): om koden er i aktiv bruk. |

**Essens:** `MVA-koder` sentraliserer MVA-logikken og kobler satser til spesifikke MVA-kontoer i kontoplanen.

---

#### MVA-linjer

Lagrer beregnet MVA-grunnlag og -beløp for hver transaksjon.

| Attributt | Type | Forklaring |
|---|---|---|
| `guid` | CHAR(32) | Unik identifikator. Primærnøkkel. |
| `transaksjon_guid` | CHAR(32) | Fremmednøkkel til `Transaksjoner`. |
| `mva_kode_guid` | CHAR(32) | Fremmednøkkel til `MVA-koder`. |
| `grunnlag_teller` | BIGINT | MVA-grunnlaget (beløpet MVA beregnes av). |
| `grunnlag_nevner` | BIGINT | Nevner for grunnlaget. |
| `mva_belop_teller` | BIGINT | Det beregnede MVA-beløpet. |
| `mva_belop_nevner` | BIGINT | Nevner for MVA-beløpet. |

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