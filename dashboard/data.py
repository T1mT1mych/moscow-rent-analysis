"""
Чтение витрины для дашборда и общие справочники

Здесь нет ничего от Streamlit, кроме кеширования в loaders: вся подготовка
данных — обычные функции pandas, их можно проверять pytest без запуска приложения.
"""

from pathlib import Path

import pandas as pd

from dashboard.district_names import DISTRICT_NAMES_RU

MART_DIR = Path(__file__).resolve().parents[1] / 'data' / 'mart'

OLD, NEW = 'Старая Москва', 'Новая Москва'
PARTS = [OLD, NEW]

# цвета частей города проверены валидатором палитры: различимы при всех видах
# дальтонизма и контрастны на светлом фоне; тема дашборда закреплена светлой
PART_COLORS = {OLD: '#2a78d6', NEW: '#eb6834'}
NEUTRAL = '#898781'
SEQUENTIAL = ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281', '#0d366b']

OKRUG_NAMES = {
    'CAO': 'ЦАО', 'SAO': 'САО', 'SVAO': 'СВАО', 'VAO': 'ВАО', 'YuVAO': 'ЮВАО',
    'YuAO': 'ЮАО', 'YuZAO': 'ЮЗАО', 'ZAO': 'ЗАО', 'SZAO': 'СЗАО',
    'ZelAO': 'ЗелАО', 'NAO': 'НАО', 'TAO': 'ТАО',
}

# метрики районов: колонка -> (название, единица, пояснение для читателя)
METRICS = {
    'avg_price_sqm_all': (
        'Цена вторички', '₽/м²',
        'Средняя цена квадратного метра в объявлениях о продаже вторичного жилья, все объекты.'),
    'avg_price_sqm_no_premium': (
        'Цена вторички без премиума', '₽/м²',
        'То же без самых дорогих объектов (премиум-сегмента). В центре разница с полной '
        'средней доходит до 40%, в спальных районах почти нулевая.'),
    'avg_rent_sqm_all': (
        'Аренда', '₽/м² в месяц',
        'Средняя месячная арендная ставка за квадратный метр.'),
    'payback_years': (
        'Окупаемость', 'лет',
        'За сколько лет аренда вернёт цену покупки: цена м² / (аренда м² × 12). '
        'Валовая оценка — без налогов, простоев и расходов на содержание. '
        'Считается без премиум-сегмента.'),
    'newbuild_premium_pct': (
        'Наценка новостроек', '%',
        'Насколько метр в новостройке дороже метра на вторичке в том же районе, '
        'без премиум-сегмента. В районах без новостроек не считается.'),
    'newbuild_premium_rub': (
        'Наценка новостроек в рублях', '₽/м²',
        'Та же наценка в рублях за метр. Процент зависит от базы: в дешёвом районе '
        'та же рублёвая разница даёт больший процент.'),
    'to_center_km': (
        'Расстояние до центра', 'км',
        'Среднее расстояние объявлений района до центра Москвы.'),
}

SEGMENTS = {
    'secondary': ('Вторичка', 'official_secondary_sqm', '₽/м²'),
    'newbuild': ('Новостройки', 'official_newbuild_sqm', '₽/м²'),
    'rent': ('Аренда', 'official_rent_sqm', '₽/м² в месяц'),
}


OFFICIAL_SERIES_NOTE = (
    'Графики во времени построены по помесячной статистике районов, которая входит в датасет '
    'отдельной таблицей. Цены в объявлениях ниже этого ряда: в старой Москве в среднем на треть, '
    'в Новой — почти вдвое, — поэтому числа на графике не совпадают с карточками. Динамика у двух источников '
    'в целом по городу совпадает почти полностью (корреляция 0,996), так что графики стоит читать как «как менялись цены», '
    'а карточки — как «сколько стоит метр в объявлениях».'
)


def fmt_num(value, digits=0):
    """Число по-русски: пробел между разрядами, запятая перед дробной частью"""
    if pd.isna(value):
        return '—'
    return f'{value:,.{digits}f}'.replace(',', ' ').replace('.', ',')


def okrug_label(code):
    return OKRUG_NAMES.get(code, code)


def prepare_districts(df):
    df = df.copy()
    df['okrug_ru'] = df['okrug'].map(okrug_label)
    df['newbuild_premium_rub'] = df['avg_newbuild_sqm_no_premium'] - df['avg_price_sqm_no_premium']
    df['name'] = df['district'].map(DISTRICT_NAMES_RU).fillna(df['district'])
    df['label'] = df['name'] + ' (' + df['okrug_ru'] + ')'
    return df


def prepare_district_month(df, districts):
    df = df.copy()
    df['month'] = pd.to_datetime(df['year_month'])
    parts = districts.set_index('district')['moscow_part']
    df['moscow_part'] = df['district'].map(parts)
    df['okrug_ru'] = df['okrug'].map(okrug_label)
    return df


def meta_dict(df):
    return dict(zip(df['key'], df['value']))


def part_monthly_median(district_month, column):
    """Медиана по районам внутри каждой части города на каждый месяц"""
    return (district_month.groupby(['month', 'moscow_part'])[column].median()
            .unstack('moscow_part').reindex(columns=PARTS))


def to_index(table, base_row=0):
    """Ряды в индекс: первая строка = 100, чтобы сравнивать рост, а не уровень"""
    return table / table.iloc[base_row] * 100


def key_rate_series(district_month):
    """Ключевая ставка общая для всего города — берём по одному значению на месяц"""
    return district_month.groupby('month')['cbr_key_rate_pct'].first()


def part_summary(districts, segment_medians):
    """Сводка по частям города для карточек на главной странице"""
    all_period = segment_medians[segment_medians['period'] == 'ALL'].set_index(['segment', 'moscow_part'])
    rows = {}
    for part in PARTS:
        side = districts[districts['moscow_part'] == part]
        rows[part] = {
            'districts': len(side),
            'price_median': all_period.loc[('Вторичка', part), 'median_price_sqm_all'],
            'rent_median': all_period.loc[('Аренда', part), 'median_price_sqm_all'],
            'newbuild_median': all_period.loc[('Новостройки', part), 'median_price_sqm_all'],
            'payback_median': side['payback_years'].median(),
            'premium_pct_median': side['newbuild_premium_pct'].median(),
            'premium_rub_median': side['newbuild_premium_rub'].median(),
        }
    return rows


def recommendation_note(part, meta):
    q1 = meta.get(f'payback_q1_{part}')
    q3 = meta.get(f'payback_q3_{part}')
    return (f'Подпись относительная: «выгодно покупать» — окупаемость короче {q1} лет, '
            f'то есть в быстрейшей четверти районов своей части города ({part}); '
            f'«выгодно снимать» — длиннее {q3} лет, в самой медленной четверти. '
            f'Сравнивать подписи старой и Новой Москвы нельзя — у них разные шкалы, '
            f'для сравнения служит само число лет.')
