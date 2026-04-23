-- Vis hele kontoplanen Skriv en spørring som henter kontonummer, navn og kontoklasse for alle kontoer som har et kontonummer. Sorter resultatet etter kontonummer.
SELECT 
	kontonummer, 
	navn, 
	kontoklasse 
FROM Kontoer 
WHERE kontonummer IS NOT NULL 
ORDER BY kontonummer;

--Vis alle kontoklasser Skriv en spørring som henter kode, navn og type (BALANSE/RESULTAT) for alle de åtte kontoklassene. Sorter etter klassenummer(Når de skriver kode mener de nummeret på kontoklassen?).
SELECT 
	klasse_nr AS kode, 
	navn, 
	type_klasse 
FROM Kontoklasser 
ORDER BY klasse_nr;

--Koble kontoer med klasser Skriv en spørring som viser kontonummer, kontonavn og navnet på kontoklassen kontoen tilhører. Bruk en JOIN.
SELECT 
	k.kontonummer, 
	k.navn AS Kontonavn, 
	kl.navn AS Kontoklasse 
FROM Kontoer k 
JOIN Kontoklasser kl ON k.kontoklasse = kl.klasse_nr 
ORDER BY Kontonummer;

--Antall posteringer per transaksjon Skriv en spørring som viser bilagsnummer, beskrivelse og bilagsdato for hver transaksjon, sammen med antall posteringer den inneholder. Sorter etter dato.
SELECT 
	COUNT(p.guid) AS antall_posteringer, 
	t.bilagsnummer, 
	t.beskrivelse, 
	t.bilagsdato 
FROM Transaksjoner t 
JOIN Posteringer p 
	ON t.guid = p.transaksjon_guid 
GROUP BY t.bilagsdato, t.bilagsnummer, t.beskrivelse 
ORDER BY t.bilagsdato;

--Saldo per konto Skriv en spørring som beregner og viser den totale saldoen i kroner for hver konto som har posteringer. Vis kontonummer, navn og saldo. Sorter etter kontonummer.
SELECT 
	SUM(p.belop_teller) / 100 AS Saldo, 
	k.kontonummer, 
	k.navn 
FROM Kontoer k 
JOIN Posteringer p 
	ON p.konto_guid = k.guid 
GROUP BY k.kontonummer, k.navn 
ORDER BY k.kontonummer;

-- Finn MVA-pliktige eller placeholder-kontoer Skriv en spørring som finner alle kontoer som enten er MVA-pliktige (mva_pliktig = TRUE) ELLER er en placeholder-konto (er_placeholder = TRUE).
SELECT 
	* 
FROM Kontoer 
WHERE mva_pliktig IS TRUE OR er_placeholder IS TRUE;

--Vis lønnstransaksjonen med debet/kredit Skriv en spørring som henter alle posteringer relatert til lønn (der transaksjonensbeskrivelse inneholder 'lønn'). Vis transaksjonsbeskrivelse, dato, kontonummer, kontonavn, beløp og en egen kolonne som sier 'Debet' eller 'Kredit' basert på fortegnet til beløpet.
SELECT 
	t.beskrivelse, 
	t.bilagsdato, 
	k.kontonummer, 
	k.navn, 
	p.belop_teller AS Lønnkolonne, 
	CASE WHEN p.belop_teller < 0 THEN 'KREDIT' WHEN p.belop_teller > 0 THEN 'DEBET' ELSE 'Null' END AS EgenKolonne 
FROM Transaksjoner t 
JOIN Posteringer p 
	ON p.transaksjon_guid = t.guid 
JOIN Kontoer k 
	ON k.guid = p.konto_guid 
WHERE t.beskrivelse ILIKE '%l?nn%'; 

--Antall kontoer per klasse Skriv en spørring som viser antall reelle driftskontoer i hver av de åtte kontoklassene. Vis også hvor mange av disse som er markert som MVA-pliktige. Bruk LEFT JOIN for å inkludere klasser uten kontoer.
SELECT 
	COUNT(k.guid) AS Antall_kontoer, 
	kl.klasse_nr, kl.navn, 
	SUM(CASE WHEN k.mva_pliktig = TRUE THEN 1 ELSE 0 END) AS antall_mva_pliktige 
FROM kontoklasser kl 
LEFT JOIN Kontoer k 
	ON k.kontoklasse = kl.klasse_nr 
GROUP BY kl.klasse_nr, kl.navn;

