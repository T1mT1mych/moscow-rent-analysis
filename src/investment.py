"""Инвестиционная аналитика: окупаемость, наценка новостроек, рейтинг районов"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker

from src.plot_style import THOUSANDS as _THOUSANDS, INK, MUTED, PART_COLORS, PRIMARY


def payback_by_segment(df_secondary, df_rentals, group_cols,
                       exclude_premium=True, exclude_new_moscow=True, min_count=30):
    """
    Окупаемость покупки за счёт аренды в разрезе произвольных признаков

    Окупаемость = цена за м² / (арендная ставка за м² × 12).
    Показывает, за сколько лет аренда «вернёт» стоимость покупки, если не учитывать
    ни налоги, ни простои, ни расходы на содержание — это валовая оценка сверху

    Параметры:
        group_cols : список колонок, по которым режем (должны быть в обеих таблицах)
        min_count  : группы меньше этого размера отбрасываем как ненадёжные
    """
    sec, rent = df_secondary, df_rentals
    if exclude_premium:
        sec, rent = sec[~sec['is_premium']], rent[~rent['is_premium']]
    if exclude_new_moscow:
        sec, rent = sec[~sec['is_new_moscow']], rent[~rent['is_new_moscow']]

    sec_agg = sec.groupby(group_cols).agg(
        price_sqm=('price_per_sqm', 'median'),
        n_sale=('price_per_sqm', 'size'),
    )
    rent_agg = rent.groupby(group_cols).agg(
        rent_sqm=('rent_per_sqm', 'median'),
        n_rent=('rent_per_sqm', 'size'),
    )

    table = sec_agg.join(rent_agg, how='inner')
    table = table[(table['n_sale'] >= min_count) & (table['n_rent'] >= min_count)]

    table['Окупаемость, лет'] = (table['price_sqm'] / (table['rent_sqm'] * 12)).round(1)
    table['Доходность, % годовых'] = (table['rent_sqm'] * 12 / table['price_sqm'] * 100).round(2)

    return table.sort_values('Окупаемость, лет')


def plot_payback_bars(table, index_labels, title):
    """Горизонтальная диаграмма окупаемости — чем короче столбик, тем быстрее возврат"""
    data = table.sort_values('Окупаемость, лет', ascending=False)

    plt.figure(figsize=(10, max(4, len(data) * 0.45)))
    plt.barh([index_labels.get(i, str(i)) for i in data.index],
             data['Окупаемость, лет'], color=PRIMARY)
    plt.title(title)
    plt.xlabel('Окупаемость, лет')
    plt.grid(axis='x')
    plt.tight_layout()
    plt.show()


def plot_yield_growth_quadrants(data, yield_col, growth_col, label_col, title, top_labels=8):
    """
    Districts на плоскости «доходность аренды × рост цены»
    Деление на четверти по медианам: правый верхний угол — районы,
    которые одновременно и хорошо сдаются, и дорожают
    """
    yield_median = data[yield_col].median()
    growth_median = data[growth_col].median()

    plt.figure(figsize=(11, 8))
    plt.scatter(data[yield_col], data[growth_col], s=45, alpha=0.65, color=PRIMARY)

    plt.axvline(yield_median, color=MUTED, linestyle='--', linewidth=1)
    plt.axhline(growth_median, color=MUTED, linestyle='--', linewidth=1)

    # подписываем только самые интересные точки, иначе график превратится в кашу
    best = data.assign(_score=data[yield_col].rank() + data[growth_col].rank())
    best = best.nlargest(top_labels, '_score')
    for _, row in best.iterrows():
        plt.annotate(row[label_col], (row[yield_col], row[growth_col]),
                     fontsize=8, xytext=(4, 4), textcoords='offset points')

    plt.title(title)
    plt.xlabel('Доходность аренды, % годовых')
    plt.ylabel('Рост цены за 24 месяца, %')
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def composite_ranking(data, columns_higher_better, weights=None):
    """
    Сводный рейтинг: каждый показатель приводится к шкале 0-1 (min-max),
    затем складывается с весами

    Веса — это управленческое решение, а не расчёт. Меняя их, меняешь и рейтинг,
    поэтому набор весов всегда нужно указывать рядом с результатом
    """
    normalized = pd.DataFrame(index=data.index)
    for col in columns_higher_better:
        low, high = data[col].min(), data[col].max()
        normalized[col] = (data[col] - low) / (high - low)

    if weights is None:
        weights = {col: 1 / len(columns_higher_better) for col in columns_higher_better}

    score = sum(normalized[col] * weight for col, weight in weights.items())
    result = data.copy()
    result['Балл'] = (score * 100).round(1)
    return result.sort_values('Балл', ascending=False)


def fit_price_gradient(reference, price_col, value_col):
    """
    Линейная зависимость показателя от логарифма цены: value = a + b * ln(price)

    Логарифм — потому что цены по районам различаются в разы, и одинаковый
    относительный шаг цены должен давать одинаковый сдвиг показателя.
    Возвращает функцию, которая по цене считает ожидаемое значение
    """
    b, a = np.polyfit(np.log(reference[price_col]), reference[value_col], 1)
    return lambda price: a + b * np.log(price)


def gradient_check(districts, price_col, value_col, group_col, reference_value):
    """
    Лежит ли другая группа районов на продолжении зависимости референсной группы

    Зависимость подбирается только по референсной группе и продлевается на
    остальные районы. Если средний остаток около нуля, различие между
    группами целиком объясняется уровнем цен, а не принадлежностью к группе
    """
    reference = districts[districts[group_col] == reference_value]
    predict = fit_price_gradient(reference, price_col, value_col)

    result = districts[[group_col, price_col, value_col]].copy()
    result['Ожидалось по цене'] = predict(result[price_col]).round(1)
    result['Остаток'] = (result[value_col] - result['Ожидалось по цене']).round(1)

    return result.groupby(group_col).agg(
        n=(value_col, 'size'),
        median_price=(price_col, 'median'),
        median_actual=(value_col, 'median'),
        median_expected=('Ожидалось по цене', 'median'),
        mean_residual=('Остаток', 'mean'),
    ).round(1)


def plot_price_gradient(districts, price_col, value_col, group_col, reference_value,
                        title, ylabel):
    """
    Районы на плоскости «цена × показатель» с линией зависимости,
    подобранной только по референсной группе и продлённой на весь диапазон цен
    """
    reference = districts[districts[group_col] == reference_value]
    predict = fit_price_gradient(reference, price_col, value_col)

    plt.figure(figsize=(11, 6))
    for value, group in districts.groupby(group_col):
        plt.scatter(group[price_col], group[value_col], s=40, alpha=0.8, label=str(value),
                    color=PART_COLORS.get(value), edgecolors='white', linewidths=0.6)

    grid = np.geomspace(districts[price_col].min(), districts[price_col].max(), 100)
    plt.plot(grid, predict(grid), color=INK, linewidth=1.5,
             label=f'зависимость по группе «{reference_value}»')
    ref_low = reference[price_col].min()
    plt.axvspan(grid[0], ref_low, color=MUTED, alpha=0.1,
                label='диапазон цен вне референсной группы')

    plt.xscale('log')
    plt.gca().xaxis.set_major_formatter(_THOUSANDS)
    plt.gca().xaxis.set_minor_formatter(ticker.NullFormatter())
    nice = [25_000, 50_000, 75_000, 100_000, 150_000, 200_000, 300_000, 400_000, 600_000]
    plt.xticks([t for t in nice if grid[0] <= t <= grid[-1]])
    plt.title(title)
    plt.xlabel('Средняя цена вторички без премиума, руб/м² (логарифмическая шкала)')
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
