-- =====================================================
-- Payback period: сравнение рынка вторички и аренды
-- Показывает, через сколько лет аренда "окупит" покупку
-- Исключена Новая Москва и Премиум-сегмент
-- =====================================================

CREATE VIEW IF NOT EXISTS v_payback_period AS

  SELECT sec.district,
         sec.okrug,
         sec.avg_price_sqm,
         rent.avg_rent_sqm,
         ROUND(sec.avg_price_sqm / (rent.avg_rent_sqm * 12), 1) AS payback_years,
         CASE
             WHEN ROUND(sec.avg_price_sqm / (rent.avg_rent_sqm * 12), 1) < 15 THEN 'выгодно покупать'
             WHEN ROUND(sec.avg_price_sqm / (rent.avg_rent_sqm * 12), 1) > 25 THEN 'выгодно снимать'
             ELSE 'нейтрально'
         END AS recommendation
    FROM (
        SELECT district,
               okrug,
               AVG(price_per_sqm) AS avg_price_sqm
          FROM secondary_market
         WHERE is_new_moscow = 0
           AND is_premium = 0
      GROUP BY district, okrug
    ) AS sec
    JOIN (
         SELECT district,
                AVG(rent_per_sqm) AS avg_rent_sqm
           FROM rentals
          WHERE is_new_moscow = 0
            AND is_premium = 0
       GROUP BY district
    ) AS rent
      ON sec.district = rent.district
ORDER BY payback_years ASC