CREATE VIEW IF NOT EXISTS v_new_build_premium AS

-- Насколько новостройки дороже вторички в том же районе
SELECT
        sec.district,
        sec.avg_secondary,
        nb.avg_newbuild,
        ROUND((nb.avg_newbuild - sec.avg_secondary) / sec.avg_secondary * 100, 1) AS premium_pct
FROM (
    SELECT district, AVG(price_per_sqm) AS avg_secondary
    FROM secondary_market
    WHERE is_new_moscow = 0 AND is_premium = 0
    GROUP BY district
) sec
JOIN (
    SELECT district, AVG(price_per_sqm) AS avg_newbuild
    FROM new_builds
    WHERE is_new_moscow = 0 AND is_premium = 0
    GROUP BY district
) nb
    ON sec.district = nb.district
ORDER BY premium_pct DESC