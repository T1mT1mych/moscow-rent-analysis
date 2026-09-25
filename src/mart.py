"""
Витрина данных (data mart) для BI-дашборда

Собирает уже посчитанные метрики (v_payback_period, v_new_build_premium,
v_official_check, медианы старая/новая Москва) в четыре таблицы `mart_*`
с одинаковыми ключами, пригодные для чтения дашбордом напрямую.

Главное, что делает этот слой поверх существующих VIEW — снимает
несовместимость фильтров. v_payback_period считает среднюю цену вторички
БЕЗ премиум-сегмента, v_official_check — ВМЕСТЕ с ним. В центральных
районах это две разные цифры под одним названием «средняя цена вторички»
(Хамовники: 371k против 531k, разница 43%). В витрине обе базы расчёта
разведены по разным колонкам с явными именами: *_no_premium и *_all.

Витрина пишется в две копии: таблицами mart_* в moscow_realty.db и CSV-файлами
в data/mart/. База в репозиторий не входит, а CSV входят — дашборд читает их,
поэтому работает сразу после клонирования, без прогона ноутбуков.

Запуск: python -m src.mart
"""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / 'data' / 'processed' / 'moscow_realty.db'
CSV_DIR = PROJECT_ROOT / 'data' / 'mart'

MART_TABLES = [
    'mart_districts',
    'mart_district_month',
    'mart_segment_medians',
    'mart_meta',
]

SEGMENTS = [
    ('rentals', 'rent_per_sqm', 'Аренда'),
    ('secondary_market', 'price_per_sqm', 'Вторичка'),
    ('new_builds', 'price_per_sqm', 'Новостройки'),
]


def build_districts(conn):
    """
    Одна строка на район (129 строк: 107 старая Москва + 22 Новая)

    Payback и наценка новостроек считаются здесь заново, а не берутся из
    VIEW, чтобы покрыть все районы. Это не смена методики: is_new_moscow —
    свойство района целиком, ни один район не смешивает оба типа, поэтому
    условие is_new_moscow = 0 во VIEW никогда не влияло на расчёт внутри
    района, а только отсекало 22 района от вывода. Формула та же, и на
    107 районах старой Москвы результат совпадает со VIEW до последнего
    знака — это зафиксировано тестом test_matches_source_views.

    Оставшиеся NULL имеют другую природу: в 20 районах нет ни одного
    объявления новостройки, наценку там считать не из чего.
    """
    base = pd.read_sql("""
        SELECT district,
               okrug,
               MAX(is_new_moscow)                    AS is_new_moscow,
               COUNT(*)                              AS n_secondary,
               ROUND(AVG(lat), 5)                    AS lat,
               ROUND(AVG(lon), 5)                    AS lon,
               ROUND(AVG(to_center_km), 2)           AS to_center_km,
               ROUND(AVG(price_per_sqm))             AS avg_price_sqm_all,
               ROUND(AVG(price_per_sqm) FILTER (WHERE is_premium = 0)) AS avg_price_sqm_no_premium,
               SUM(is_premium)                       AS n_premium_secondary
          FROM secondary_market
      GROUP BY district
    """, conn)

    rentals = pd.read_sql("""
        SELECT district,
               COUNT(*)                          AS n_rentals,
               ROUND(AVG(rent_per_sqm))          AS avg_rent_sqm_all,
               ROUND(AVG(rent_per_sqm) FILTER (WHERE is_premium = 0)) AS avg_rent_sqm_no_premium
          FROM rentals
      GROUP BY district
    """, conn)

    new_builds = pd.read_sql("""
        SELECT district,
               COUNT(*)                          AS n_new_builds,
               ROUND(AVG(price_per_sqm))         AS avg_newbuild_sqm_all
          FROM new_builds
      GROUP BY district
    """, conn)

    payback = pd.read_sql("""
        SELECT sec.district,
               ROUND(sec.a / (rent.a * 12), 1) AS payback_years
          FROM (SELECT district, AVG(price_per_sqm) AS a
                  FROM secondary_market WHERE is_premium = 0 GROUP BY district) sec
          JOIN (SELECT district, AVG(rent_per_sqm) AS a
                  FROM rentals WHERE is_premium = 0 GROUP BY district) rent
            ON sec.district = rent.district
    """, conn)

    premium = pd.read_sql("""
        SELECT sec.district,
               ROUND(nb.a)                        AS avg_newbuild_sqm_no_premium,
               ROUND((nb.a - sec.a) / sec.a * 100, 1) AS newbuild_premium_pct
          FROM (SELECT district, AVG(price_per_sqm) AS a
                  FROM secondary_market WHERE is_premium = 0 GROUP BY district) sec
          JOIN (SELECT district, AVG(price_per_sqm) AS a
                  FROM new_builds WHERE is_premium = 0 GROUP BY district) nb
            ON sec.district = nb.district
    """, conn)

    official = pd.read_sql("""
        SELECT district,
               ROUND(AVG(official_price))    AS official_avg_price,
               ROUND(AVG(difference_pct), 1) AS official_diff_pct,
               SUM(n_listings)               AS n_matched_to_official
          FROM (
              SELECT d.year_month,
                     s.district,
                     COUNT(*)                          AS n_listings,
                     d.secondary_price_per_sqm         AS official_price,
                     ROUND((AVG(s.price_per_sqm) / d.secondary_price_per_sqm - 1) * 100, 1)
                                                       AS difference_pct
                FROM secondary_market s
                JOIN district_prices_monthly d
                  ON s.district = d.district
                 AND substr(s.date_posted, 1, 7) = substr(d.year_month, 1, 7)
            GROUP BY d.year_month, s.district, d.secondary_price_per_sqm
          )
      GROUP BY district
    """, conn)

    df = base
    for part in (rentals, new_builds, payback, premium, official):
        df = df.merge(part, on='district', how='left')

    df['n_rentals'] = df['n_rentals'].fillna(0).astype(int)
    df['n_new_builds'] = df['n_new_builds'].fillna(0).astype(int)
    df['is_new_moscow'] = df['is_new_moscow'].astype(bool)
    df['moscow_part'] = df['is_new_moscow'].map({False: 'Старая Москва', True: 'Новая Москва'})
    df['recommendation'] = add_recommendation(df)

    return df.sort_values('district').reset_index(drop=True)


