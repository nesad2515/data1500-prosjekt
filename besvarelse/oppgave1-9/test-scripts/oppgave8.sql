BEGIN;

INSERT INTO Transaksjoner 
	(guid, bok_guid, valuta_guid, bilagsnummer, bilagsdato, posteringsdato, registreringsdato, beskrivelse, periode_guid) 
	VALUES 
		('GUIDFOROPPGAVE8DENNESKALSLETTES1', 
		(SELECT guid FROM Booker LIMIT 1), 
		(SELECT guid FROM Valutaer WHERE kode = 'NOK'), 
		'TEST for oppgave 8',
		CURRENT_DATE,
		CURRENT_TIMESTAMP,
		CURRENT_TIMESTAMP,
		'Test for Rollback funksjon',
		(SELECT guid FROM Regnskapsperioder WHERE navn = 'Mars 2026')
		);
		
INSERT INTO Posteringer 
	(guid, transaksjon_guid, konto_guid, belop_teller) 
	VALUES 
	('GUIDFOROPPGAVE8POSTERINGERSLETTE',
	'GUIDFOROPPGAVE8DENNESKALSLETTES1',
	(SELECT guid FROM Kontoer WHERE kontonummer = 1920),
	1000
	);

-- Verifiser at dataene er synlige innenfor transaksjonen
SELECT * FROM Transaksjoner WHERE guid = 'GUIDFOROPPGAVE8DENNESKALSLETTES1'; -- Skal returnere 1 rad

ROLLBACK;

-- Verifiser at dataene er borte etter ROLLBACK
SELECT * FROM Transaksjoner WHERE guid = 'GUIDFOROPPGAVE8DENNESKALSLETTES1'; -- Skal returnere 0 rader