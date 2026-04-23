
--Scenario A en vellykket transaksjon

BEGIN;
	DO $$
		DECLARE
		tx_tran_guid CHAR(32);
		tx_bok_guid CHAR(32) := 'b123456789abcdef0123456789abcdef';
		tx_valuta_guid_nok CHAR(32) := '47e7d6a792444983949987679805908b';
		tx_bilagsnummer TEXT;
		tx_bilagsdato DATE;
		tx_beskrivelse TEXT;
		tx_periode_guid_mars CHAR(32) := 'c3d4e5f6a7b849010987654321ab0003';
		
		BEGIN
			tx_tran_guid := REPLACE(gen_random_uuid()::text, '-', '');
			tx_bilagsnummer := 'Faktura for oppgave 7';
			tx_bilagsdato := '2026-03-28';
			tx_beskrivelse := 'En faktura for oppgave 7, hvor vi skal vise hvordan BEGIN og COMMIT funker,';
			
			INSERT INTO Transaksjoner
			(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
			VALUES
			(tx_tran_guid, tx_bok_guid, tx_valuta_guid_nok, tx_bilagsnummer, tx_bilagsdato, tx_beskrivelse, tx_periode_guid_mars);
			
			INSERT INTO Posteringer
			(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
			VALUES
			(REPLACE(gen_random_uuid()::TEXT, '-', ''), tx_tran_guid, 'e1f2a3b4c5d64e7f8a9b0c1d2e3f4a5b', '6560 Konto DEBET oppgave om BEGIN og COMMIT', 'TEST', 'n', tx_bilagsdato, 200000),
			(REPLACE(gen_random_uuid()::TEXT, '-', ''), tx_tran_guid, 'f5e4d3c2b1a04f9e8d7c6b5a43210fed', '2710 Inngående MVA oppgave 7', 'TEST', 'n', tx_bilagsdato, 50000),
			(REPLACE(gen_random_uuid()::TEXT, '-', ''), tx_tran_guid, '0a1b2c3d4e5f4a1b2c3d4e5f6a7b8c9d', '2400 Leverandørgjeld på 2500 oppgave 7', 'TEST', 'n', tx_bilagsdato, -250000);
	END $$;
COMMIT;

SELECT * FROM Transaksjoner WHERE bilagsnummer = 'Faktura for oppgave 7';

--Scenario B en mislykket transaksjon

BEGIN;

DO $$
DECLARE
    -- Bevisst ugyldig: 32 tegn, men finnes ikke i Kontoer-tabellen
	v_ugyldig_guid CHAR(32) := 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF';
	-- de andre guid som man trenger for INSERT
	-- v_book_guid CHAR(32)
	-- ...
	v_tran_guid CHAR(32);
	v_bok_guid CHAR(32);
	v_valuta_guid_nok CHAR(32);
	v_bilagsnummer TEXT := 'B-2026-FEIL';
	v_bilagsdato DATE := '2026-03-27';
	v_beskrivelse TEXT := 'Ugyldig Transaksjon oppgave 7B';
	v_periode_guid CHAR(32);
BEGIN
-- Bruker select for å finne de nødvendige guid-er	
-- Bruk STRICT for å unngå feil hvis `select` returnerer ingen rader
-- SELECT guid INTO STRICT v_bok_guid FROM "Bøker" LIMIT 1; 
-- ...
	v_tran_guid := REPLACE(gen_random_uuid()::text, '-', '');
	SELECT guid INTO STRICT v_bok_guid FROM Booker LIMIT 1;
	SELECT guid INTO STRICT v_valuta_guid_nok FROM Valutaer WHERE guid = '47e7d6a792444983949987679805908b';
	SELECT guid INTO STRICT v_periode_guid FROM Regnskapsperioder WHERE navn = 'Mars 2026';
	
-- INSERT INTO "Transaksjoner" (guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato,
--         posteringsdato, beskrivelse, periode_guid) VALUES (...);			
	INSERT INTO Transaksjoner
		(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, beskrivelse, periode_guid)
		VALUES
		(v_tran_guid, v_bok_guid, v_valuta_guid_nok, v_bilagsnummer, v_bilagsdato, v_beskrivelse, v_periode_guid);
		
-- INSERT INTO "Posteringer"
--        (guid, transaksjon_guid, konto_guid, tekst,
--         belop_teller, belop_nevner, antall_teller, antall_nevner)
--    VALUES (...);
	INSERT INTO Posteringer
			(guid, transaksjon_guid, konto_guid, tekst, handling, avstemmingsstatus, avstemmingsdato, belop_teller)
			VALUES
			(REPLACE(gen_random_uuid()::TEXT, '-', ''), v_tran_guid, v_ugyldig_guid, 'Ugyldig Transaksjon for oppgave 7', 'TEST', 'n', v_bilagsdato, 250000);
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
END $$;

ROLLBACK;

\echo '--- Verifisering etter ROLLBACK ---'
-- Bekreft at den feilede transaksjonen IKKE finnes
SELECT
    CASE WHEN COUNT(*) = 0
         THEN 'OK: B-2026-FEIL finnes IKKE i databasen (ROLLBACK virket)'
         ELSE 'FEIL: B-2026-FEIL ble lagret til tross for ROLLBACK!'
    END AS rollback_status
FROM Transaksjoner
WHERE bilagsnummer = 'B-2026-FEIL';