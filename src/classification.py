"""Классификация: какие признаки объясняют попадание объекта в премиум-сегмент"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from sklearn.inspection import permutation_importance

import matplotlib.pyplot as plt

from src.regression import build_features


def fit_premium_classifier(df, numeric_cols, categorical_cols,
                           target_col='is_premium', test_size=0.2,
                           random_state=42, n_estimators=200):
    """
    Обучает случайный лес, предсказывающий попадание объекта в премиум-сегмент
    Важно: в признаки не должны попадать цена и всё, что из неё посчитано,
    иначе получится утечка целевой переменной
    class_weight='balanced' компенсирует перекос классов — премиума мало
    stratify сохраняет долю премиума одинаковой в обучении и тесте
    """
    X = build_features(df, numeric_cols, categorical_cols)
    y = df[target_col].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        class_weight='balanced',
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print(f"Объектов: {len(X):,} (обучение {len(X_train):,} / тест {len(X_test):,}), признаков: {X.shape[1]}")
    print(f"Доля премиума в выборке: {y.mean() * 100:.1f}%")
    print(f"\nROC-AUC = {roc_auc_score(y_test, y_proba):.3f}")
    print("\nОтчёт по классам:")
    print(classification_report(y_test, y_pred, target_names=['обычный', 'премиум'], digits=3))
    print("Матрица ошибок (строки — факт, столбцы — прогноз):")
    print(pd.DataFrame(
        confusion_matrix(y_test, y_pred),
        index=['факт: обычный', 'факт: премиум'],
        columns=['прогноз: обычный', 'прогноз: премиум'],
    ).to_string())

    return model, (X_train, X_test, y_train, y_test)


def feature_importance_table(model, X, top=15):
    """
    Встроенная важность признаков случайного леса
    Считается по тому, насколько признак улучшал разбиения при обучении
    """
    table = pd.DataFrame({
        'Признак': X.columns,
        'Важность': np.round(model.feature_importances_, 4),
    }).sort_values('Важность', ascending=False).reset_index(drop=True)
    return table.head(top)


def permutation_importance_table(model, X_test, y_test, top=15,
                                 n_repeats=5, random_state=42):
    """
    Важность через перемешивание: насколько падает качество модели,
    если значения признака случайно перемешать
    Считается на тестовых данных, поэтому честнее встроенной важности
    """
    # n_jobs=1 намеренно: параллельный режим на Windows роняет joblib
    # на очистке временных файлов, а выигрыш по времени здесь незначителен
    result = permutation_importance(
        model, X_test, y_test,
        scoring='roc_auc', n_repeats=n_repeats,
        random_state=random_state, n_jobs=1,
    )
    table = pd.DataFrame({
        'Признак': X_test.columns,
        'Падение ROC-AUC': np.round(result.importances_mean, 4),
    }).sort_values('Падение ROC-AUC', ascending=False).reset_index(drop=True)
    return table.head(top)


def plot_importance(table, value_col, title):
    """Горизонтальная диаграмма важности признаков"""
    data = table.iloc[::-1]  # переворачиваем, чтобы самый важный оказался сверху
    plt.figure(figsize=(10, 6))
    plt.barh(data['Признак'], data[value_col])
    plt.title(title)
    plt.xlabel(value_col)
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.show()
