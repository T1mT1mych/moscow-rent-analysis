"""Функции для поверхностного анализа факторов цены"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker

# Русские подписи для категориальных значений (в исходных данных — на английском)
BUILDING_TYPE_RU = {
    'khrushchev': 'Хрущёвка',
    'panel': 'Панель',
    'modern_panel': 'Совр. панель',
    'brick': 'Кирпич',
    'monolith': 'Монолит',
    'stalin': 'Сталинка',
}

RENOVATION_RU = {
    'no_renovation': 'Без ремонта',
    'cosmetic': 'Косметический',
    'euro': 'Евроремонт',
    'designer': 'Дизайнерский',
}

COMPLEX_CLASS_RU = {
    'economy': 'Эконом',
    'comfort': 'Комфорт',
    'business': 'Бизнес',
    'premium': 'Премиум',
}

BOOL_RU = {True: 'Да', False: 'Нет'}


def rooms_distribution(segments):
    """
    Сводная таблица распределения объявлений по числу комнат
    Параметры:
        segments : dict {название сегмента: DataFrame с колонкой 'rooms'}
    """
    columns = {}
    for label, df in segments.items():
        counts = df['rooms'].value_counts().sort_index()
        columns[f'{label}, шт'] = counts
        columns[f'{label}, %'] = (counts / counts.sum() * 100).round(1)

    table = pd.DataFrame(columns).fillna(0)
    table.index.name = 'Комнат'
    return table


def price_by_building_year(df, price_col, segment_label,
                           exclude_premium=True, exclude_new_moscow=True):
    """
    Медианная цена за м² по году постройки дома + график
    По умолчанию исключает премиум-сегмент и Новую Москву, чтобы они не искажали тренд
    """
    data = df
    if exclude_premium:
        data = data[~data['is_premium']]
    if exclude_new_moscow:
        data = data[~data['is_new_moscow']]

    by_year = data.groupby('building_year')[price_col].median()

    plt.figure(figsize=(12, 5))
    plt.plot(by_year.index, by_year.values, marker='o', markersize=3, linewidth=1)
    plt.title(f'Медианная цена за м² по году постройки дома ({segment_label})')
    plt.xlabel('Год постройки')
    plt.ylabel('Цена за м²')
    plt.gca().yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, p: f'{int(x):,}'.replace(',', ' '))
    )
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

    return by_year


def price_effect_by_category(df, price_col, category_col, baseline,
                             exclude_premium=True, exclude_new_moscow=True,
                             labels=None, axis_name=None):
    """
    Влияние категориального признака на цену за м²
    Считает количество объявлений, медианную цену и относительную
    разницу к базовой категории в процентах
    Параметры:
        baseline   : значение категории (в исходном виде, до перевода), принимаемое за точку отсчёта
        labels     : dict перевода значений категории на русский, для отображения
        axis_name  : русское название признака для подписи оси/индекса
    """
    data = df
    if exclude_premium:
        data = data[~data['is_premium']]
    if exclude_new_moscow:
        data = data[~data['is_new_moscow']]

    grouped = data.groupby(category_col)[price_col]
    table = pd.DataFrame({
        'Объявлений, шт': grouped.size(),
        'Медиана цены за м²': grouped.median().round(0),
    })

    base_price = table.loc[baseline, 'Медиана цены за м²']
    table['Разница к базе, %'] = ((table['Медиана цены за м²'] / base_price - 1) * 100).round(1)

    table = table.sort_values('Медиана цены за м²')

    if labels:
        table = table.rename(index=labels)
    table.index.name = axis_name or category_col

    return table


def compare_category_across_segments(segments, category_col, baseline,
                                     exclude_premium=True, exclude_new_moscow=True,
                                     labels=None, axis_name=None):
    """
    Сравнение влияния категориального признака на цену за м² сразу в нескольких сегментах
    Параметры:
        segments   : dict {название сегмента: (DataFrame, название колонки с ценой)}
        baseline   : категория (в исходном виде), принимаемая за точку отсчёта
        labels     : dict перевода значений категории на русский, для отображения
        axis_name  : русское название признака для подписи оси/индекса
    """
    parts = {}
    for label, (df, price_col) in segments.items():
        table = price_effect_by_category(
            df, price_col, category_col, baseline,
            exclude_premium=exclude_premium,
            exclude_new_moscow=exclude_new_moscow,
            labels=labels,
        )
        parts[f'{label}, шт'] = table['Объявлений, шт']
        parts[f'{label}, медиана'] = table['Медиана цены за м²']
        parts[f'{label}, % к базе'] = table['Разница к базе, %']

    result = pd.DataFrame(parts)
    result.index.name = axis_name or category_col
    return result


def plot_category_effect(table, title):
    """
    Горизонтальная диаграмма относительной разницы цены по категориям
    Работает с таблицей из compare_category_across_segments
    """
    pct_cols = [c for c in table.columns if '% к базе' in c]
    ax = table[pct_cols].plot(kind='barh', figsize=(10, 6))
    ax.set_title(title)
    ax.set_xlabel('Разница к базе, %')
    ax.set_ylabel(table.index.name or '')
    ax.axvline(0, color='black', linewidth=0.8)
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.show()


def correlation_with_price(df, price_col, factor_cols,
                           exclude_premium=True, exclude_new_moscow=True):
    """
    Корреляция цены за м² с числовыми факторами
    Считает две меры сразу:
        Пирсон  — сила линейной связи
        Спирмен — сила монотонной связи (устойчив к выбросам и нелинейности)
    """
    data = df
    if exclude_premium:
        data = data[~data['is_premium']]
    if exclude_new_moscow:
        data = data[~data['is_new_moscow']]

    rows = {}
    for col in factor_cols:
        rows[col] = {
            'Пирсон': round(data[price_col].corr(data[col], method='pearson'), 3),
            'Спирмен': round(data[price_col].corr(data[col], method='spearman'), 3),
            'Объектов': len(data),
        }

    return pd.DataFrame(rows).T


def plot_price_vs_factor(df, price_col, factor_col, title, xlabel,
                         exclude_premium=True, exclude_new_moscow=True,
                         bins=30, sample=4000, random_state=42):
    """
    Точечная диаграмма цены от фактора + линия медианы по интервалам
    Точки прорежены (sample), чтобы график не превращался в сплошное пятно,
    линия медианы считается по всем данным
    """
    data = df
    if exclude_premium:
        data = data[~data['is_premium']]
    if exclude_new_moscow:
        data = data[~data['is_new_moscow']]

    points = data.sample(min(sample, len(data)), random_state=random_state)

    # медиана цены по интервалам фактора — сглаженный тренд поверх облака точек
    grouped = data.groupby(pd.cut(data[factor_col], bins=bins), observed=True)
    trend = grouped.agg(x=(factor_col, 'median'), y=(price_col, 'median')).dropna()

    plt.figure(figsize=(11, 5))
    plt.scatter(points[factor_col], points[price_col], s=6, alpha=0.15, label='объявления')
    plt.plot(trend['x'], trend['y'], color='crimson', linewidth=2, label='медиана по интервалам')
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel('Цена за м²')
    plt.gca().yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, p: f'{int(x):,}'.replace(',', ' '))
    )
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

    return trend


def plot_price_by_class_okrug(pivot_table, title):
    """Сгруппированная диаграмма: медианная цена за м² по округам и классам жилья"""
    ax = pivot_table.plot(kind='bar', figsize=(13, 6))
    ax.set_title(title)
    ax.set_xlabel('Округ')
    ax.set_ylabel('Медианная цена за м²')
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, p: f'{int(x):,}'.replace(',', ' '))
    )
    ax.grid(axis='y', alpha=0.3)
    ax.legend(title='Класс')
    plt.tight_layout()
    plt.show()
