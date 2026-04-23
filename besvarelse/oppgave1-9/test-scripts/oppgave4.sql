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


--//


WITH RECURSIVE CTE_Posteringer AS (
	SELECT
		COALESCE(SUM(p.belop_teller, 0)) AS saldo,
		k.kontonummer,
		k.guid,
		k.kontoklasse
	FROM Posteringer p
	JOIN Kontoer k
		ON k.guid = p.konto_guid
	GROUP BY
		k.kontonummer,
		k.guid,
		k.kontoklasse
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
		kh.sti ||' > '|| k.navn 
		cp.saldo 
	FROM Kontoer k 
	JOIN Kontoplan_hierarki kh 
		ON k.overordnet_guid = kh.guid)
	JOIN CTE_Posteringer cp 
		ON cp.guid = kh.guid
),
		
		
aggreging AS (
	SELECT 
		kh.guid
		kh.nivaa, 
		REPEAT('  ', nivaa) || COALESCE(kh.kontonummer, '-') AS kontonummer, 
		REPEAT('  ', nivaa) || kh.navn as navn, 
		kh.sti,
		cp.saldo,
		cp.kontoklasse
	FROM kontoplan_hierarki kh
	LEFT JOIN CTE_Posteringer cp 
		on kh.guid = cp.guid
	WHERE cp.kontoklasse BETWEEN 1 AND 2
	ORDER BY kh.kontonummer;
),	

aggreging AS (
	SELECT 
	kh.guid
	SUM()
),	

	

	
--//


WITH RECURSIVE CTE_Posteringer AS (
	SELECT
		SUM(p.belop_teller) AS saldo,
		k.kontonummer,
		k.guid,
		k.kontoklasse
	FROM Posteringer p
	JOIN Kontoer k
		ON k.guid = p.konto_guid
	GROUP BY
		k.kontonummer,
		k.guid,
		k.kontoklasse
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
		kh.sti ||' > '|| k.navn 
	FROM Kontoer k 
	JOIN Kontoplan_hierarki kh 
		ON k.overordnet_guid = kh.guid)
	SELECT 
		kh.nivaa, 
		REPEAT('  ', nivaa) || COALESCE(kh.kontonummer, '-') AS kontonummer, 
		REPEAT('  ', nivaa) || kh.navn as navn, 
		kh.sti,
		cp.saldo AS total_sum,
		cp.kontoklasse
	FROM kontoplan_hierarki kh
	LEFT JOIN CTE_Posteringer cp 
		on kh.guid = cp.guid
	WHERE cp.kontoklasse BETWEEN 1 AND 2
		GROUP BY 
		kh.nivaa,
		kh.kontonummer,
		kh.navn,
		kh.sti,
		cp.kontoklasse,
		cp.saldo
	ORDER BY kh.kontonummer;
	

		