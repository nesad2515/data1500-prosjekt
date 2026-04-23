--Lag et VIEW kalt v_salgsrapport som joiner Fakturaer, Fakturalinjer, Kunder, Kontoer (for inntektskonto) og MVA_koder
-- for å vise en detaljert salgsrapport. 
--Viewet skal inneholde: kundenavn, fakturanummer, fakturadato, varebeskrivelse, antall, enhetspris (eks. MVA), MVA-sats og totalbeløp inkl. MVA.
BEGIN;

CREATE VIEW v_salgsrapport AS 
SELECT 
	k.navn AS kundenavn,
	f.fakturanummer, 
	f.fakturadato,
	v.beskrivelse,
	v.antall AS Antall,
	v.enhetspris_teller AS Enhetspris,
	ko.kontonummer AS inntektskonto,
	m.sats_teller,
	ABS(SUM(v.enhetspris_teller + (v.enhetspris_teller/100) * m.sats_teller)) AS "Totalbeløp inkl. MVA"
FROM Fakturaer f
JOIN Fakturalinjer v 
	ON v.faktura_guid = f.guid
JOIN Kunder k 
	ON k.guid = f.kunde_guid
JOIN MVA_koder m
	ON v.mva_kode_guid = m.guid
JOIN Kontoer ko
	ON v.inntektskonto_guid = ko.guid
WHERE 
	ko.kontonummer BETWEEN 3000 AND 3999
GROUP BY
	k.navn,
	f.fakturanummer,
	f.fakturadato,
	v.beskrivelse,
	v.antall,
	v.enhetspris_teller,
	ko.kontonummer,
	m.sats_teller;
	
	
CREATE MATERIALIZED VIEW mv_salgsrapport AS
SELECT * FROM v_salgsrapport;
COMMIT;