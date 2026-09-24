"""Тесты для src/segmentation.py"""

import matplotlib
matplotlib.use('Agg')  # без графического дисплея — тесты рисуют в никуда

import matplotlib.pyplot as plt
import pandas as pd

import pytest

from src.segmentation import (
    add_premium_flag,
    add_premium_flag_by_year,
    compare_premium_methods,
    add_new_moscow_flag,
    compare_old_vs_new_moscow_median,
    plot_old_vs_new_moscow_boxplot,
    plot_new_moscow_share_pie,
)


def two_year_frame():
    """
    Две группы по году: во втором году цены на порядок выше, в каждом свой выброс

    Числа подобраны так, что выброс 2020 года (30) выше порога своего года,
    но ниже общего порога по всей выборке — это и есть ситуация, которую
    старый метод не ловил
    """
    return pd.DataFrame({
        'date_posted': ['2020-03-01'] * 6 + ['2021-07-01'] * 6,
        'price': [10, 11, 12, 13, 14, 30,
                  100, 110, 120, 130, 140, 300],
    })


def test_add_premium_flag_marks_outlier():
    df = pd.DataFrame({'price': [10, 20, 30, 40, 50, 60, 1000]})
    result = add_premium_flag(df.copy(), 'price')
    assert result['is_premium'].iloc[-1] == True
    assert result['is_premium'].iloc[0] == False


def test_add_premium_flag_returns_bool_dtype():
    df = pd.DataFrame({'price': [10, 20, 30, 40, 50]})
    result = add_premium_flag(df.copy(), 'price')
    assert result['is_premium'].dtype == bool


def test_add_premium_flag_all_equal_values():
    # Граничный случай: при одинаковых ценах IQR = 0, порог совпадает
    # со значением, и из-за `>=` премиумом помечаются все строки —
    # так ведёт себя код сейчас, тест фиксирует это поведение
    df = pd.DataFrame({'price': [100, 100, 100, 100]})
    result = add_premium_flag(df.copy(), 'price')
    assert result['is_premium'].all()


def test_by_year_marks_outlier_in_each_year():
    # Порог считается внутри года, поэтому выброс находится в обоих годах,
    # хотя дорогой объект 2020 года дешевле обычных объектов 2021-го
    result = add_premium_flag_by_year(two_year_frame(), 'price')
    assert list(result['is_premium']) == [False] * 5 + [True] + [False] * 5 + [True]


def test_by_year_differs_from_global_threshold():
    # Общий порог по всей выборке пропустил бы выброс 2020 года (500 < порога),
    # порог года его ловит — ровно та ошибка, ради которой метод и менялся
    df = two_year_frame()
    by_year = add_premium_flag_by_year(df.copy(), 'price')['is_premium']
    global_flag = add_premium_flag(df.copy(), 'price')['is_premium']
    assert by_year.iloc[5] and not global_flag.iloc[5]


def test_by_year_returns_bool_dtype():
    result = add_premium_flag_by_year(two_year_frame(), 'price')
    assert result['is_premium'].dtype == bool


def test_by_year_rejects_missing_dates():
    df = two_year_frame()
    df.loc[0, 'date_posted'] = None
    with pytest.raises(ValueError, match='пропуски'):
        add_premium_flag_by_year(df, 'price')


def test_compare_premium_methods_table():
    table = compare_premium_methods(two_year_frame(), 'price')
    assert list(table.index) == [2020, 2021]
    assert list(table['Объявлений']) == [6, 6]
    # выброс 2020 года не проходит общий порог, но проходит порог своего года
    assert table.loc[2020, 'Сменили метку, шт'] == 1
    assert table.attrs['global_threshold'] > 0


def test_add_new_moscow_flag():
    df = pd.DataFrame({'okrug': ['TAO', 'CAO', 'ZelAO', 'SAO', 'NAO']})
    result = add_new_moscow_flag(df.copy())
    assert list(result['is_new_moscow']) == [True, False, True, False, True]


def test_compare_old_vs_new_moscow_median_does_not_raise(capsys):
    df = pd.DataFrame({
        'price': [100, 200, 300, 10, 20, 30],
        'is_new_moscow': [False, False, False, True, True, True],
    })
    compare_old_vs_new_moscow_median(df, 'price')
    captured = capsys.readouterr()
    assert 'Старая Москва' in captured.out
    assert 'Новая Москва' in captured.out


def test_plot_old_vs_new_moscow_boxplot_does_not_raise():
    df = pd.DataFrame({
        'price': [100, 200, 300, 10, 20, 30],
        'is_new_moscow': [False, False, False, True, True, True],
    })
    plot_old_vs_new_moscow_boxplot(df, 'price', 'тест')
    plt.close('all')


def test_plot_new_moscow_share_pie_does_not_raise():
    df = pd.DataFrame({'is_new_moscow': [True, False, False, True, False]})
    plot_new_moscow_share_pie(df)
    plt.close('all')