def payback_thresholds(df):
    """Границы Q1/Q3 окупаемости внутри каждой части Москвы"""
    return {part: (g['payback_years'].quantile(0.25), g['payback_years'].quantile(0.75))
            for part, g in df.groupby('moscow_part')}


def add_recommendation(df):
    """
    Подпись «выгодно покупать / нейтрально / выгодно снимать»

    Шкала СВОЯ для каждой части Москвы и потому относительная: подпись
    означает «в нижней/верхней четверти по окупаемости внутри своей части
    города», а не абсолютную выгоду. Прежние фиксированные пороги 15/25
    лет калибровались, когда в выборке была только старая Москва, и на
    129 районах разъезжались: у Новой Москвы медиана 15.0 садилась ровно
    на границу, из-за чего почти половина её районов получала ярлык
    «выгодно покупать» просто по месту черты.

    Сравнивать подписи между старой и Новой Москвой нельзя — там разные
    шкалы, диапазон Новой Москвы вообще укладывается в 2 года. Для
    сравнения между частями есть payback_years. Сами границы пишутся в
    mart_meta, чтобы дашборд мог их показать.

    В v_payback_period пороги 15/25 намеренно оставлены как были — VIEW
    остаётся воспроизводимым артефактом опубликованных выводов.
    """
    bounds = payback_thresholds(df)
    labels = []
    for part, years in zip(df['moscow_part'], df['payback_years']):
        q1, q3 = bounds[part]
        if pd.isna(years):
            labels.append(None)
        elif years < q1:
            labels.append('выгодно покупать')
        elif years > q3:
            labels.append('выгодно снимать')
        else:
            labels.append('нейтрально')
    return labels


def build_district_month(conn):
    """
    Район × месяц (9804 строки) — временная ось дашборда

    Каркас — официальная статистика district_prices_monthly, потому что
    она покрывает все 129 районов на всём периоде без дыр. Наши объявления
    подшиваются слева: там, где в районе за месяц не было объявлений,
    n_listings_ours = 0, а our_avg_price = NULL. Дашборд по этой колонке
    решает, можно ли доверять точке ряда.

    Объявления агрегируются здесь, а не берутся из v_official_check: VIEW
    отфильтровывает Новую Москву, и её 22 района остались бы без наших цен.
    Формула та же, на районах старой Москвы результат совпадает с VIEW.
    """
    df = pd.read_sql("""
        SELECT d.year_month,
               d.district,
               d.okrug,
               d.secondary_price_per_sqm      AS official_secondary_sqm,
               d.newbuild_price_per_sqm       AS official_newbuild_sqm,
               d.rental_price_per_sqm_monthly AS official_rent_sqm,
               d.secondary_mom_change_pct,
               d.cbr_key_rate_pct,
               d.avg_mortgage_rate_pct,
               o.n_listings                   AS n_listings_ours,
               o.our_avg_price                AS our_avg_price_all,
               ROUND((o.avg_price / d.secondary_price_per_sqm - 1) * 100, 1) AS diff_vs_official_pct
          FROM district_prices_monthly d
          LEFT JOIN (
              SELECT district,
                     substr(date_posted, 1, 7)  AS ym,
                     COUNT(*)                   AS n_listings,
                     AVG(price_per_sqm)         AS avg_price,
                     ROUND(AVG(price_per_sqm), 0) AS our_avg_price
                FROM secondary_market
            GROUP BY district, ym
          ) o
            ON d.district = o.district
           AND substr(d.year_month, 1, 7) = o.ym
      ORDER BY d.year_month, d.district
    """, conn)

    new_moscow = pd.read_sql(
        'SELECT DISTINCT district, is_new_moscow FROM secondary_market', conn)
    df = df.merge(new_moscow, on='district', how='left')
    df['is_new_moscow'] = df['is_new_moscow'].astype(bool)
    df['n_listings_ours'] = df['n_listings_ours'].fillna(0).astype(int)

    return df


