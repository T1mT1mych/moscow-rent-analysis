"""Тесты для проверки «лежит ли группа на продолжении ценовой зависимости» из src/investment.py"""

import numpy as np
import pandas as pd

from src.investment import fit_price_gradient, gradient_check


def districts_on_line(offset_for_b=0.0):
    """Группа A задаёт точную зависимость value = 2 + 3 * ln(price), группа B дешевле и сдвинута на offset"""
    price_a = np.array([100, 150, 200, 300, 400], dtype=float)
    price_b = np.array([30, 45, 60, 80], dtype=float)
    return pd.DataFrame({
        'group': ['A'] * len(price_a) + ['B'] * len(price_b),
        'price': np.concatenate([price_a, price_b]),
        'value': np.concatenate([2 + 3 * np.log(price_a),
                                 2 + 3 * np.log(price_b) + offset_for_b]),
    })


def test_fit_recovers_exact_line():
    data = districts_on_line()
    predict = fit_price_gradient(data[data['group'] == 'A'], 'price', 'value')
    assert np.isclose(predict(50.0), 2 + 3 * np.log(50.0))


def test_group_on_extension_has_zero_residual():
    result = gradient_check(districts_on_line(), 'price', 'value', 'group', 'A')
    assert abs(result.loc['B', 'mean_residual']) < 0.1


def test_shifted_group_shows_its_offset():
    """Если группа B систематически выше линии, остаток должен это показать"""
    result = gradient_check(districts_on_line(offset_for_b=2.0), 'price', 'value', 'group', 'A')
    assert abs(result.loc['B', 'mean_residual'] - 2.0) < 0.1
    assert abs(result.loc['A', 'mean_residual']) < 0.1
