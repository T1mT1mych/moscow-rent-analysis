"""Инвестиционная аналитика: окупаемость, наценка новостроек, рейтинг районов"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker

_THOUSANDS = ticker.FuncFormatter(lambda x, p: f'{int(x):,}'.replace(',', ' '))


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
             data['Окупаемость, лет'], color='steelblue')
    plt.title(title)
    plt.xlabel('Окупаемость, лет')
    plt.grid(axis='x', alpha=0.3)
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
    plt.scatter(data[yield_col], data[growth_col], s=45, alpha=0.65, color='steelblue')

    plt.axvline(yield_median, color='grey', linestyle='--', linewidth=1)
    plt.axhline(growth_median, color='grey', linestyle='--', linewidth=1)

    # подписываем только самые интересные точки, иначе график превратится в кашу
    best = data.assign(_score=data[yield_col].rank() + data[growth_col].rank())
    best = best.nlargest(top_labels, '_score')
    for _, row in best.iterrows():
        plt.annotate(row[label_col], (row[yield_col], row[growth_col]),
                     fontsize=8, xytext=(4, 4), textcoords='offset points')

    plt.title(title)
    plt.xlabel('Доходность аренды, % годовых')
    plt.ylabel('Рост цены за 24 месяца, %')
    plt.grid(alpha=0.3)
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
