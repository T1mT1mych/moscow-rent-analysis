"""Регрессионная модель прогноза цены за м²"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, root_mean_squared_error

import matplotlib.pyplot as plt
from matplotlib import ticker

from src.plot_style import ACCENT


def build_features(df, numeric_cols, categorical_cols):
    """
    Готовит матрицу признаков для модели
    Числовые колонки берём как есть, категориальные разворачиваем в набор
    бинарных колонок (one-hot), потому что модель умеет работать только с числами
    Параметры:
        df               : исходный DataFrame
        numeric_cols     : числовые и бинарные признаки
        categorical_cols : текстовые признаки под one-hot кодирование
    """
    X_numeric = df[numeric_cols].astype(float)
    X_categorical = pd.get_dummies(df[categorical_cols], drop_first=True, dtype=float)
    return pd.concat([X_numeric, X_categorical], axis=1)


def fit_price_model(df, target_col, numeric_cols, categorical_cols,
                    test_size=0.2, random_state=42):
    """
    Обучает линейную регрессию прогноза цены за м² и печатает качество модели
    Данные делятся на обучающую и тестовую части: модель учится на первой,
    а качество измеряется на второй — на данных, которых она не видела
    Возвращает: (модель, таблица коэффициентов, словарь метрик, тестовые данные)
    """
    X = build_features(df, numeric_cols, categorical_cols)
    y = df[target_col].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    metrics = {
        'R2': round(r2_score(y_test, y_pred), 3),
        'MAE': round(mean_absolute_error(y_test, y_pred), 0),
        'RMSE': round(root_mean_squared_error(y_test, y_pred), 0),
        'Средняя цена в тесте': round(y_test.mean(), 0),
    }

    print(f"Объектов: {len(X):,} (обучение {len(X_train):,} / тест {len(X_test):,}), признаков: {X.shape[1]}")
    print(f"R²   = {metrics['R2']} — доля разброса цены, объяснённая моделью")
    print(f"MAE  = {metrics['MAE']:,.0f} руб/м² — средняя ошибка прогноза".replace(',', ' '))
    print(f"RMSE = {metrics['RMSE']:,.0f} руб/м² — та же ошибка, но с большим штрафом за грубые промахи".replace(',', ' '))
    print(f"Для сравнения, средняя цена в тесте: {metrics['Средняя цена в тесте']:,.0f} руб/м²".replace(',', ' '))
    print(f"Относительная ошибка: {metrics['MAE'] / metrics['Средняя цена в тесте'] * 100:.1f}%")

    coefficients = pd.DataFrame({
        'Признак': X.columns,
        'Коэффициент': np.round(model.coef_, 1),
    }).sort_values('Коэффициент', key=abs, ascending=False).reset_index(drop=True)

    return model, coefficients, metrics, (X_test, y_test, y_pred)


def plot_predictions(y_test, y_pred, title):
    """
    График «прогноз против факта»: чем ближе точки к диагонали, тем точнее модель
    """
    plt.figure(figsize=(7, 7))
    plt.scatter(y_test, y_pred, s=6, alpha=0.2)

    limits = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
    plt.plot(limits, limits, color=ACCENT, linewidth=1.5, label='идеальный прогноз')

    plt.title(title)
    plt.xlabel('Фактическая цена за м²')
    plt.ylabel('Прогноз модели')
    formatter = ticker.FuncFormatter(lambda x, p: f'{int(x):,}'.replace(',', ' '))
    plt.gca().xaxis.set_major_formatter(formatter)
    plt.gca().yaxis.set_major_formatter(formatter)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()
