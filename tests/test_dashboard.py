"""
Тесты дашборда

Подготовка данных проверяется обычным pytest, страницы — через AppTest Streamlit:
он выполняет страницу без браузера и сервера, поэтому ловит падения на реальных
данных витрины из data/mart/ и при переключении фильтров.
"""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.data import (
    MART_DIR, NEW, OLD, fmt_num, plural_ru, meta_dict, part_monthly_median,
    part_summary, prepare_district_month, prepare_districts, to_index,
)

APP = str(Path(__file__).resolve().parents[1] / 'streamlit_app.py')
PAGES = ['app_pages/overview.py', 'app_pages/map.py', 'app_pages/district.py',
         'app_pages/dynamics.py', 'app_pages/old_vs_new.py']


@pytest.fixture(scope='module')
def districts():
    return prepare_districts(pd.read_csv(MART_DIR / 'mart_districts.csv'))


def test_fmt_num_uses_russian_separators():
    assert fmt_num(1234567.891, 1) == '1 234 567,9'
    assert fmt_num(float('nan')) == '—'


def test_plural_ru():
    forms = ('район', 'района', 'районов')
    assert [plural_ru(n, *forms) for n in (1, 2, 5, 11, 12, 21, 22, 107)] == [
        'район', 'района', 'районов', 'районов', 'районов', 'район', 'района', 'районов']


def test_premium_in_rubles_is_newbuild_minus_secondary(districts):
    row = districts.dropna(subset=['newbuild_premium_rub']).iloc[0]
    assert row['newbuild_premium_rub'] == row['avg_newbuild_sqm_no_premium'] - row['avg_price_sqm_no_premium']


def test_dashboard_colors_match_notebook_style():
    """Старая и Новая Москва одного цвета и в дашборде, и в графиках ноутбуков"""
    from dashboard.data import PART_COLORS
    from src.plot_style import PART_COLORS as NOTEBOOK_PART_COLORS
    assert PART_COLORS == NOTEBOOK_PART_COLORS


def test_every_okrug_has_russian_name(districts):
    assert not districts['okrug_ru'].str.match(r'^[A-Za-z]').any()


def test_every_district_has_russian_name(districts):
    assert districts['name'].str.fullmatch(r'[А-Яа-яЁё \-]+').all()
    assert districts['name'].is_unique


def test_part_summary_matches_mart(districts):
    medians = pd.read_csv(MART_DIR / 'mart_segment_medians.csv', dtype={'period': str})
    summary = part_summary(districts, medians)
    assert summary[OLD]['districts'] + summary[NEW]['districts'] == len(districts)
    assert summary[NEW]['payback_median'] < summary[OLD]['payback_median']


def test_index_starts_at_100(districts):
    monthly = prepare_district_month(pd.read_csv(MART_DIR / 'mart_district_month.csv'), districts)
    table = to_index(part_monthly_median(monthly, 'official_secondary_sqm'))
    assert (table.iloc[0] == 100).all()
    assert list(table.columns) == [OLD, NEW]


def test_meta_has_recommendation_thresholds():
    meta = meta_dict(pd.read_csv(MART_DIR / 'mart_meta.csv'))
    for part in (OLD, NEW):
        assert f'payback_q1_{part}' in meta and f'payback_q3_{part}' in meta


def open_page(page):
    at = AppTest.from_file(APP, default_timeout=30).run()
    if page != PAGES[0]:
        at.switch_page(page).run()
    return at


@pytest.mark.parametrize('page', PAGES)
def test_page_renders_without_errors(page):
    at = open_page(page)
    assert not at.exception, at.exception


def test_map_every_metric_and_filter():
    at = open_page('app_pages/map.py')
    for option in at.selectbox(key='metric').options:
        at.selectbox(key='metric').select(option).run()
        assert not at.exception, (option, at.exception)
    at.multiselect(key='okrugs').select('ТАО').run()
    assert not at.exception


def test_map_filter_to_empty_shows_warning():
    at = open_page('app_pages/map.py')
    at.segmented_control(key='part').set_value('Новая Москва').run()
    at.multiselect(key='okrugs').select('ЦАО').run()
    assert not at.exception
    assert at.warning


def test_district_without_new_builds():
    at = open_page('app_pages/district.py')
    no_new_builds = next(o for o in at.selectbox(key='district').options if o.startswith('Аэропорт'))
    at.selectbox(key='district').select(no_new_builds).run()
    assert not at.exception
    assert any(m.value == '—' for m in at.metric)


def test_district_segments_switch():
    at = open_page('app_pages/district.py')
    for segment in ('newbuild', 'rent'):
        at.segmented_control(key='segment').set_value(segment).run()
        assert not at.exception


def test_dynamics_index_scale_and_old_vs_new_toggle():
    at = open_page('app_pages/dynamics.py')
    at.segmented_control(key='scale').set_value('Рост, январь 2020 = 100').run()
    assert not at.exception
    at = open_page('app_pages/old_vs_new.py')
    at.toggle(key='no_premium').set_value(True).run()
    assert not at.exception
