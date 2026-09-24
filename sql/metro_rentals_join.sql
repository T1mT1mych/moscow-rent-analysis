CREATE VIEW IF NOT EXISTS v_rentals_metro AS

SELECT r.*,
       m.year_opened
  FROM rentals r
  LEFT JOIN metro_stations m
    ON r.metro_station = m.station_name
