"""Гео-анализ: тепловые карты, кластеризация районов, метро"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker, colors

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

_THOUSANDS = ticker.FuncFormatter(lambda x, p: f'{int(x):,}'.replace(',', ' '))


def plot_heatmap(matrix, title, cbar_label, cmap='YlOrRd', center=None,
                 fmt='{:,.0f}', figsize=(11, 7), annotate=True):
    """
    Тепловая карта: таблица, где значение каждой ячейки закодировано цветом

    Параметры:
        matrix      : DataFrame — строки и столбцы станут осями карты
        cmap        : палитра. Последовательная (YlOrRd) — когда важна величина «от малого к большому».
                      Расходящаяся (RdBu_r) — когда важно отклонение в обе стороны от середины
        center      : если задан, палитра центрируется на этом значении (для расходящихся палитр)
        annotate    : подписывать ли числа в ячейках
    """
    data = matrix.values.astype(float)

    if center is not None:
        norm = colors.TwoSlopeNorm(
            vmin=np.nanmin(data), vcenter=center, vmax=np.nanmax(data)
        )
    else:
        norm = None

    fig, ax = plt.subplots(figsize=figsize)
    image = ax.imshow(data, cmap=cmap, norm=norm, aspect='auto')

    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=45, ha='right')
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(matrix.index)

    if annotate:
        # цвет текста подбираем по яркости фона, чтобы подпись читалась на любой ячейке
        rgba = image.cmap(image.norm(data))
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                value = data[i, j]
                if np.isnan(value):
                    continue
                brightness = 0.299 * rgba[i, j, 0] + 0.587 * rgba[i, j, 1] + 0.114 * rgba[i, j, 2]
                ax.text(j, i, fmt.format(value), ha='center', va='center', fontsize=8,
                        color='white' if brightness < 0.5 else 'black')

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label(cbar_label)

    ax.set_title(title)
    plt.tight_layout()
    plt.show()


def choose_clusters(features, k_range=range(2, 9), random_state=42):
    """
    Подбор числа кластеров: считает силуэт для каждого k
    Силуэт от -1 до 1, чем выше — тем плотнее кластеры и тем лучше разделены
    """
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    rows = []
    for k in k_range:
        model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = model.fit_predict(X)
        rows.append({
            'k': k,
            'Силуэт': round(silhouette_score(X, labels), 3),
            'Инерция': round(model.inertia_, 1),
        })
    return pd.DataFrame(rows)


def cluster_districts(features, n_clusters, random_state=42):
    """
    Кластеризация районов методом k-средних
    Признаки стандартизуются: без этого цена в сотнях тысяч
    полностью заглушила бы километры и минуты
    """
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = model.fit_predict(X)

    result = features.copy()
    result['cluster'] = labels

    summary = result.groupby('cluster').agg(['median', 'size'])
    summary = result.groupby('cluster').median()
    summary['Районов'] = result.groupby('cluster').size()

    return result, summary


def plot_clusters_map(district_data, lat_col, lon_col, cluster_col, title):
    """
    Районы на координатной плоскости, цвет — номер кластера
    Позволяет увидеть, совпадают ли кластеры по цене с географией
    """
    plt.figure(figsize=(9, 8))
    for cluster in sorted(district_data[cluster_col].unique()):
        subset = district_data[district_data[cluster_col] == cluster]
        plt.scatter(subset[lon_col], subset[lat_col], s=60, alpha=0.8, label=f'Кластер {cluster}')

    plt.title(title)
    plt.xlabel('Долгота')
    plt.ylabel('Широта')
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_price_by_metro_line(df, price_col, title, top=None):
    """Медианная цена за м² по веткам метро, отсортировано"""
    by_line = df.groupby('metro_line')[price_col].agg(['median', 'size'])
    by_line = by_line.sort_values('median')
    if top:
        by_line = by_line.tail(top)

    plt.figure(figsize=(10, 6))
    plt.barh(by_line.index, by_line['median'], color='steelblue')
    plt.title(title)
    plt.xlabel('Медианная цена за м²')
    plt.gca().xaxis.set_major_formatter(_THOUSANDS)
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.show()

    return by_line
