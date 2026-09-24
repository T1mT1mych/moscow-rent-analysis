"""Тесты для src/mart.py — витрина собирается на синтетической БД той же схемы"""

from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from src.mart import build_mart, build_districts, build_segment_medians

SQL_DIR = Path(__file__).resolve().parents[1] / 'sql'


def make_db(path):
    """
    Три района: два в старой Москве, один в Новой

    В Tverskoy половина вторички помечена премиумом — на этом районе
    проверяется, что база «со всеми» и «без премиума» разъезжаются.
    """
    rows_secondary = []
    for district, okrug, new_moscow, base in [
        ('Tverskoy', 'CAO', 0, 300000),
        ('Yasenevo', 'YuZAO', 0, 200000),
        ('Troitsk', 'TAO', 1, 90000),
    ]:
        for i in range(10):
            premium = 1 if (district == 'Tverskoy' and i >= 5) else 0
            rows_secondary.append({
                'district': district, 'okrug': okrug,
                'lat': 55.7 + i / 1000, 'lon': 37.6 + i / 1000,
                'to_center_km': 5.0 + i,
                'date_posted': f'202{1 + i % 2}-0{1 + i % 9}-15',
                'price_per_sqm': base * (2 if premium else 1),
                'is_premium': premium, 'is_new_moscow': new_moscow,
            })

    rows_rentals = [{
        'district': d, 'okrug': o, 'date_posted': f'202{1 + i % 2}-0{1 + i % 9}-15',
        'rent_per_sqm': base, 'is_premium': 0, 'is_new_moscow': nm,
    } for d, o, nm, base in [('Tverskoy', 'CAO', 0, 1500),
                             ('Yasenevo', 'YuZAO', 0, 1200),
                             ('Troitsk', 'TAO', 1, 500)]
      for i in range(10)]

    rows_new_builds = [{
        'district': d, 'okrug': o, 'date_posted': f'202{1 + i % 2}-0{1 + i % 9}-15',
        'price_per_sqm': base, 'is_premium': 0, 'is_new_moscow': nm,
    } for d, o, nm, base in [('Tverskoy', 'CAO', 0, 400000),
                             ('Troitsk', 'TAO', 1, 110000)]
      for i in range(10)]

    rows_monthly = [{
        'year_month': f'2021-0{m}-01', 'district': d, 'okrug': o,
        'secondary_price_per_sqm': base, 'newbuild_price_per_sqm': base * 1.2,
        'rental_price_per_sqm_monthly': base / 200,
        'secondary_mom_change_pct': 0.5, 'newbuild_mom_change_pct': 0.4,
        'n_listings_secondary': 5, 'n_listings_newbuild': 3, 'n_listings_rental': 4,
        'cbr_key_rate_pct': 7.5, 'avg_mortgage_rate_pct': 9.0,
    } for d, o, base in [('Tverskoy', 'CAO', 310000),
                         ('Yasenevo', 'YuZAO', 210000),
                         ('Troitsk', 'TAO', 95000)]
      for m in range(1, 4)]

    conn = sqlite3.connect(str(path))
    pd.DataFrame(rows_secondary).to_sql('secondary_market', conn, index=False)
    pd.DataFrame(rows_rentals).to_sql('rentals', conn, index=False)
    pd.DataFrame(rows_new_builds).to_sql('new_builds', conn, index=False)
    pd.DataFrame(rows_monthly).to_sql('district_prices_monthly', conn, index=False)

    for name in ['payback_period', 'new_build_premium', 'official_check']:
        conn.executescript((SQL_DIR / f'{name}.sql').read_text(encoding='utf-8'))

    conn.commit()
    conn.close()


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'test.db'
    make_db(path)
    return path


def test_build_mart_returns_four_tables(db):
    mart = build_mart(db)
    assert set(mart) == {'mart_districts', 'mart_district_month',
                         'mart_segment_medians', 'mart_meta'}


def test_district_grain_is_unique(db):
    districts = build_mart(db)['mart_districts']
    assert len(districts) == 3
    assert districts['district'].is_unique


