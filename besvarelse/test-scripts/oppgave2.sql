BEGIN;

TRUNCATE TABLE 
    Posteringer, 
    Transaksjoner, 
    Regnskapsperioder, 
    MVA_koder, 
    Kontoer, 
    Booker, 
    Valutakurser, 
    Valutaer, 
    kontoklasser 
RESTART IDENTITY CASCADE;

INSERT INTO kontoklasser
	(klasse_nr, navn, type_klasse, normal_saldo, beskrivelse)
	VALUES
	(1,'Eiendeler', 'BALANSE', 'DEBET', 'Det bedriften eier (penger, utstyr, kundefordringer)'),
	(2, 'Egenkapital og gjeld', 'BALANSE', 'KREDIT', 'Det bedriften skylder og eiernes andel av bedriften'),
	(3, 'Salgsinntekter og driftsinntekter', 'RESULTAT', 'KREDIT', 'inntekter fra salg av varer og tjenester'),
	(4, 'Varekostander', 'RESULTAT', 'DEBET', 'Varen sine kostnader'),
	(5, 'Lønnskostnad', 'RESULTAT', 'DEBET', 'Lønn til personal'),
	(6, 'Driftskostnader 1', 'RESULTAT', 'DEBET', 'Rekvisita'),
	(7, 'Driftskostnader 2', 'RESULTAT', 'DEBET', 'Administrasjon/markedsføring'),
	(8, 'Finansposter', 'RESULTAT', 'DEBET', 'Bedriftens inntekter og kostnader knyttet til kapital, renter og investeringer');
	
INSERT INTO Valutaer
	(guid, kode, navn, desimaler, hent_kurs_flag, kurs_kilde)
	VALUES
	('47e7d6a792444983949987679805908b','NOK', 'Norske Kroner', 2, 0, 'Norges-bank'),
	('7c59828608ca46c6947671239016922d', 'SEK', 'Svenske Kroner', 2, 0, 'Norges-bank'),
	('d51680a6b72a4209939529948408107c', 'USD', 'United States Dollars', 2, 0, 'Norges-bank');
	
INSERT INTO Valutakurser
	(guid, fra_valuta_guid, til_valuta_guid, dato, kurs_kilde, type_kurs, kurs_teller, kurs_nevner)
	VALUES
	('f812850901da4216892348560371510e', 'd51680a6b72a4209939529948408107c', '47e7d6a792444983949987679805908b', '2026-02-08', 'Norges-bank', 'bid', 1050, 100),
	('a029384756bc4a3d9e8f1a2b3c4d5e6f', '7c59828608ca46c6947671239016922d', '47e7d6a792444983949987679805908b', '2026-03-02', 'Norges-bank', 'last', 102, 100),
	('e91d8273645a4f3e2d1c0b9a87654321', '7c59828608ca46c6947671239016922d', '47e7d6a792444983949987679805908b', '2026-03-27', 'Norges-bank', 'last', 98, 100);
	
INSERT INTO Booker
	(guid, navn, organisasjonsnr, adresse, regnskapsaar, rot_konto_guid)
	VALUES
	('b123456789abcdef0123456789abcdef', 'DATA1500 Konsulnt AS', '123456789', 'Storgata 9B', '2026-01-01', NULL);
	
