-- =============================================================================
-- OPPGAVE 5 — Setup: Opprette forretnings-tabeller og testdata
-- Forutsetning: oppgave1.sql og oppgave2.sql fra Oppgave 1 og 2 er kjørt.
-- =============================================================================


BEGIN;

-- Betalingsbetingelser
CREATE TABLE IF NOT EXISTS Betalingsbetingelser (
    guid            CHAR(32)        PRIMARY KEY,
    navn            VARCHAR(100)    NOT NULL,
    dager_til_forfall INTEGER       NOT NULL DEFAULT 30,
    rabatt_prosent  NUMERIC(5,2)    DEFAULT 0,
    rabatt_dager    INTEGER         DEFAULT 0
);

-- Kunder
CREATE TABLE IF NOT EXISTS Kunder (
    guid                    CHAR(32)        PRIMARY KEY,
    bok_guid                CHAR(32)        NOT NULL REFERENCES Booker(guid),
    navn                    VARCHAR(200)    NOT NULL,
    organisasjonsnr         VARCHAR(20),
    epost                   VARCHAR(200),
    betalingsbetingelse_guid CHAR(32)       REFERENCES Betalingsbetingelser(guid)
);

-- Fakturaer
CREATE TABLE IF NOT EXISTS Fakturaer (
    guid                    CHAR(32)        PRIMARY KEY,
    bok_guid                CHAR(32)        NOT NULL REFERENCES Booker(guid),
    fakturanummer           VARCHAR(30)     NOT NULL,
    type                    VARCHAR(10)     NOT NULL CHECK (type IN ('SALG','KJØP','UTGIFT')),
    status                  VARCHAR(15)     NOT NULL DEFAULT 'UTKAST'
                                CHECK (status IN ('UTKAST','SENDT','BETALT','KREDITERT')),
    kunde_guid              CHAR(32)        REFERENCES Kunder(guid),
    fakturadato             DATE            NOT NULL,
    forfallsdato            DATE            NOT NULL,
    valuta_guid             CHAR(32)        NOT NULL REFERENCES Valutaer(guid),
    transaksjon_guid        CHAR(32)        REFERENCES Transaksjoner(guid)
);

-- Fakturalinjer
CREATE TABLE IF NOT EXISTS Fakturalinjer (
    guid                    CHAR(32)        PRIMARY KEY,
    faktura_guid            CHAR(32)        NOT NULL REFERENCES Fakturaer(guid) ON DELETE CASCADE,
    beskrivelse             VARCHAR(500)    NOT NULL,
    antall                  NUMERIC(12,4)   NOT NULL DEFAULT 1,
    enhetspris_teller       BIGINT          NOT NULL,
    enhetspris_nevner       INTEGER         NOT NULL DEFAULT 100 CHECK (enhetspris_nevner > 0),
    mva_kode_guid           CHAR(32)        REFERENCES MVA_koder(guid),
    inntektskonto_guid      CHAR(32)        REFERENCES Kontoer(guid)
);

-- =============================================================================
-- Testdata for Oppgave 4
-- =============================================================================

-- Betalingsbetingelse: 30 dager netto
INSERT INTO Betalingsbetingelser (guid, navn, dager_til_forfall)
VALUES (REPLACE(gen_random_uuid()::TEXT, '-', ''), '30 dager netto', 30);

-- Kunder
INSERT INTO Kunder (guid, bok_guid, navn, organisasjonsnr, epost, betalingsbetingelse_guid)
VALUES
    (REPLACE(gen_random_uuid()::TEXT, '-', ''),
     (SELECT guid FROM Booker LIMIT 1),
     'TechNord AS', '123456789', 'regnskap@technord.no',
     (SELECT guid FROM Betalingsbetingelser WHERE navn = '30 dager netto')),

    (REPLACE(gen_random_uuid()::TEXT, '-', ''),
     (SELECT guid FROM Booker LIMIT 1),
     'Göteborg Tech AB', '556789012', 'invoice@goteborgtech.se',
     (SELECT guid FROM Betalingsbetingelser WHERE navn = '30 dager netto'));

-- Faktura F-2026-001 (TechNord AS, scenario 3)
INSERT INTO Fakturaer
    (guid, bok_guid, fakturanummer, type, status, kunde_guid, fakturadato, forfallsdato, valuta_guid, transaksjon_guid)
VALUES
    (REPLACE(gen_random_uuid()::TEXT, '-', ''),
     (SELECT guid FROM Booker LIMIT 1),
     'F-2026-001', 'SALG', 'BETALT',
     (SELECT guid FROM Kunder WHERE navn = 'TechNord AS'),
     '2026-03-10', '2026-04-09',
     (SELECT guid FROM Valutaer WHERE kode = 'NOK'),
     (SELECT guid FROM Transaksjoner WHERE bilagsnummer = 'Faktura 3'));

-- Fakturalinje for F-2026-001: 50 timer konsulentbistand à 1 000 kr
INSERT INTO Fakturalinjer
    (guid, faktura_guid, beskrivelse, antall, enhetspris_teller, enhetspris_nevner, mva_kode_guid, inntektskonto_guid)
VALUES
    (REPLACE(gen_random_uuid()::TEXT, '-', ''),
     (SELECT guid FROM Fakturaer WHERE fakturanummer = 'F-2026-001'),
     'Konsulentbistand mars 2026', 50, 100000, 100,
     (SELECT guid FROM MVA_koder WHERE kode = '1'),
     (SELECT guid FROM Kontoer WHERE kontonummer = 3100));

-- Faktura F-2026-002 (Göteborg Tech AB, scenario 8)
INSERT INTO Fakturaer
    (guid, bok_guid, fakturanummer, type, status, kunde_guid, fakturadato, forfallsdato, valuta_guid, transaksjon_guid)
VALUES
    (REPLACE(gen_random_uuid()::TEXT, '-', ''),
     (SELECT guid FROM Booker LIMIT 1),
     'F-2026-002', 'SALG', 'BETALT',
     (SELECT guid FROM Kunder WHERE navn = 'Göteborg Tech AB'),
     '2026-04-01', '2026-05-01',
     (SELECT guid FROM Valutaer WHERE kode = 'SEK'),
     (SELECT guid FROM Transaksjoner WHERE bilagsnummer = 'Faktura 8'));

-- Fakturalinje for F-2026-002: 100 timer à 500 SEK
INSERT INTO Fakturalinjer
    (guid, faktura_guid, beskrivelse, antall, enhetspris_teller, enhetspris_nevner, mva_kode_guid, inntektskonto_guid)
VALUES
    (REPLACE(gen_random_uuid()::TEXT, '-', ''),
     (SELECT guid FROM Fakturaer WHERE fakturanummer = 'F-2026-002'),
     'Systemutvikling april 2026', 100, 50000, 100,
     NULL,  -- Eksport: ingen norsk MVA
     (SELECT guid FROM Kontoer WHERE kontonummer = 3100));

COMMIT;