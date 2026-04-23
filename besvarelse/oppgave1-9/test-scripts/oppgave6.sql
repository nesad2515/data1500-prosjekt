DROP OWNED BY regnskap_admin, revisor, regnskapsforer, les_tilgang;
DROP ROLE IF EXISTS regnskap_admin;
DROP ROLE IF EXISTS revisor;
DROP ROLE IF EXISTS regnskapsforer;
DROP ROLE IF EXISTS les_tilgang;

CREATE ROLE regnskap_admin;
GRANT CONNECT ON DATABASE regnskap TO regnskap_admin;
GRANT USAGE ON SCHEMA public TO regnskap_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO regnskap_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO regnskap_admin;

CREATE ROLE revisor;
GRANT CONNECT ON DATABASE regnskap TO revisor;
GRANT USAGE ON SCHEMA public TO revisor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO revisor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO revisor;

CREATE ROLE regnskapsforer;
GRANT CONNECT ON DATABASE regnskap TO regnskapsforer;
GRANT USAGE ON SCHEMA public TO regnskapsforer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO regnskapsforer;
GRANT INSERT, UPDATE ON TABLE Transaksjoner, Posteringer, MVA_linjer TO regnskapsforer;

CREATE ROLE les_tilgang; 
GRANT CONNECT ON DATABASE regnskap TO les_tilgang;
GRANT USAGE ON SCHEMA public TO les_tilgang;
GRANT SELECT ON TABLE Kontoer, Kontoklasser, Valutaer TO les_tilgang;

DROP ROLE IF EXISTS dba_ola;
DROP ROLE IF EXISTS revisor_kari;
DROP ROLE IF EXISTS bokforer_per;
DROP ROLE IF EXISTS ekstern_revisor;

CREATE ROLE dba_ola LOGIN PASSWORD '123'; 
GRANT regnskap_admin TO dba_ola;

CREATE ROLE revisor_kari LOGIN PASSWORD '123';
GRANT revisor TO revisor_kari;

CREATE ROLE bokforer_per LOGIN PASSWORD '123';
GRANT regnskapsforer TO bokforer_per;

CREATE ROLE ekstern_revisor LOGIN PASSWORD '123';
GRANT les_tilgang TO ekstern_revisor;

--Spørring mot skjema
SELECT grantee, table_catalog, table_name, privilege_type, is_grantable, with_hierarchy FROM information_schema.role_table_grants WHERE grantee = 'regnskap_admin' OR grantee = 'revisor' OR grantee = 'les_tilgang' OR grantee = 'regnskapsforer' ORDER BY grantee;

--Bokforer_per ikke kan slette fra Transaksjoner
SET ROLE Bokforer_per;
DELETE FROM Transaksjoner WHERE kilde = 'manuell';
RESET ROLE;

--ekstern_revisor ikke kan lese fra Transaksjoner men kan lese fra kontoer
SET ROLE ekstern_revisor;
SELECT * FROM Transaksjoner;
SELECT * FROM Kontoer LIMIT 1; --Bedre for å lesebarheten
RESET ROLE;

--RLS 

ALTER TABLE Transaksjoner ENABLE ROW LEVEL SECURITY;

CREATE POLICY policy_aar_filter ON Transaksjoner FOR SELECT TO regnskapsforer USING (
	EXTRACT(YEAR FROM bilagsdato) = EXTRACT(YEAR FROM CURRENT_DATE)
);

CREATE POLICY policy_revisor_alt ON Transaksjoner FOR SELECT TO regnskap_admin, revisor USING (TRUE); 






