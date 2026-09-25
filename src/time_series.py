"""Анализ временной динамики рынка"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.plot_style import THOUSANDS as _THOUSANDS, ACCENT, INK_SECONDARY, MUTED, PRIMARY


def city_monthly_series(df):
    """
    Сводит помесячную статистику по районам к общегородскому ряду
    Цены берём как медиану по районам, ставки — как есть (они одинаковы для всех районов месяца)
    Дополнительно считаем помесячный прирост цен в процентах
    """
    series = df.groupby('year_month').agg(
        secondary=('secondary_price_per_sqm', 'median'),
        newbuild=('newbuild_price_per_sqm', 'median'),
        rental=('rental_price_per_sqm_monthly', 'median'),
        key_rate=('cbr_key_rate_pct', 'first'),
        mortgage_rate=('avg_mortgage_rate_pct', 'first'),
    ).sort_index()

    for col in ['secondary', 'newbuild', 'rental']:
        series[f'{col}_mom'] = series[col].pct_change() * 100

    return series


def plot_price_index(series, cols, labels, title):
    """
    Индекс цен: все сегменты приведены к 100 в первом месяце
    Нужно, чтобы сравнить сегменты с разным масштабом цен на одном графике
    """
    plt.figure(figsize=(12, 5))
    for col, label in zip(cols, labels):
        index = series[col] / series[col].iloc[0] * 100
        plt.plot(series.index, index, linewidth=1.8, label=label)

    plt.axhline(100, color=MUTED, linewidth=0.8, linestyle='--')
    plt.title(title)
    plt.xlabel('Месяц')
    plt.ylabel('Индекс цены, первый месяц = 100')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_price_and_rate(series, price_col, price_label, title):
    """
    Цена и ставки — две панели одна под другой с общей шкалой времени

    Не одна панель с двумя осями Y: у цены и ставки разные единицы, и выравнивание
    двух шкал произвольно — оно само рисует «связь», которую надо проверять
    расчётом (это делает lagged_correlation). Прежняя версия с двумя осями
    сохранена как plot_price_and_rate_dual_axis, чтобы старый график воспроизводился
    """
    fig, (ax_price, ax_rate) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                            gridspec_kw={'height_ratios': [3, 2]})

    ax_price.plot(series.index, series[price_col], color=PRIMARY, label=price_label)
    ax_price.set_ylabel(f'{price_label}, руб/м²')
    ax_price.yaxis.set_major_formatter(_THOUSANDS)
    ax_price.grid(True)
    ax_price.set_title(title)

    ax_rate.plot(series.index, series['key_rate'], color=ACCENT, drawstyle='steps-post',
                 label='Ключевая ставка ЦБ')
    ax_rate.plot(series.index, series['mortgage_rate'], color=MUTED, drawstyle='steps-post',
                 label='Средняя ставка по ипотеке')
    ax_rate.set_ylabel('Ставка, % годовых')
    ax_rate.set_xlabel('Месяц')
    ax_rate.grid(True)
    ax_rate.legend(loc='upper left')

    plt.tight_layout()
    plt.show()


def plot_price_and_rate_dual_axis(series, price_col, price_label, title):
    """
    Устаревшая версия: цена и ставки на одном графике с двумя осями Y

    Оставлена только для воспроизводимости прежнего вида раздела 8.2.1.
    Для новых графиков — plot_price_and_rate
    """
    fig, ax_price = plt.subplots(figsize=(12, 5))

    ax_price.plot(series.index, series[price_col], color='steelblue', linewidth=2, label=price_label)
    ax_price.set_xlabel('Месяц')
    ax_price.set_ylabel(f'{price_label}, руб/м²', color='steelblue')
    ax_price.tick_params(axis='y', labelcolor='steelblue')
    ax_price.yaxis.set_major_formatter(_THOUSANDS)
    ax_price.grid(True)

    ax_rate = ax_price.twinx()
    ax_rate.plot(series.index, series['key_rate'], color='crimson', linewidth=1.5, label='Ключевая ставка ЦБ')
    ax_rate.plot(series.index, series['mortgage_rate'], color='darkorange',
                 linewidth=1.5, linestyle='--', label='Средняя ставка по ипотеке')
    ax_rate.set_ylabel('Ставка, % годовых', color='crimson')
    ax_rate.tick_params(axis='y', labelcolor='crimson')

    lines = ax_price.get_lines() + ax_rate.get_lines()
    ax_price.legend(lines, [line.get_label() for line in lines], loc='upper left')

    plt.title(title)
    plt.tight_layout()
    plt.show()


def lagged_correlation(series, change_col, rate_col, max_lag=6):
    """
    Корреляция помесячного прироста цены со ставкой при разных сдвигах
    Лаг N означает: сравниваем прирост цены с уровнем ставки N месяцев назад,
    то есть проверяем, влияет ли ставка на рынок с задержкой
    """
    rows = []
    for lag in range(max_lag + 1):
        corr = series[change_col].corr(series[rate_col].shift(lag))
        rows.append({'Лаг, мес': lag, 'Корреляция': round(corr, 3)})
    return pd.DataFrame(rows)


def plot_lagged_correlation(table, title):
    """Диаграмма корреляции по лагам — где столбик выше по модулю, там связь сильнее"""
    plt.figure(figsize=(10, 4.5))
    colors = [ACCENT if v < 0 else PRIMARY for v in table['Корреляция']]
    plt.bar(table['Лаг, мес'], table['Корреляция'], color=colors)
    plt.axhline(0, color=INK_SECONDARY, linewidth=0.8)
    plt.title(title)
    plt.xlabel('Сдвиг ставки назад, месяцев')
    plt.ylabel('Корреляция с приростом цены')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.show()


def forecast_linear_trend(series, col, history_months=24, periods=6):
    """
    Простой прогноз: прямая линия тренда, построенная по последним history_months,
    продлённая на periods месяцев вперёд
    Метод намеренно примитивный — он не знает ни про сезонность, ни про ставки,
    и годится только как ориентир «если всё продолжится как сейчас»
    """
    history = series[col].dropna().iloc[-history_months:]
    x = np.arange(len(history))
    slope, intercept = np.polyfit(x, history.values, 1)

    future_x = np.arange(len(history), len(history) + periods)
    future_values = slope * future_x + intercept
    future_index = pd.date_range(history.index[-1], periods=periods + 1, freq='MS')[1:]

    forecast = pd.Series(future_values, index=future_index)
    return forecast, slope


def plot_forecast(series, col, forecast, title, history_months=24):
    """График: фактический ряд, участок обучения тренда и прогноз"""
    plt.figure(figsize=(12, 5))
    plt.plot(series.index, series[col], color=PRIMARY, linewidth=1.8, label='Факт')

    trend_start = series.index[-history_months]
    plt.axvspan(trend_start, series.index[-1], color=PRIMARY, alpha=0.08,
                label=f'Участок построения тренда ({history_months} мес)')

    bridge = pd.concat([series[col].iloc[[-1]], forecast])
    plt.plot(bridge.index, bridge.values, color=ACCENT, linewidth=2,
             linestyle='--', marker='o', markersize=4, label='Прогноз')

    plt.title(title)
    plt.xlabel('Месяц')
    plt.ylabel('Цена за м²')
    plt.gca().yaxis.set_major_formatter(_THOUSANDS)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()
