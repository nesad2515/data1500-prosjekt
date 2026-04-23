BEGIN;

INSERT INTO Transaksjoner (guid, ...) VALUES (...);
INSERT INTO Posteringer (guid, transaksjon_guid, ...) VALUES (...);

-- Verifiser at dataene er synlige innenfor transaksjonen
SELECT * FROM Transaksjoner WHERE guid = ...; -- Skal returnere 1 rad

ROLLBACK;

-- Verifiser at dataene er borte etter ROLLBACK
SELECT * FROM Transaksjoner WHERE guid = ...; -- Skal returnere 0 rader