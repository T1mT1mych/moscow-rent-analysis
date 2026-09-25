"""Статистическая проверка различий между группами и сравнение распределений"""

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib.pyplot as plt

from src.plot_style import ACCENT, INK_SECONDARY


def _effect_size_label(r):
    """Словесная оценка величины эффекта по общепринятым порогам"""
    r = abs(r)
    if r < 0.1:
        return 'пренебрежимо мал'
    if r < 0.3:
        return 'малый'
    if r < 0.5:
        return 'средний'
    return 'большой'


def compare_groups(sample_a, sample_b, label_a, label_b, comparison_name):
    """
    Сравнение двух групп критерием Манна-Уитни

    Почему именно он: цены распределены сильно несимметрично, с длинным правым хвостом,
    поэтому t-критерий с его требованием нормальности здесь не подходит.
    Манна-Уитни работает с рангами, никаких предположений о форме распределения не делает
    и сравнивает распределения целиком, а не только средние

    Кроме p-value обязательно считаем размер эффекта (ранговая бисериальная корреляция):
    на больших выборках статистически значимым становится любое, даже ничтожное различие,
    и без размера эффекта p-value ничего не говорит о практической важности
    """
    a = sample_a.dropna()
    b = sample_b.dropna()

    u_statistic, p_value = stats.mannwhitneyu(a, b, alternative='two-sided')
    effect = 1 - 2 * u_statistic / (len(a) * len(b))

    return {
        'Сравнение': comparison_name,
        f'n ({label_a})': len(a),
        f'n ({label_b})': len(b),
        f'Медиана ({label_a})': round(a.median(), 1),
        f'Медиана ({label_b})': round(b.median(), 1),
        'Разница, %': round((a.median() / b.median() - 1) * 100, 1),
        'p-value': p_value,
        'Размер эффекта': round(abs(effect), 3),
        'Оценка эффекта': _effect_size_label(effect),
    }


def comparison_table(results):
    """Собирает результаты нескольких сравнений в одну таблицу"""
    rows = []
    for result in results:
        rows.append({
            'Сравнение': result['Сравнение'],
            'Разница медиан, %': result['Разница, %'],
            'p-value': f"{result['p-value']:.2e}" if result['p-value'] > 0 else '< 1e-300',
            'Значимо (p<0.05)': 'да' if result['p-value'] < 0.05 else 'нет',
            'Размер эффекта': result['Размер эффекта'],
            'Оценка': result['Оценка эффекта'],
        })
    return pd.DataFrame(rows)


def distribution_shape(series, label):
    """
    Метрики формы распределения, не зависящие от масштаба цен
    Нужны, чтобы сравнивать сегменты с разными уровнями цен между собой
    """
    s = series.dropna()
    q1, median, q3 = s.quantile([0.25, 0.5, 0.75])
    p10, p90 = s.quantile([0.10, 0.90])
    return {
        'Сегмент': label,
        'Объектов': len(s),
        'Медиана': round(median, 1),
        'Разброс IQR / медиана': round((q3 - q1) / median, 3),
        'P90 / P10': round(p90 / p10, 2),
        'Коэф. вариации': round(s.std() / s.mean(), 3),
        'Асимметрия': round(s.skew(), 2),
    }


def plot_normalized_distributions(segments, title, bins=60, clip=3.0):
    """
    Распределения нескольких сегментов на одном графике

    Каждый сегмент делится на собственную медиану, поэтому все кривые
    оказываются в одном масштабе вокруг 1.0 — сравнивается форма
    распределения, а не уровень цен
    """
    plt.figure(figsize=(12, 5))

    for label, series in segments.items():
        normalized = (series.dropna() / series.median())
        normalized = normalized[normalized <= clip]
        plt.hist(normalized, bins=bins, alpha=0.45, density=True, label=label)

    plt.axvline(1.0, color=INK_SECONDARY, linewidth=1, linestyle='--', label='медиана сегмента')
    plt.title(title)
    plt.xlabel('Цена относительно медианы своего сегмента')
    plt.ylabel('Плотность')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_normalized_boxplots(segments, title, clip=3.0):
    """Те же нормированные распределения, но боксплотами — виднее хвосты и выбросы"""
    data, labels = [], []
    for label, series in segments.items():
        normalized = series.dropna() / series.median()
        data.append(normalized[normalized <= clip])
        labels.append(label)

    plt.figure(figsize=(10, 5))
    plt.boxplot(data, orientation='horizontal', tick_labels=labels)
    plt.axvline(1.0, color=ACCENT, linewidth=1, linestyle='--')
    plt.title(title)
    plt.xlabel('Цена относительно медианы своего сегмента')
    plt.grid(axis='x')
    plt.tight_layout()
    plt.show()
