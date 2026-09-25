"""
Выгрузка ключевых графиков из выполненных ноутбуков в output/figures/

Графики не перерисовываются заново: берутся ровно те картинки, что сохранены
в выводах ячеек ноутбука, поэтому README показывает то же самое, что читатель
увидит в анализе. Ячейка находится по фрагменту её кода — если фрагмент
перестанет встречаться ровно один раз, скрипт остановится с ошибкой, а не
выгрузит не тот график.

Запуск (после выполнения ноутбуков): python -m src.export_figures
"""

import base64
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = PROJECT_ROOT / 'notebooks'
FIGURES_DIR = PROJECT_ROOT / 'output' / 'figures'

# имя файла -> (ноутбук, фрагмент кода ячейки, номер картинки в выводе ячейки)
FIGURES = {
    'district_clusters.png': ('deep_analysis.ipynb', 'plot_clusters_map(', 0),
    'price_by_okrug_and_building_type.png': (
        'deep_analysis.ipynb', "title='Медианная цена за м² по округам и типам домов", 0),
    'price_and_key_rate.png': ('deep_analysis.ipynb', "plot_price_and_rate(city, 'secondary'", 0),
    'yield_vs_growth.png': ('deep_analysis.ipynb', 'plot_yield_growth_quadrants(', 0),
    'premium_threshold_stability.png': ('deep_analysis.ipynb', 'plot_threshold_stability(', 0),
    'payback_vs_price.png': (
        'deep_analysis.ipynb', "districts, 'avg_price_sqm_no_premium', 'payback_years'", 0),
}


def find_image(notebook, fragment, index):
    nb = json.loads((NOTEBOOKS / notebook).read_text(encoding='utf-8'))
    cells = [c for c in nb['cells'] if c['cell_type'] == 'code' and fragment in ''.join(c['source'])]
    if len(cells) != 1:
        raise ValueError(f'{notebook}: фрагмент {fragment!r} найден в {len(cells)} ячейках, нужна ровно одна')
    images = [o['data']['image/png'] for o in cells[0].get('outputs', []) if 'image/png' in o.get('data', {})]
    if len(images) <= index:
        raise ValueError(f'{notebook}: в ячейке с {fragment!r} нет картинки №{index} — ноутбук выполнен?')
    return base64.b64decode(''.join(images[index]))


def export_figures():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for name, (notebook, fragment, index) in FIGURES.items():
        (FIGURES_DIR / name).write_bytes(find_image(notebook, fragment, index))
        print(f'{name:40} <- {notebook}')


if __name__ == '__main__':
    export_figures()