def build_segment_medians(conn):
    """
    Медианы старая/новая Москва по трём сегментам

    Гранулярность: сегмент × часть Москвы × период, где период — это
    каждый год плюс строка 'ALL' за весь диапазон. 'ALL' считается по
    сырым данным, а не как медиана годовых медиан — второе дало бы
    другое число.
    """
    rows = []

    for table, price_col, label in SEGMENTS:
        df = pd.read_sql(
            f'SELECT {price_col} AS price, is_premium, is_new_moscow, date_posted FROM {table}',
            conn)
        df['is_premium'] = df['is_premium'].astype(bool)
        df['is_new_moscow'] = df['is_new_moscow'].astype(bool)
        df['year'] = pd.to_datetime(df['date_posted']).dt.year.astype(str)

        for is_new, part in [(False, 'Старая Москва'), (True, 'Новая Москва')]:
            side = df[df['is_new_moscow'] == is_new]
            for period in ['ALL'] + sorted(side['year'].unique()):
                chunk = side if period == 'ALL' else side[side['year'] == period]
                no_prem = chunk[~chunk['is_premium']]
                rows.append({
                    'segment': label,
                    'source_table': table,
                    'moscow_part': part,
                    'period': period,
                    'median_price_sqm_all': round(chunk['price'].median()),
                    'median_price_sqm_no_premium': round(no_prem['price'].median()),
                    'n_listings': len(chunk),
                    'n_premium': int(chunk['is_premium'].sum()),
                })

    return pd.DataFrame(rows)


def build_meta(conn, districts, district_month, segment_medians):
    """Отпечаток сборки: по нему видно, что витрина отстала от исходных таблиц"""
    rows = [
        ('built_at', datetime.now(timezone.utc).isoformat(timespec='seconds')),
        ('mart_districts_rows', str(len(districts))),
        ('mart_district_month_rows', str(len(district_month))),
        ('mart_segment_medians_rows', str(len(segment_medians))),
    ]
    for table, _, _ in SEGMENTS:
        n = pd.read_sql(f'SELECT COUNT(*) AS n FROM {table}', conn)['n'][0]
        rows.append((f'source_rows_{table}', str(n)))

    for part, (q1, q3) in payback_thresholds(districts).items():
        rows.append((f'payback_q1_{part}', f'{q1:.1f}'))
        rows.append((f'payback_q3_{part}', f'{q3:.1f}'))

    return pd.DataFrame(rows, columns=['key', 'value'])


def build_mart(db_path=DB_PATH):
    """Собирает все таблицы витрины и возвращает их словарём"""
    conn = sqlite3.connect(str(db_path))
    try:
        districts = build_districts(conn)
        district_month = build_district_month(conn)
        segment_medians = build_segment_medians(conn)
        meta = build_meta(conn, districts, district_month, segment_medians)
    finally:
        conn.close()

    return {
        'mart_districts': districts,
        'mart_district_month': district_month,
        'mart_segment_medians': segment_medians,
        'mart_meta': meta,
    }


def write_mart(mart, db_path=DB_PATH, csv_dir=CSV_DIR):
    """Записывает витрину в БД таблицами mart_* и в CSV-файлы <имя таблицы>.csv"""
    csv_dir = Path(csv_dir)
    csv_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        for name, df in mart.items():
            df.to_sql(name, conn, if_exists='replace', index=False)
            df.to_csv(csv_dir / f'{name}.csv', index=False, lineterminator='\n')
            print(f'{name:24} {len(df):>6} строк')
        conn.commit()
    finally:
        conn.close()


if __name__ == '__main__':
    mart = build_mart()
    write_mart(mart)
    print(f'\nВитрина записана в {DB_PATH} и {CSV_DIR}')
