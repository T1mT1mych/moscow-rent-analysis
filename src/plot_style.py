"""
Единый стиль графиков проекта (matplotlib)

Импорт модуля применяет стиль ко всем последующим графикам. Его импортируют все
модули src/ с функциями рисования, поэтому ноутбукам отдельно ничего вызывать не нужно.

Палитра — проверенный набор: категориальные цвета различимы при всех видах
дальтонизма и контрастны на светлом фоне (проверено валидатором палитры).
Те же цвета использует дашборд: старая Москва всегда синяя, Новая — оранжевая.

Правила, которые держит этот модуль и функции рисования:
- одна ось Y на график: разные единицы — разные панели, а не вторая ось
- величина — одна шкала одного цвета от светлого к тёмному, отклонение от нуля —
  два противоположных цвета с серой серединой; радужные палитры не используются
- сетка и оси — тонкие и светлые, сплошные, верхней и правой рамки нет
"""

from cycler import cycler
import matplotlib as mpl
from matplotlib import ticker
from matplotlib.colors import LinearSegmentedColormap

SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
PRIMARY = SERIES[0]
ACCENT = SERIES[7]  # опорные линии: тренд, порог, прогноз, «было» против «стало»

OLD_MOSCOW, NEW_MOSCOW = '#2a78d6', '#eb6834'
PART_COLORS = {'Старая Москва': OLD_MOSCOW, 'Новая Москва': NEW_MOSCOW}

INK = '#0b0b0b'
INK_SECONDARY = '#52514e'
MUTED = '#898781'
GRID = '#e1e0d9'
BASELINE = '#c3c2b7'

SEQUENTIAL = LinearSegmentedColormap.from_list(
    'project_sequential',
    ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#2a78d6', '#1c5cab', '#104281', '#0d366b'],
)
DIVERGING = LinearSegmentedColormap.from_list(
    'project_diverging', ['#104281', '#3987e5', '#9ec5f4', '#f0efec', '#f3a4a3', '#e34948', '#a52524'],
)

THOUSANDS = ticker.FuncFormatter(lambda x, p: f'{x:,.0f}'.replace(',', ' '))


def apply_style():
    mpl.rcParams.update({
        'axes.prop_cycle': cycler(color=SERIES),
        'axes.edgecolor': BASELINE,
        'axes.labelcolor': INK_SECONDARY,
        'axes.titlecolor': INK,
        'axes.titlesize': 13,
        'axes.titleweight': 'bold',
        'axes.titlelocation': 'left',
        'axes.titlepad': 12,
        'axes.labelsize': 10.5,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': False,
        'axes.axisbelow': True,
        'grid.color': GRID,
        'grid.linestyle': '-',
        'grid.linewidth': 0.8,
        'grid.alpha': 1.0,
        'xtick.color': MUTED,
        'ytick.color': MUTED,
        'xtick.labelcolor': INK_SECONDARY,
        'ytick.labelcolor': INK_SECONDARY,
        'legend.frameon': False,
        'legend.fontsize': 9.5,
        'lines.linewidth': 2,
        'lines.markersize': 7,
        'patch.linewidth': 0,
        'image.cmap': 'project_sequential',
        'figure.facecolor': 'white',
        'figure.dpi': 100,
        'savefig.dpi': 150,
        'savefig.bbox': 'tight',
        'font.family': 'sans-serif',
        'font.sans-serif': ['Segoe UI', 'DejaVu Sans', 'Arial', 'sans-serif'],
        'font.size': 10.5,
    })


for _cmap in (SEQUENTIAL, DIVERGING):
    if _cmap.name not in mpl.colormaps:
        mpl.colormaps.register(_cmap)

apply_style()