INSERT INTO Kontoer
	(guid, bok_guid, overordnet_guid, valuta_guid, kontonummer, kontoklasse, gnucash_type, navn, beskrivelse, er_placeholder, er_skjult)
	VALUES
	('HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE', 'b123456789abcdef0123456789abcdef', NULL, '47e7d6a792444983949987679805908b', NULL, 1, 'ROOT', 'Hoved ROT', 'Hoved roten brukes til hierarki', TRUE, TRUE),
	('550e8400e29b41d4a716446655440001', 'b123456789abcdef0123456789abcdef', 'HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE', '47e7d6a792444983949987679805908b', NULL, 1, 'ASSETS', 'Eiendeler ROT', '1 - Eiendeler', TRUE, FALSE),
	('550e8400e29b41d4a716446655440002', 'b123456789abcdef0123456789abcdef', 'HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE', '47e7d6a792444983949987679805908b', NULL, 2, 'LIABILITY', 'Gjeld og Egenkapital ROT', 'Hoved roten brukes til hierarki', TRUE, FALSE),
	('550e8400e29b41d4a716446655440003', 'b123456789abcdef0123456789abcdef', 'HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE', '47e7d6a792444983949987679805908b', NULL, 3, 'INCOME', 'Salgsinntekter', 'INCOME klasse 3', TRUE, FALSE),
	('550e8400e29b41d4a716446655440004', 'b123456789abcdef0123456789abcdef', 'HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE', '47e7d6a792444983949987679805908b', NULL, 4, 'EXPENSE', 'Varekostander', 'Vare kostnader klasse 4', TRUE, FALSE),
	('550e8400e29b41d4a716446655440005', 'b123456789abcdef0123456789abcdef', 'HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE', '47e7d6a792444983949987679805908b', NULL, 5, 'EXPENSE', 'Personale Kostnader', 'Lønn f.eks Klasse 5', TRUE, FALSE),
	('550e8400e29b41d4a716446655440006', 'b123456789abcdef0123456789abcdef', 'HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE', '47e7d6a792444983949987679805908b', NULL, 6, 'EXPENSE', 'Driftskostnader I', 'driftsinntekter Klasse 6', TRUE, FALSE),
	('550e8400e29b41d4a716446655440007', 'b123456789abcdef0123456789abcdef', 'HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE', '47e7d6a792444983949987679805908b', NULL, 7, 'EXPENSE', 'Driftskostnader II', 'driftsinntekter II Klasse 7', TRUE, FALSE),
	('550e8400e29b41d4a716446655440008', 'b123456789abcdef0123456789abcdef', 'HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE', '47e7d6a792444983949987679805908b', NULL, 8, 'EXPENSE', 'Finans', 'Skatt osv Klasse 8', TRUE, FALSE);
	
	
	
