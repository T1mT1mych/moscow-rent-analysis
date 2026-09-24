CREATE VIEW IF NOT EXISTS v_secondary_market_metro AS

SELECT s.*,
       m.year_opened
  FROM secondary_market s
  LEFT JOIN metro_stations m
    ON s.metro_station = m.station_name
