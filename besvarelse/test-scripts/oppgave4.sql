--DEL A Janis tok ikke med Klasse 7, og bruker litt andre navn enn meg, men ellers så er spørringen riktig utifra premissene som er gitt
WITH RECURSIVE kontoplan_hierarki AS (
	SELECT 
		guid, 
		CASE WHEN kontonummer::TEXT IS NULL THEN '-' ELSE kontonummer::TEXT END AS kontonummer, 
		navn, 
		0 AS nivaa, 
		CAST(navn AS TEXT) AS sti 
	FROM Kontoer 
	WHERE overordnet_guid IS NULL 
	UNION ALL 
	SELECT 
		k.guid, 
		k.kontonummer::TEXT, 
		k.navn, 
		kh.nivaa + 1, 
		kh.sti ||' > '|| k.navn 
	FROM Kontoer k 
	JOIN Kontoplan_hierarki kh 
		ON k.overordnet_guid = kh.guid) 
	SELECT 
		nivaa, 
		REPEAT('  ', nivaa) || COALESCE(kontonummer, '-') AS kontonummer, 
		REPEAT('  ', nivaa) || navn as navn, 
		sti 
	FROM kontoplan_hierarki 
	ORDER BY sti;

--DEL B
WITH CTE_Posteringer cp AS (
	SELECT
		SUM(p.belop_teller) 
			AS saldo,
		konto_guid
	FROM Posteringer p
	GROUP BY 
		konto_guid,
	),
	kontoplan_hierarki AS (
	SELECT 
		guid, 
		CASE WHEN kontonummer::TEXT IS NULL THEN '-' ELSE kontonummer::TEXT END AS kontonummer, 
		navn, 
		0 AS nivaa, 
		CAST(navn AS TEXT) AS sti 
	FROM Kontoer 
	WHERE overordnet_guid IS NULL 
	UNION ALL 
	SELECT 
		k.guid, 
		k.kontonummer::TEXT, 
		k.navn, 
		kh.nivaa + 1, 
		kh.sti ||' > '|| k.navn, 
	FROM Kontoer k 
	JOIN Kontoplan_hierarki kh 
		ON k.overordnet_guid = kh.guid) 
	SELECT 
		nivaa, 
		REPEAT('  ', nivaa) || COALESCE(kontonummer, '-') AS kontonummer, 
		REPEAT('  ', nivaa) || navn as navn, 
		sti,
		cp.saldo
	FROM Kontoplan_hierarki
	WHERE k.kontoklasse BETWEEN 1 AND 2
	ORDER BY k.kontonummer;