INSERT INTO Kontoer
	(guid, bok_guid, overordnet_guid, valuta_guid, kontonummer, kontoklasse, gnucash_type, navn, beskrivelse, mva_kode_guid)
	VALUES
	('c987654321fedcba0987654321fedcba', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440001', '47e7d6a792444983949987679805908b', 1920, 1, 'BANK', 'Bankinnskudd', 'Bedriften får en eiendel', NULL),
	('da72e1f0b9c84d7e8f1a2b3c4d5e6f7a', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440002', '47e7d6a792444983949987679805908b', 2000, 2, 'EQUITY', 'Akjsekapital', 'Bedriften sine aksjer', NULL),
	('e1f2a3b4c5d64e7f8a9b0c1d2e3f4a5b', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440006', '47e7d6a792444983949987679805908b', 6560, 6, 'EXPENSE', 'Rekvisita', 'Rekvisita for kontoret', NULL),
	('f5e4d3c2b1a04f9e8d7c6b5a43210fed', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440002', '47e7d6a792444983949987679805908b', 2710, 2, 'LIABILITY', 'Inngående MVA Høy sats', 'Inngående MVA', NULL),
	('0a1b2c3d4e5f4a1b2c3d4e5f6a7b8c9d', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440002', '47e7d6a792444983949987679805908b', 2400, 2, 'ACCOUNTS_PAYABLE', 'Leverandør Gjeld', 'MVA fra leverandøren', NULL),
	('11223344556644778899aabbccddeeff', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440001', '47e7d6a792444983949987679805908b', 1500, 1, 'ACCOUNTS_RECEIVABLE', 'Kundefordringer', 'Hva kunden skylder oss', NULL),
	('ffee0099887744665544332211aabbcc', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440003', '47e7d6a792444983949987679805908b', 3100, 3, 'INCOME', 'Salgsinntekter, Tjenester', 'Hva vi har gjort', NULL),
	('a1b2c3d4e5f6478987654321abcdef01', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440002', '47e7d6a792444983949987679805908b', 2700, 2, 'LIABILITY', 'Utgående MVA høy sats', 'GJELD', NULL),
	('d4e5f6a7b8c940121098765432fedcba', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440005', '47e7d6a792444983949987679805908b', 5000, 5, 'EXPENSE', 'Lønn til ansatte', 'Betaler de som jobber for oss', NULL),
	('18c9d0e1f2a344565432109876fedcba', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440002', '47e7d6a792444983949987679805908b', 2600, 2, 'LIABILITY', 'Forskuddstrekk', 'Hvor mye vi betaler i forskudd', NULL),
	('f2e3f4a5b6c748909876543210fedcba', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440005', '47e7d6a792444983949987679805908b', 5400, 5, 'EXPENSE', 'Arbeidsgiveravgift', 'Hvor mye vi arbeidsgiveren tar er seperat', NULL),
	('14a5b6c7d8e940121098765432fedcba', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440002', '47e7d6a792444983949987679805908b', 2780, 2, 'LIABILITY', 'Skyldig arbeidsgiveravgift', 'Avgift', NULL),
	('36c7d8e9f0a142343210987654fedcba', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440001', '47e7d6a792444983949987679805908b', 1350, 1, 'STOCK', 'Askjer i utenlandske selskaper', 'Hvor mye vi eier i utlandet', NULL),
	('b4e5f6a7b8c940121098765432fedcba', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440002', '47e7d6a792444983949987679805908b', 2740, 2, 'LIABILITY', 'Oppgjørskonto MVA', 'Konto', NULL),
	('54c5d6e7f8a940121098765432fedcba', 'b123456789abcdef0123456789abcdef', '550e8400e29b41d4a716446655440008', '47e7d6a792444983949987679805908b', 8160, 8, 'EXPENSE', 'Valutatap (Disagio)', 'Hvor mye vi tapte', NULL);

	
UPDATE Kontoer SET mva_pliktig = TRUE WHERE kontonummer IN (3100, 6560, 2700, 2710);	
	
UPDATE Booker
	SET rot_konto_guid = 'HOVED_ROT_BLIR_BRUKT_FOR_INDEKSE';
	
INSERT INTO MVA_koder
	(guid, kode, navn, type_mva, sats_teller, sats_nevner, mva_konto_guid)
	VALUES
	('MVAKodeFraScenario2Utgaaende', '1', 'Utgående MVA, Høy sats(25%)', 'UTGAAENDE', 25, 100, 'a1b2c3d4e5f6478987654321abcdef01'),
	('MVAKodeFraScenario2Inngående', '3', 'Inngående MVA, Høy sats(25%)','INNGAAENDE', 25, 100, 'f5e4d3c2b1a04f9e8d7c6b5a43210fed');

UPDATE Kontoer
	SET mva_kode_guid = 'MVAKodeFraScenario2Utgaaende'
	WHERE guid = 'ffee0099887744665544332211aabbcc';
	
UPDATE Kontoer
	SET mva_kode_guid = 'MVAKodeFraScenario2Inngående'
	WHERE guid = 'e1f2a3b4c5d64e7f8a9b0c1d2e3f4a5b';
	
	
INSERT INTO Regnskapsperioder
	(guid, bok_guid, navn, fra_dato, til_dato)
	VALUES
	('a1b2c3d4e5f6478987654321abcd0001', 'b123456789abcdef0123456789abcdef', 'Januar 2026', '2026-01-01', '2026-01-31'),
	('b2c3d4e5f6a748909876543210fe0002', 'b123456789abcdef0123456789abcdef', 'Februar 2026', '2026-02-01', '2026-02-28'),
	('c3d4e5f6a7b849010987654321ab0003', 'b123456789abcdef0123456789abcdef', 'Mars 2026', '2026-03-01', '2026-03-31'),
	('d4e5f6a7b8c940121098765432fe0004', 'b123456789abcdef0123456789abcdef', 'April 2026', '2026-04-01', '2026-04-30'),
	('e5f6a7b8c9d041232109876543ab0005', 'b123456789abcdef0123456789abcdef', 'Mai 2026', '2026-05-01', '2026-05-31'),
	('f6a7b8c9d0e142343210987654fe0006', 'b123456789abcdef0123456789abcdef', 'Juni 2026', '2026-06-01', '2026-06-30'),
	('0b1c2d3e4f5a43456543210987ab0007', 'b123456789abcdef0123456789abcdef', 'Juli 2026', '2026-07-01', '2026-07-31'),
	('1c2d3e4f5a6b44567654321098fe0008', 'b123456789abcdef0123456789abcdef', 'August 2026', '2026-08-01', '2026-08-31'),
	('2d3e4f5a6b7c45678765432109ab0009', 'b123456789abcdef0123456789abcdef', 'September 2026', '2026-09-01', '2026-09-30'),
	('3e4f5a6b7c8d46789876543210fe0010', 'b123456789abcdef0123456789abcdef', 'Oktober 2026', '2026-10-01', '2026-10-31'),
	('4f5a6b7c8d9e47890987654321ab0011', 'b123456789abcdef0123456789abcdef', 'November 2026', '2026-11-01', '2026-11-30'),
	('5a6b7c8d9e0f48901098765432fe0012', 'b123456789abcdef0123456789abcdef', 'Desember 2026', '2026-12-01', '2026-12-31'),
	('5a6b7c8d9e0f48901098765432fe0000', 'b123456789abcdef0123456789abcdef', 'Januar 2024', '2024-01-01', '2024-01-01');
	
DO $$
	DECLARE
		tx_guid CHAR(32);
		tx_bok_guid CHAR(32) := 'b123456789abcdef0123456789abcdef';
		tx_valuta_guid_nok CHAR(32) := '47e7d6a792444983949987679805908b';
		tx_valuta_guid_usd CHAR(32) := 'd51680a6b72a4209939529948408107c';
		tx_valuta_guid_sek CHAR(32) := '7c59828608ca46c6947671239016922d';
		tx_bilagsnummer TEXT;
		tx_bilagsdato DATE;
		tx_beskrivelse TEXT;
		tx_periode_guid_jan CHAR(32) := 'a1b2c3d4e5f6478987654321abcd0001';
		tx_periode_guid_feb CHAR(32) := 'b2c3d4e5f6a748909876543210fe0002';
		tx_periode_guid_mars CHAR(32) := 'c3d4e5f6a7b849010987654321ab0003';
	BEGIN
		tx_guid := REPLACE(gen_random_uuid()::text, '-', '');
		tx_bilagsnummer := 'Faktura 1';
		tx_bilagsdato := '2026-01-01';
		tx_beskrivelse := '200000 i aksjekapital, pengene settes inn i bedriftens bankkonto.';
		
		
		INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(tx_guid, tx_bok_guid, tx_valuta_guid_nok, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_jan);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'c987654321fedcba0987654321fedcba', 'Bankinnskudd kjøp av eiendeler', 'Stiftelse', 'y', tx_bilagsdato, 20000000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'da72e1f0b9c84d7e8f1a2b3c4d5e6f7a', 'Egenkapital og gjeld for kjøp av eiendeler', 'Stiftelse', 'c', tx_bilagsdato, -20000000);
		
		tx_guid := REPLACE(gen_random_uuid()::text, '-', '');
		tx_bilagsnummer := 'Faktura 2';
		tx_bilagsdato := '2026-01-10';
		tx_beskrivelse := 'brukte 4375 NOK inkl MVA Inngående 25%, til å kjøpe kontorekvisita betales om 30 dager.';
		
		INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(tx_guid, tx_bok_guid, tx_valuta_guid_nok, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_jan);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'e1f2a3b4c5d64e7f8a9b0c1d2e3f4a5b', 'Rekvisita kjøp av stoler', 'Kjøp', 'c', tx_bilagsdato, 350000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'f5e4d3c2b1a04f9e8d7c6b5a43210fed', 'inngående MVA', 'Kjøp', 'c', tx_bilagsdato, 87500);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, '0a1b2c3d4e5f4a1b2c3d4e5f6a7b8c9d', 'Leverandørgjeld', 'Kjøp', 'c', tx_bilagsdato, -437500);
		
		INSERT INTO MVA_linjer
		(guid, transaksjon_guid, mva_kode_guid, grunnlag_teller, mva_belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'MVAKodeFraScenario2Inngående', 350000, 87500);
		
		tx_guid := REPLACE(gen_random_uuid()::text, '-', '');
		tx_bilagsnummer := 'Faktura 3';
		tx_bilagsdato := '2026-01-20';
		tx_beskrivelse := 'Fakturere en kunde(TechNord AS) med Utgående MVA 25% 62500 NOK.';
		
		INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(tx_guid, tx_bok_guid, tx_valuta_guid_nok, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_jan);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, '11223344556644778899aabbccddeeff', 'Salg av tjenester til TechNord AS Eiendeler', 'Salg', 'c', tx_bilagsdato, 6250000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'ffee0099887744665544332211aabbcc', 'Salgsinntekter for salg av tjenester', 'Salg', 'y', tx_bilagsdato, -5000000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'a1b2c3d4e5f6478987654321abcdef01', 'Utgående MVA av salg av tjenester', 'Salg', 'c', tx_bilagsdato, -1250000);
		
		INSERT INTO MVA_linjer
		(guid, transaksjon_guid, mva_kode_guid, grunnlag_teller, mva_belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'MVAKodeFraScenario2Utgaaende', 5000000, -1250000);
		
		tx_guid := REPLACE(gen_random_uuid()::text, '-', '');
		tx_bilagsnummer := 'Faktura 4';
		tx_bilagsdato := '2026-02-01';
		tx_beskrivelse := 'Utbetaling av lønn og føring av avgifter';
		
		INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(tx_guid, tx_bok_guid, tx_valuta_guid_nok, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_feb);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'd4e5f6a7b8c940121098765432fedcba', 'Lønn til ansatte', 'Lønn', 'c', tx_bilagsdato, 4500000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'c987654321fedcba0987654321fedcba', 'Bankinnskudd', 'Lønn', 'y', tx_bilagsdato, -3300000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, '18c9d0e1f2a344565432109876fedcba', 'Forskuddstrekk', 'Lønn', 'y', tx_bilagsdato, -1200000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'f2e3f4a5b6c748909876543210fedcba', 'Arbeidsgiveravgift/Lønnskostnad', 'Lønn', 'y', tx_bilagsdato, 634500);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, '14a5b6c7d8e940121098765432fedcba', 'Skyldig Arbeidsgiveravgift', 'Lønn', 'c', tx_bilagsdato, -634500);
		
		
		tx_guid := REPLACE(gen_random_uuid()::text, '-', '');
		tx_bilagsnummer := 'Faktura 5';
		tx_bilagsdato := '2026-02-20';
		tx_beskrivelse := 'TechNord AS betaler oss for salg av tjeneste';
		
		INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(tx_guid, tx_bok_guid, tx_valuta_guid_nok, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_feb);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'c987654321fedcba0987654321fedcba', 'Bankinnskudd', 'Innbeatling', 'y', tx_bilagsdato, 6250000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, '11223344556644778899aabbccddeeff', 'Kundefordringer', 'Innbetaling', 'y', tx_bilagsdato, -6250000);
		
		tx_guid := REPLACE(gen_random_uuid()::text, '-', '');
		tx_bilagsnummer := 'Faktura 6';
		tx_bilagsdato := '2026-02-09';
		tx_beskrivelse := 'Kjøpte aksjer i Apple for 1750 USD altså 10 Aksjer = 18375 NOK';
		
		INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(tx_guid, tx_bok_guid, tx_valuta_guid_usd, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_feb);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller, antall_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, '36c7d8e9f0a142343210987654fedcba', 'Aksjer i utenlandske selskaper', 'Kjøp', 'y', tx_bilagsdato, 1837500, 10);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'c987654321fedcba0987654321fedcba', 'Bankinnskudd siden vi ikke har tapt penger', 'Kjøp', 'y', tx_bilagsdato, -1837500);
		
		tx_guid := REPLACE(gen_random_uuid()::text, '-', '');
		tx_bilagsnummer := 'Faktura 7';
		tx_bilagsdato := '2026-03-01';
		tx_beskrivelse := 'MVA-oppgjør og innbetaling til staten';
		
		INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(tx_guid, tx_bok_guid, tx_valuta_guid_nok, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_mars);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'a1b2c3d4e5f6478987654321abcdef01', 'Betaler Utgående MVA med høy sats', 'Betaling', 'c', tx_bilagsdato, 1250000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'f5e4d3c2b1a04f9e8d7c6b5a43210fed', 'Inngående MVA med høy sats', 'Betaling', 'y', tx_bilagsdato, -87500);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'b4e5f6a7b8c940121098765432fedcba', 'Oppgjørskonto med MVA', 'Betaling', 'y', tx_bilagsdato, -1162500);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'c987654321fedcba0987654321fedcba', 'Bankinnskudd', 'Betaling', 'c', tx_bilagsdato, 0);
		
		tx_guid := REPLACE(gen_random_uuid()::text, '-', '');
		tx_bilagsnummer := 'Faktura 8';
		tx_bilagsdato := '2026-03-10';
		tx_beskrivelse := 'Faktura for salg av tjenester til et Svensk firma for 50000 SEK';
		
		INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(tx_guid, tx_bok_guid, tx_valuta_guid_sek, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_mars);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, '11223344556644778899aabbccddeeff', 'Kundefordringer', 'Fakturering', 'y', tx_bilagsdato, 5100000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'ffee0099887744665544332211aabbcc', 'Salgsinntekter', 'Fakturering', 'c', tx_bilagsdato, -5100000);
		
		tx_guid := REPLACE(gen_random_uuid()::text, '-', '');
		tx_bilagsnummer := 'Faktura 9';
		tx_bilagsdato := '2026-03-28';
		tx_beskrivelse := 'Betalt faktura for salg av tjenester til et Svensk firma for 49000 NOK, med valutatap 2000 NOK føres mot Konto 8160';

		INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(tx_guid, tx_bok_guid, tx_valuta_guid_nok, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_mars);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, 'c987654321fedcba0987654321fedcba', 'Bankinnskudd', 'Innbetaling', 'c', tx_bilagsdato, 4900000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, '54c5d6e7f8a940121098765432fedcba', 'Valutatap', 'Innbeatling', 'c', tx_bilagsdato, 200000);
		
		INSERT INTO Posteringer
		(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
		VALUES
		(REPLACE(gen_random_uuid()::text, '-', ''), tx_guid, '11223344556644778899aabbccddeeff', 'Kundefordringer', 'Innbeatling', 'c', tx_bilagsdato, -5100000);
	END $$;

	
UPDATE Regnskapsperioder
	SET status = 'LAAST'
	WHERE guid = 'a1b2c3d4e5f6478987654321abcd0001' OR guid = 'b2c3d4e5f6a748909876543210fe0002';
	
--For RLS
INSERT INTO Transaksjoner 
	(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, posteringsdato, registreringsdato, beskrivelse, kilde, periode_guid) 
	VALUES 
	(REPLACE(gen_random_uuid()::text, '-', ''), 'b123456789abcdef0123456789abcdef', '47e7d6a792444983949987679805908b', 'TEST FAKTURA', '2024-01-01', '2024-01-01', '2024-01-01', 'Test Faktura for RLS', 'manuell', '5a6b7c8d9e0f48901098765432fe0000');	
	
ROLLBACK;
	

	