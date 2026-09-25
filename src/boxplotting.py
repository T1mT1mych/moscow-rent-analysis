"""Функция для постройки боксплота"""

from matplotlib import ticker
import matplotlib.pyplot as plt

from src.plot_style import THOUSANDS


def plot_price_boxplot(data, title, width, height, delenia, xlabel='Цена за м²'):
    """
    Горизонтальный boxplot для одной числовой колонки
    Параметры:
        data   : pandas Series с числовыми значениями)
        title  : заголовок графика
        xlabel : подпись оси X
    """

    plt.figure(figsize=(width, height))
    plt.boxplot(data, orientation='horizontal')
    plt.title(title)
    plt.xlabel(xlabel)

    # Формат числовых значений оси (разделитель тысяч — пробел)
    plt.gca().xaxis.set_major_formatter(
        THOUSANDS
    )

    # Количество делений на оси
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(nbins=delenia))

    # Сетка
    plt.grid(axis='x')
    plt.tight_layout()
    plt.show()