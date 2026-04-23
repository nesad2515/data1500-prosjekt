DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

CREATE TABLE Valutaer(
	guid CHAR(32) PRIMARY KEY, 
	kode TEXT UNIQUE NOT NULL CHECK (length(kode) = 3), 
	navn TEXT NOT NULL, 
	desimaler INTEGER DEFAULT 100 NOT NULL CHECK (desimaler > 0),
	hent_kurs_flag INTEGER DEFAULT 0 NOT NULL CHECK(hent_kurs_flag = 0 OR hent_kurs_flag = 1),
	kurs_kilde TEXT
);


CREATE TABLE Valutakurser(
	guid CHAR(32) PRIMARY KEY,
	fra_valuta_guid CHAR(32) NOT NULL CONSTRAINT fk_fra_valuta_valutakurser REFERENCES valutaer(guid),
	til_valuta_guid CHAR(32) NOT NULL CONSTRAINT fk_til_valuta_valutakurser REFERENCES valutaer(guid),
	dato TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	kurs_kilde TEXT NOT NULL,
	type_kurs TEXT NOT NULL CHECK(type_kurs IN ('last', 'bid', 'ask', 'nav')),
	kurs_teller BIGINT NOT NULL,
	kurs_nevner BIGINT NOT NULL DEFAULT 100 CHECK(kurs_nevner > 0),
	CONSTRAINT sjekk_ulike_valutaer CHECK(fra_valuta_guid != til_valuta_guid)
);


CREATE TABLE Kontoklasser(
	klasse_nr INTEGER PRIMARY KEY CHECK(klasse_nr BETWEEN 1 AND 8),
	navn TEXT UNIQUE NOT NULL,
	type_klasse TEXT NOT NULL CHECK(type_klasse IN ('BALANSE', 'RESULTAT')),
	normal_saldo TEXT NOT NULL CHECK(normal_saldo IN ('DEBET', 'KREDIT')),
	beskrivelse TEXT
);


CREATE TABLE Booker(
	guid CHAR(32) PRIMARY KEY,
	navn TEXT NOT NULL,
	organisasjonsnr TEXT,
	adresse TEXT,
	regnskapsaar DATE
);


CREATE TABLE Regnskapsperioder(
	guid CHAR(32) PRIMARY KEY,
	bok_guid CHAR(32) NOT NULL CONSTRAINT fk_regnskapsperioder_bok_guid REFERENCES booker(guid),
	navn TEXT NOT NULL,
	fra_dato DATE NOT NULL,
	til_dato DATE NOT NULL,
	status TEXT NOT NULL DEFAULT 'AAPEN' CHECK(status IN('AAPEN', 'LUKKET', 'LAAST')),
	CONSTRAINT dato_check CHECK(til_dato >= fra_dato)
);


CREATE TABLE Transaksjoner(
	guid CHAR(32) PRIMARY KEY,
	bok_guid CHAR(32) NOT NULL CONSTRAINT fk_transaksjoner_bok_guid REFERENCES booker(guid),
	valuta_guid CHAR(32) NOT NULL CONSTRAINT fk_transaksjoner_valuta_guid REFERENCES valutaer(guid),
	bilagsnummer TEXT NOT NULL UNIQUE,
	bilagsdato DATE NOT NULL,
	posteringsdato TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	registreringsdato TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	beskrivelse TEXT NOT NULL,
	kilde TEXT DEFAULT 'manuell' CHECK(kilde IN ('manuell', 'import', 'planlagt')),
	periode_guid CHAR(32) NOT NULL CONSTRAINT fk_transaksjoner_periode_guid REFERENCES regnskapsperioder(guid),
	CONSTRAINT reg_check CHECK(registreringsdato >= bilagsdato)
);


CREATE TABLE Kontoer(
	guid CHAR(32) PRIMARY KEY,
	bok_guid CHAR(32) NOT NULL CONSTRAINT fk_kontoer_bok_guid REFERENCES booker(guid),
	overordnet_guid CHAR(32) CONSTRAINT hierarki REFERENCES kontoer(guid) ON DELETE RESTRICT,
	valuta_guid CHAR(32) NOT NULL CONSTRAINT fk_kontoer_valuta_guid REFERENCES valutaer(guid),
	kontonummer INTEGER CHECK(kontonummer BETWEEN 1000 AND 9999),
	kontoklasse INTEGER NOT NULL CONSTRAINT fk_kontoer_kontoklasse REFERENCES kontoklasser(klasse_nr),
	gnucash_type TEXT,
	navn TEXT NOT NULL,
	beskrivelse TEXT,
	er_placeholder BOOLEAN NOT NULL DEFAULT FALSE,
	er_skjult BOOLEAN NOT NULL DEFAULT FALSE,
	mva_pliktig BOOLEAN NOT NULL DEFAULT FALSE
);


