CREATE VIEW IF NOT EXISTS v_new_builds_metro AS

SELECT n.*,
       m.year_opened
  FROM new_builds n
  LEFT JOIN metro_stations m
    ON n.metro_station = m.station_name
