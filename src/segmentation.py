"""Функции для сегментации рынка недвижимости (премиум, Новая Москва)"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker

NEW_MOSCOW_OKRUGS = ['TAO', 'NAO', 'ZelAO']


def premium_threshold(prices):
    """Порог премиум-сегмента методом IQR: Q3 + 1.5 × (Q3 − Q1)"""
    q1 = prices.quantile(0.25)
    q3 = prices.quantile(0.75)
    return q3 + 1.5 * (q3 - q1)


def add_premium_flag(df, price_col, verbose=True):
    """
    Премиум-сегмент по ОБЩЕМУ порогу IQR, посчитанному на всей выборке сразу

    УСТАРЕЛО — в пайплайне больше не используется, см. add_premium_flag_by_year

    Проверка 8.5.2 показала, что этот метод неверен на данных за несколько лет:
    цены за 2020-2026 выросли на 55%, порог зафиксирован на среднем уровне
    периода, и в итоге доля премиума растёт с 2.0% до 8.0% просто по годам.
    То есть флаг частично кодирует «объявление размещено позже», а не «дорогое
    жильё». Функция оставлена намеренно — чтобы ошибку можно было воспроизвести
    и показать сравнение «было / стало», а не молча переписать историю

    Параметры:
        df        : DataFrame с данными объявлений
        price_col : название колонки с ценой за м²
    """
    Q1 = df[price_col].quantile(0.25)
    Q3 = df[price_col].quantile(0.75)
    IQR = Q3 - Q1
    threshold = Q3 + 1.5 * IQR

    df['is_premium'] = df[price_col] >= threshold

    if verbose:
        print(f"Q1 = {Q1:.0f}")
        print(f"Q3 = {Q3:.0f}")
        print(f"IQR = {IQR:.0f}")
        print(f"Порог премиум-сегмента: {threshold:.0f}")
        print(df['is_premium'].value_counts())
        print(f"\nДоля премиум-сегмента: {df['is_premium'].mean()*100:.1f}%")

    return df


def add_premium_flag_by_year(df, price_col, date_col='date_posted', verbose=True):
    """
    Премиум-сегмент методом IQR, посчитанным ВНУТРИ каждого года публикации

    Основной метод проекта. Порог считается отдельно по объявлениям каждого
    года, поэтому is_premium означает «дорогое относительно своего времени»,
    а не «дорогое по меркам усреднённого шестилетия»

    Параметры:
        df        : DataFrame с данными объявлений
        price_col : название колонки с ценой за м²
        date_col  : колонка с датой публикации, из неё берётся год
    """
    year = pd.to_datetime(df[date_col]).dt.year

    if year.isna().any():
        raise ValueError(
            f"В колонке {date_col} есть пропуски — для этих строк год неизвестен "
            f"и порог посчитать не из чего ({int(year.isna().sum())} строк)"
        )

    thresholds = df.groupby(year)[price_col].transform(premium_threshold)
    df['is_premium'] = df[price_col] >= thresholds

    if verbose:
        table = pd.DataFrame({
            'Объявлений': year.groupby(year).size(),
            'Порог года': df.groupby(year)[price_col].apply(premium_threshold).round(0),
            'Премиум, шт': df['is_premium'].groupby(year).sum(),
            'Премиум, %': (df['is_premium'].groupby(year).mean() * 100).round(1),
        })
        table.index.name = 'Год'
        print(table.to_string())
        print(f"\nВсего премиум-сегмента: {df['is_premium'].sum()} "
              f"({df['is_premium'].mean()*100:.1f}%)")

    return df


def compare_premium_methods(df, price_col, date_col='date_posted'):
    """
    Сравнение двух методов расчёта премиум-сегмента: общий порог против порога года

    Показывает по годам, как расходятся доли премиума, и сколько объявлений
    в итоге меняют метку. Нужна, чтобы исправление методики было видно в
    ноутбуке числами, а не только на словах

    Возвращает таблицу по годам; сводка по всей выборке печатается
    """
    year = pd.to_datetime(df[date_col]).dt.year
    global_threshold = premium_threshold(df[price_col])

    by_global = df[price_col] >= global_threshold
    by_year = df[price_col] >= df.groupby(year)[price_col].transform(premium_threshold)

    table = pd.DataFrame({
        'Объявлений': year.groupby(year).size(),
        'Порог года': df.groupby(year)[price_col].apply(premium_threshold).round(0),
        'Премиум по общему порогу, %': (by_global.groupby(year).mean() * 100).round(1),
        'Премиум по порогу года, %': (by_year.groupby(year).mean() * 100).round(1),
        'Сменили метку, шт': (by_global != by_year).groupby(year).sum(),
    })
    table.index.name = 'Год'
    table.attrs['global_threshold'] = round(global_threshold)

    lost = (by_global & ~by_year).sum()
    gained = (~by_global & by_year).sum()

    print(f"Общий порог по всей выборке: {global_threshold:,.0f}".replace(',', ' '))
    print(f"Премиум по общему порогу:  {by_global.sum()} ({by_global.mean()*100:.1f}%)")
    print(f"Премиум по порогу года:    {by_year.sum()} ({by_year.mean()*100:.1f}%)")
    print(f"\nСменили метку: {lost + gained} объявлений из {len(df)} "
          f"({(lost + gained) / len(df) * 100:.1f}%)")
    print(f"  были премиумом, перестали: {lost}")
    print(f"  не были премиумом, стали:  {gained}")

    return table


def threshold_stability(df, price_col, period_col, global_threshold=None):
    """
    Проверка устойчивости порога премиум-сегмента во времени

    Считает для каждого периода собственный порог IQR и сравнивает два подхода:
      - сколько объектов периода попадает в премиум по общему порогу (как сейчас в проекте)
      - сколько попадает по порогу, посчитанному внутри самого периода

    Если доли сильно расходятся, значит общий порог смешивает «дорогое жильё»
    с «объявлением, размещённым позже» — цены-то со временем растут
    """
    if global_threshold is None:
        global_threshold = premium_threshold(df[price_col])

    rows = []
    for period, group in df.groupby(period_col):
        local = premium_threshold(group[price_col])
        rows.append({
            'Период': period,
            'Объявлений': len(group),
            'Порог периода': round(local),
            'Премиум по общему порогу, %': round((group[price_col] >= global_threshold).mean() * 100, 1),
            'Премиум по порогу периода, %': round((group[price_col] >= local).mean() * 100, 1),
        })

    table = pd.DataFrame(rows).set_index('Период')
    table.attrs['global_threshold'] = round(global_threshold)
    return table


def plot_threshold_stability(table, title):
    """Два графика: как ездит сам порог и как из-за этого меняется доля премиума"""
    global_threshold = table.attrs.get('global_threshold')

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    ax1.plot(table.index, table['Порог периода'], marker='o', linewidth=2,
             color='steelblue', label='Порог, посчитанный внутри периода')
    if global_threshold:
        ax1.axhline(global_threshold, color='crimson', linestyle='--', linewidth=1.5,
                    label=f'Общий порог по всем данным ({global_threshold:,})'.replace(',', ' '))
    ax1.set_ylabel('Порог премиум-сегмента')
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{int(x):,}'.replace(',', ' ')))
    ax1.set_title(title)
    ax1.grid(alpha=0.3)
    ax1.legend()

    ax2.plot(table.index, table['Премиум по общему порогу, %'], marker='o', linewidth=2,
             color='crimson', label='Доля премиума по общему порогу')
    ax2.plot(table.index, table['Премиум по порогу периода, %'], marker='s', linewidth=2,
             color='steelblue', label='Доля премиума по порогу периода')
    ax2.set_ylabel('Доля премиум-сегмента, %')
    ax2.set_xlabel('Период')
    ax2.grid(alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    plt.show()


def add_new_moscow_flag(df):
    """
    Помечает объекты в Новой Москве (округа TAO, NAO, ZelAO)
    Параметры:
        df : DataFrame с колонкой okrug
    """
    df['is_new_moscow'] = df['okrug'].isin(NEW_MOSCOW_OKRUGS)

    print(df['is_new_moscow'].value_counts())
    print(f"Доля Новой Москвы: {df['is_new_moscow'].mean()*100:.1f}%")

    return df


def compare_old_vs_new_moscow_median(df, price_col):
    """Печатает медиану цены за м² для старой и Новой Москвы"""
    old_moscow_median = df[~df['is_new_moscow']][price_col].median()
    new_moscow_median = df[df['is_new_moscow']][price_col].median()

    print(f"Старая Москва, медиана {price_col}: {old_moscow_median:,.0f}")
    print(f"Новая Москва, медиана {price_col}: {new_moscow_median:,.0f}")
    print(f"Разница: в {old_moscow_median/new_moscow_median:.1f} раз")


def plot_old_vs_new_moscow_boxplot(df, price_col, segment_label):
    """
    Горизонтальный боксплот цены за м²: старая vs Новая Москва
    Параметры:
        segment_label : подпись сегмента для заголовка ('съем', 'вторичка', 'новостройки')
    """
    old_moscow = df[~df['is_new_moscow']][price_col]
    new_moscow = df[df['is_new_moscow']][price_col]

    plt.figure(figsize=(10, 5))
    plt.boxplot([old_moscow, new_moscow], orientation='horizontal', tick_labels=['Старая Москва', 'Новая Москва'])
    plt.title(f'Цена за м² ({segment_label}): старая vs Новая Москва')
    plt.xlabel('Цена за м²')
    plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{int(x):,}'.replace(',', ' ')))
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_new_moscow_share_pie(df):
    """Круговая диаграмма доли объявлений: старая vs Новая Москва"""
    counts = df['is_new_moscow'].value_counts()
    labels = ['Старая Москва', 'Новая Москва']

    plt.figure(figsize=(4, 4))
    plt.pie(counts, labels=labels, autopct='%1.1f%%', colors=['steelblue', 'lightcoral'])
    plt.title('Доля объявлений: старая vs Новая Москва')
    plt.show()