ALTER TABLE booker ADD COLUMN rot_konto_guid CHAR(32); 
ALTER TABLE booker ADD CONSTRAINT fk_rot_konto FOREIGN KEY (rot_konto_guid) REFERENCES kontoer(guid) ON DELETE RESTRICT;


CREATE TABLE Posteringer(
	guid CHAR(32) PRIMARY KEY,
	transaksjon_guid CHAR(32) NOT NULL CONSTRAINT fk_posteringer_transaksjoner_guid REFERENCES transaksjoner(guid) ON DELETE CASCADE,
	konto_guid CHAR(32) NOT NULL CONSTRAINT fk_posteringer_konto_guid REFERENCES kontoer(guid) ON DELETE RESTRICT,
	tekst TEXT,
	handling TEXT,
	avstemmingsstatus TEXT NOT NULL DEFAULT 'n' CHECK(avstemmingsstatus IN('n', 'c', 'y')),
	avstemmingsdato DATE,
	belop_teller BIGINT NOT NULL,
	belop_nevner BIGINT NOT NULL DEFAULT 100 CHECK(belop_nevner > 0),
	antall_teller BIGINT NOT NULL DEFAULT 0,
	antall_nevner BIGINT NOT NULL DEFAULT 1 CHECK(antall_nevner > 0)
);


CREATE TABLE MVA_koder(
	guid CHAR(32) PRIMARY KEY,
	kode TEXT UNIQUE NOT NULL,
	navn TEXT NOT NULL,
	type_mva TEXT NOT NULL CHECK(type_mva IN('UTGAAENDE', 'INNGAAENDE', 'INGEN')),
	sats_teller BIGINT NOT NULL,
	sats_nevner BIGINT DEFAULT 100 CHECK(sats_nevner > 0),
	mva_konto_guid CHAR(32) NOT NULL CONSTRAINT fk_mva_koder_konto_guid REFERENCES kontoer(guid),
	aktiv BOOLEAN NOT NULL DEFAULT TRUE
);


ALTER TABLE kontoer ADD COLUMN mva_kode_guid CHAR(32);
ALTER TABLE kontoer ADD CONSTRAINT fk_mva_kode FOREIGN KEY(mva_kode_guid) REFERENCES mva_koder(guid) ON DELETE RESTRICT;

CREATE TABLE MVA_linjer(
	guid CHAR(32) PRIMARY KEY,
	transaksjon_guid CHAR(32) NOT NULL CONSTRAINT fk_mva_linjer_transaksjon_guid REFERENCES transaksjoner(guid),
	mva_kode_guid CHAR(32) NOT NULL CONSTRAINT fk_mva_linjer_mva_kode_guid REFERENCES mva_koder(guid),
	grunnlag_teller BIGINT NOT NULL,
	grunnlag_nevner BIGINT NOT NULL DEFAULT 100 CHECK(grunnlag_nevner > 0),
	mva_belop_teller BIGINT NOT NULL,
	mva_belop_nevner BIGINT DEFAULT 100 CHECK(mva_belop_nevner > 0)
);


CREATE OR REPLACE FUNCTION Transaksjoner_Update_Timestamp()
RETURNS TRIGGER AS $$
BEGIN
	NEW.registreringsdato := CURRENT_TIMESTAMP;
	NEW.posteringsdato := CURRENT_TIMESTAMP;
	RAISE NOTICE 'Timestamp oppdatert fra % til %', OLD.registreringsdato, CURRENT_TIMESTAMP;
	
	RETURN NEW;
END;

$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION Valuta_Update_Timestamp()
RETURNS TRIGGER AS $$
BEGIN
	NEW.dato := CURRENT_TIMESTAMP;
	RAISE NOTICE 'Timestamp oppdatert på valuter fra % til %', OLD.dato, CURRENT_TIMESTAMP;
	
	RETURN NEW;