--Saldo for alle eiendelskontoer Skriv en spørring som viser saldoen for alle reelle eiendelskontoer (klasse 1), inkludert de som har null i saldo. Bruk LEFT JOIN.
SELECT 
	k.kontonummer, 
	k.navn, 
	SUM(p.belop_teller) / 100.0 AS Saldo_kroner 
FROM Kontoer k 
LEFT JOIN Posteringer p 
	ON p.konto_guid = k.guid 
WHERE k.kontoklasse = 1 
GROUP BY k.kontonummer, k.navn;

--Finn ubalanserte transaksjoner Skriv en spørring som verifiserer dobbelt bokholderi-prinsippet. Spørringen skal finne alle transaksjoner der summen av belop_teller for alle tilhørende posteringer ikke er 0. Spørringen skal returnere et tomt resultat hvis databasen er i balanse.
SELECT 
	p.transaksjon_guid, 
	SUM(p.belop_teller) AS Saldo 
FROM Posteringer p 
GROUP BY p.transaksjon_guid 
HAVING SUM(belop_teller) <> 0;

--Vis alle MVA-beregninger Skriv en spørring som henter alle MVA-linjer og kobler dem med MVA-koden og transaksjonen de tilhører. Vis MVA-kode, grunnlag, MVA-beløp og transaksjonsbeskrivelse.
SELECT 
	mk.kode, 
	t.beskrivelse,
	m.grunnlag_teller,
	m.mva_belop_teller 
FROM MVA_linjer m 
JOIN MVA_koder mk 
	ON mk.guid = m.mva_kode_guid 
JOIN Transaksjoner t 
	ON t.guid = m.transaksjon_guid; 

--Vis alle valutakurser Skriv en spørring som viser alle registrerte valutakurser. Vis 'fra'-valuta, 'til'-valuta, kurs og dato. Sorter etter nyeste kurs først.
SELECT 
	v1.navn AS fra_valuta, 
	v2.navn AS til_valuta, 
	vk.kurs_teller, dato 
FROM Valutakurser vk 
JOIN Valutaer v1 
	ON v1.guid = vk.fra_valuta_guid 
JOIN Valutaer v2 
	ON v2.guid = vk.til_valuta_guid 
ORDER BY dato DESC;

--Antall transaksjoner per periode Skriv en spørring som viser antall transaksjoner i hver regnskapsperiode som har transaksjoner. Vis periodenavn, datoer, status og antall transaksjoner.
SELECT 
	COUNT(t.guid), 
	r.navn, 
	r.fra_dato, 
	r.til_dato, 
	r.status 
FROM Regnskapsperioder r 
JOIN Transaksjoner t 
	ON t.periode_guid = r.guid 
GROUP BY r.navn, r.fra_dato, r.til_dato, r.status;

--Total saldo per kontoklasse Skriv en spørring som beregner den totale saldoen for hver kontoklasse. Vis klassenummer, klassenavn, type og totalsaldo.
SELECT 
	SUM(p.belop_teller) AS totalsaldo, 
	k.kontoklasse, 
	kl.type_klasse, 
	kl.navn 
FROM Posteringer p 
JOIN Kontoer k 
	ON k.guid = p.konto_guid 
JOIN Kontoklasser kl 
	ON kl.klasse_nr = k.kontoklasse 
GROUP BY k.kontoklasse, kl.type_klasse, kl.navn;

--Detaljert analyse av resultatkontoer Skriv en spørring som viser en detaljert analyse for alle resultatkontoer (klasse 3-8). Vis kontonummer, navn, antall posteringer, netto saldo, total debet, total kredit og gjennomsnittlig transaksjonsbeløp (absoluttverdi).
SELECT 
	k.kontonummer, 
	k.navn, 
	COUNT(p.guid) AS Antall_posteringer, 
	SUM(p.belop_teller) AS netto_saldo, 
	SUM(CASE WHEN p.belop_teller > 0 THEN p.belop_teller ELSE 0 END) AS Total_Debet, 
	SUM(CASE WHEN p.belop_teller < 0 THEN p.belop_teller ELSE 0 END) AS Total_Kredit, 
	AVG(ABS(p.belop_teller)) 
FROM Posteringer p 
JOIN Kontoer k 
	ON k.guid = p.konto_guid 
WHERE k.kontoklasse >= 3 
GROUP BY k.kontonummer, k.navn;