def test_premium_split_diverges_where_premium_exists(db):
    districts = build_mart(db)['mart_districts'].set_index('district')

    tverskoy = districts.loc['Tverskoy']
    assert tverskoy['avg_price_sqm_all'] > tverskoy['avg_price_sqm_no_premium']

    # там, где премиума нет, обе базы обязаны совпасть
    yasenevo = districts.loc['Yasenevo']
    assert yasenevo['avg_price_sqm_all'] == yasenevo['avg_price_sqm_no_premium']


def test_new_moscow_is_filled(db):
    """Новая Москва считается по той же формуле, а не остаётся пустой"""
    districts = build_mart(db)['mart_districts'].set_index('district')
    assert pd.notna(districts.loc['Troitsk', 'payback_years'])
    assert pd.notna(districts.loc['Troitsk', 'newbuild_premium_pct'])


def test_null_stays_where_there_is_no_data(db):
    """
    NULL двух разных природ: «не считали» заполняется, «данных нет» — нет

    В Yasenevo нет ни одного объявления новостройки, наценку там считать
    не из чего, и она обязана остаться пустой.
    """
    districts = build_mart(db)['mart_districts'].set_index('district')
    assert districts.loc['Yasenevo', 'n_new_builds'] == 0
    assert pd.isna(districts.loc['Yasenevo', 'newbuild_premium_pct'])


def test_matches_source_views(db):
    """
    Расширение охвата не должно менять ни одного уже опубликованного числа

    Витрина считает payback и наценку сама, чтобы покрыть Новую Москву.
    На районах, которые попадают во VIEW, результат обязан совпасть точно.
    """
    districts = build_mart(db)['mart_districts']

    conn = sqlite3.connect(str(db))
    payback = pd.read_sql('SELECT district, payback_years FROM v_payback_period', conn)
    premium = pd.read_sql('SELECT district, premium_pct FROM v_new_build_premium', conn)
    conn.close()

    merged = payback.merge(districts, on='district', suffixes=('_view', '_mart'))
    assert len(merged) == len(payback)
    assert (merged['payback_years_view'] == merged['payback_years_mart']).all()

    merged_nb = premium.merge(districts, on='district')
    assert len(merged_nb) == len(premium)
    assert (merged_nb['premium_pct'] == merged_nb['newbuild_premium_pct']).all()


def test_district_month_covers_official_grain(db):
    mart = build_mart(db)
    assert len(mart['mart_district_month']) == 9  # 3 района × 3 месяца
    assert mart['mart_district_month']['n_listings_ours'].notna().all()


def test_segment_medians_all_period_is_computed_from_raw(db):
    conn = sqlite3.connect(str(db))
    medians = build_segment_medians(conn)
    conn.close()

    row = medians[(medians['segment'] == 'Вторичка')
                  & (medians['moscow_part'] == 'Новая Москва')
                  & (medians['period'] == 'ALL')]
    assert len(row) == 1
    assert row['median_price_sqm_all'].iloc[0] == 90000
    assert row['n_listings'].iloc[0] == 10


def test_segment_medians_have_year_rows(db):
    conn = sqlite3.connect(str(db))
    medians = build_segment_medians(conn)
    conn.close()

    periods = set(medians['period'])
    assert 'ALL' in periods
    assert {'2021', '2022'} <= periods


def test_recommendation_scale_is_per_moscow_part(db):
    """
    Шкала подписи калибруется внутри своей части города

    В синтетических данных Новая Москва — один район, и он обязан быть
    «нейтрально»: при одном значении Q1 и Q3 совпадают, крайних четвертей
    просто нет. Старая Москва с двумя районами делится на края.
    """
    districts = build_mart(db)['mart_districts'].set_index('district')
    assert districts.loc['Troitsk', 'recommendation'] == 'нейтрально'
    assert set(districts.loc[['Tverskoy', 'Yasenevo'], 'recommendation']) == {
        'выгодно покупать', 'выгодно снимать'}


def test_recommendation_thresholds_are_published_in_meta(db):
    """Дашборд должен уметь показать, где именно проведена черта"""
    meta = build_mart(db)['mart_meta'].set_index('key')['value']
    assert 'payback_q1_Старая Москва' in meta.index
    assert 'payback_q3_Новая Москва' in meta.index


def test_meta_records_source_row_counts(db):
    meta = build_mart(db)['mart_meta'].set_index('key')['value']
    assert meta['source_rows_secondary_market'] == '30'
    assert meta['mart_districts_rows'] == '3'