END;

$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_oppdater_timestamp_trans BEFORE UPDATE ON transaksjoner FOR EACH ROW EXECUTE FUNCTION Transaksjoner_Update_Timestamp();
CREATE TRIGGER trg_oppdater_timestamp_val BEFORE UPDATE ON Valutakurser FOR EACH ROW EXECUTE FUNCTION Valuta_Update_Timestamp();

CREATE INDEX idx_kontoer_bok_guid ON kontoer(bok_guid);
CREATE INDEX idx_kontoer_kontonummer ON kontoer(kontonummer);
CREATE INDEX idx_kontoer_overordnet_guid ON kontoer(overordnet_guid);
CREATE INDEX idx_mva_linjer_transaksjon_guid ON MVA_linjer(transaksjon_guid);
CREATE INDEX idx_posteringer_konto_guid ON posteringer(konto_guid);
CREATE INDEX idx_posteringer_transaksjon_guid ON posteringer(transaksjon_guid);
CREATE INDEX idx_transaksjoner_bok_guid ON transaksjoner(bok_guid);
CREATE INDEX idx_transaksjoner_periode_guid ON transaksjoner(periode_guid);
CREATE INDEX idx_transaksjoner_posteringsdato ON transaksjoner(posteringsdato);

COMMENT ON TABLE kontoer IS 'Hierarkisk kontoplan. som kombinerer kontonummer og kontoklasse.';
COMMENT ON COLUMN kontoer.guid IS 'Primærnøkkel.';
COMMENT ON COLUMN kontoer.bok_guid IS 'Fremmednøkkel til Bøker.';
COMMENT ON COLUMN kontoer.overordnet_guid IS 'Bruker denne til å gjøre SELF-JOINS for å jobbe med rekursiv og hierarki';
COMMENT ON COLUMN kontoer.valuta_guid IS 'Fremmednøkkel til Valutaer: fra tabellen Valutaer';
COMMENT ON COLUMN kontoer.kontonummer IS '4-sifret kontonummer kan være mellom (1000-9999). er unik siden man kan ikke ha samme kontonummer';
COMMENT ON COLUMN kontoer.kontoklasse IS 'Fremmednøkkel til Kontoklasser fra kontoklasse tabellen  kan bare være mellom (1–8).';
COMMENT ON COLUMN kontoer.gnucash_type IS 'GnuCash-typen';
COMMENT ON COLUMN kontoer.er_placeholder IS 'Om det er en forelder til flere kontoer normalt false, kan ikke posteres på.';
COMMENT ON COLUMN kontoer.navn IS 'Kontonavnet, f.eks. Bankinnskudd. Ikke NULL.';
COMMENT ON COLUMN kontoer.beskrivelse IS 'Beskrivelse av kontotype.';
COMMENT ON COLUMN kontoer.er_skjult IS 'Om kontoen kan skjules Standardverdien er FALSE.';
COMMENT ON COLUMN kontoer.mva_pliktig IS 'Følger denne tabellen norske lover om mer verdi normalt false';
COMMENT ON COLUMN kontoer.mva_kode_guid IS 'Fremmednøkkel til MVA-koder fra MVA_koder tabellen: viser oss hvilken kode kontoen følger.';

COMMENT ON TABLE transaksjoner IS 'Viser oss bilagsdato og når transaksjonen ble gjort med hvilke valuter';
COMMENT ON COLUMN transaksjoner.guid IS 'Primærnøkkel.';
COMMENT ON COLUMN transaksjoner.bok_guid IS 'Fremmednøkkel til Booker fra Booker tabellen.';
COMMENT ON COLUMN transaksjoner.valuta_guid IS 'Fremmednøkkel til Valutaer fra Valutaer tabellen. transaksjonens hovedvaluta. ';
COMMENT ON COLUMN transaksjoner.bilagsnummer IS 'Bilagsnummeret sin identifaktor brukes til å henvise til kvittering f.eks';
COMMENT ON COLUMN transaksjoner.bilagsdato IS 'Datoen på det Bilagsnummeret når den ble opprettet';
COMMENT ON COLUMN transaksjoner.posteringsdato IS 'Når transaksjonen blir jobbet på eller settet inn i systemet.';
COMMENT ON COLUMN transaksjoner.registreringsdato IS 'Når Transaksjonen ble registrert i systemet.';
COMMENT ON COLUMN transaksjoner.beskrivelse IS 'Beksrivelse av transaksjon';
COMMENT ON COLUMN transaksjoner.kilde IS 'Hvordan ble transaksjonen opprettet: manuell, import, planlagt. normalt så blir den manuellt plassert inn';
COMMENT ON COLUMN transaksjoner.periode_guid IS '	Fremmednøkkel til Regnskapsperioder fra Regnskapsperioder tabellen. ';

