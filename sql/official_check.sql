-- =====================================================
-- Сверка собственных расчётов с официальной статистикой
-- Объявления сопоставляются с официальными данными того же месяца,
-- поэтому view покрывает весь период, а не один срез
-- Новая Москва исключена
-- =====================================================

CREATE VIEW IF NOT EXISTS v_official_check AS

SELECT
    d.year_month,
    s.district,
    COUNT(*)                                  AS n_listings,
    ROUND(AVG(s.price_per_sqm), 0)            AS our_avg_price,
    d.secondary_price_per_sqm                 AS official_price,
    ROUND(AVG(s.price_per_sqm) - d.secondary_price_per_sqm, 0) AS difference,
    ROUND((AVG(s.price_per_sqm) / d.secondary_price_per_sqm - 1) * 100, 1) AS difference_pct
FROM secondary_market s
JOIN district_prices_monthly d
    ON s.district = d.district
   AND substr(s.date_posted, 1, 7) = substr(d.year_month, 1, 7)
WHERE s.is_new_moscow = 0
GROUP BY d.year_month, s.district, d.secondary_price_per_sqm
ORDER BY d.year_month, s.district