COMMENT ON TABLE regnskapsperioder IS 'Status på hvordan vi gjør det i ulike månder';
COMMENT ON COLUMN regnskapsperioder.guid IS 'Primærnøkkel.';
COMMENT ON COLUMN regnskapsperioder.bok_guid IS 'Fremmednøkkel til Booker.';
COMMENT ON COLUMN regnskapsperioder.navn IS 'Navn på perioden altså månden vi jobber med.';
COMMENT ON COLUMN regnskapsperioder.fra_dato IS 'startdato av månden.';
COMMENT ON COLUMN regnskapsperioder.til_dato IS 'sluttdato av månden.';
COMMENT ON COLUMN regnskapsperioder.status IS 'Sjekker statusen på transaksjon altså om den er åpen lukket eller låst';

COMMENT ON TABLE booker IS 'Regnskapsboken';
COMMENT ON COLUMN booker.guid IS 'Primærnøkkel.';
COMMENT ON COLUMN booker.navn IS 'Navnet på regnskapsboken.';
COMMENT ON COLUMN booker.organisasjonsnr IS 'Organisasjonsnummeret er 9 siffer.';
COMMENT ON COLUMN booker.adresse IS 'Adressen på organisasjonen.';
COMMENT ON COLUMN booker.regnskapsaar IS 'Hvilket år det er';
COMMENT ON COLUMN booker.rot_konto_guid IS 'Rotkontoen i kontohierarkiet. Fremmednøkkel til kontoer fra kontoer tabellen viser oss hierarkiet og rekursiv av kontoen.';

COMMENT ON TABLE kontoklasser IS 'De 8 ulike formene for kontoklasser';
COMMENT ON COLUMN kontoklasser.klasse_nr IS 'Primærnøkkel. kan bare være max 8 forsjellige klasser i denne databasen';
COMMENT ON COLUMN kontoklasser.navn IS 'Navnet på klassen, er unik.';
COMMENT ON COLUMN kontoklasser.type_klasse IS 'Viser oss hvilken type det er mellom balanse og resultat.';
COMMENT ON COLUMN kontoklasser.normal_saldo IS 'Viser oss hvilken side klassen går mot enten debit eller kreditt.';
COMMENT ON COLUMN kontoklasser.beskrivelse IS 'Hva blir klassen brukt for';

COMMENT ON TABLE valutakurser IS 'Nåværende verdi av valutkurser';
COMMENT ON COLUMN valutakurser.guid IS 'Primærnøkkel.';
COMMENT ON COLUMN valutakurser.fra_valuta_guid IS '	Fremmednøkkel til Valutaer fra Valutaer tabellen: Hvilken valut skal vi konverte fra.';
COMMENT ON COLUMN valutakurser.til_valuta_guid IS 'Fremmednøkkel til Valutaer fra Valutaer tabellen: til våres valut normalt NOK';
COMMENT ON COLUMN valutakurser.dato IS 'Tidspunktet for når kursen ble bytte for.';
COMMENT ON COLUMN valutakurser.kurs_kilde IS 'Hvor kom veriden av valutene fra';
COMMENT ON COLUMN valutakurser.type_kurs IS ' Har 4 forskjellige type kurser: last (siste), bid (kjøp), ask (salg), nav (for fond).';
COMMENT ON COLUMN valutakurser.kurs_teller IS 'Telleren for å kalkulere om';
COMMENT ON COLUMN valutakurser.kurs_nevner IS 'Nevner for å kalkulere om kan ikke være null. Standard verdi er 100';

COMMENT ON TABLE valutaer IS '(NOK, USD, EUR)';
COMMENT ON COLUMN valutaer.guid IS 'Primærnøkkel';
COMMENT ON COLUMN valutaer.kode IS 'Forkortelse av hvilken kurs det er snakk om f.eks NOK eller EUR er UNIQUE';
COMMENT ON COLUMN valutaer.navn IS 'Fulle navnet kursen';
COMMENT ON COLUMN valutaer.desimaler IS 'Antall desimaler valutaen er her bruker vi 12,2 så vi kan få minst 0.02 og høyeste er 10millioner, stanardverdi er 100.';
COMMENT ON COLUMN valutaer.hent_kurs_flag IS 'Skal systemet hente kursen selv normal verdi er false.';
COMMENT ON COLUMN valutaer.kurs_kilde IS 'Hvor har vi hentet kursen fra.';


COMMENT ON TABLE posteringer IS 'Hvordan regnestykket ser ut ';
COMMENT ON COLUMN posteringer.guid IS 'Primærnøkkel.';
COMMENT ON COLUMN posteringer.transaksjon_guid IS 'Fremmednøkkel til Transaksjoner fra Transaksjoner tabellen.';
COMMENT ON COLUMN posteringer.konto_guid IS 'Fremmednøkkel til kontoer fra Kontoer tabellen.';
COMMENT ON COLUMN posteringer.tekst IS 'Detaljert opplysning om posteringen.';
COMMENT ON COLUMN posteringer.handling IS 'Hvilken type er det? lønn kjøp eller salg';
COMMENT ON COLUMN posteringer.avstemmingsstatus IS 'Statusen om posteringen sin status er stemt på n (ikke avstemt), c (klarert), y (avstemt mot bank). Standardverdien er "n".';
COMMENT ON COLUMN posteringer.avstemmingsdato IS 'Dato for bankavstemming.';
COMMENT ON COLUMN posteringer.belop_teller IS 'Beløpet i transaksjonens sin valuta som blir brukt som teller. Positivt = debet, negativt = kredit.';
COMMENT ON COLUMN posteringer.belop_nevner IS 'Nevner for beløpet. normal verdien er 100.';
COMMENT ON COLUMN posteringer.antall_teller IS 'Antall enheter det er snakk om normal verdi er 0.';
COMMENT ON COLUMN posteringer.antall_nevner IS 'Nevner for antallet hjelper til med å brøken, normal verdi er 1.';


COMMENT ON TABLE mva_koder IS 'koder og satser i Norge';
COMMENT ON COLUMN mva_koder.guid IS 'Primærnøkkel.';
COMMENT ON COLUMN mva_koder.kode IS 'MVA-koden den er unik';
COMMENT ON COLUMN mva_koder.navn IS 'Navn på koden og hva den gjør';
COMMENT ON COLUMN mva_koder.type_mva IS 'Tilstanden til koden den kan være tre ulike variabler UTGAAENDE, INNGAAENDE, INGEN.';
COMMENT ON COLUMN mva_koder.sats_teller IS 'Hvor mye prosent sats skal telleren ha i prosent.';
COMMENT ON COLUMN mva_koder.sats_nevner IS 'Normal nevner normal verdi er 100 for å gjøre den om til prosent regning';
COMMENT ON COLUMN mva_koder.mva_konto_guid IS 'Fremmednøkkel til kontoer fra konto-tabellen: Hvilken konto skal beløpet bli sendt til';
COMMENT ON COLUMN mva_koder.aktiv IS 'Om koden er i aktiv bruk normalt TRUE';

COMMENT ON TABLE MVA_linjer IS 'Hvor mye per transaksjon med mva';
COMMENT ON COLUMN MVA_linjer.guid IS 'Primærnøkkel.';
COMMENT ON COLUMN MVA_linjer.transaksjon_guid IS '	Fremmednøkkel til Transaksjoner tabellen for å knytte transaksjon med mva.';
COMMENT ON COLUMN MVA_linjer.mva_kode_guid IS 'Fremmednøkkel til MVA-koder for å koble sammen hvilken mva det er snakk om';
COMMENT ON COLUMN MVA_linjer.grunnlag_teller IS 'Telleren for grunnlaget';
COMMENT ON COLUMN MVA_linjer.grunnlag_nevner IS 'Nevner for grunnlaget samme som vanlige nevnere med å dele på 100 vis ingenting annet er spesifisert. ';
COMMENT ON COLUMN MVA_linjer.mva_belop_teller IS 'Beløpet til MVA som går i et med grunnlaget for å finne prisen';
COMMENT ON COLUMN MVA_linjer.mva_belop_nevner IS 'Nevner for MVA-beløpet.';
