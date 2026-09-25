"""
Весь проект одной командой: от сырых CSV до витрины дашборда и графиков README

    python -m src.pipeline            все шаги по порядку
    python -m src.pipeline --list     список шагов
    python -m src.pipeline --from 7   продолжить с шага 7 (например, после исправления ошибки)

Ноутбуки выполняются целиком и сохраняются вместе с результатами — так же, как при
ручном «Run All». Если шаг падает, конвейер останавливается: следующие шаги зависят
от предыдущих, и продолжать на неполных данных нельзя.
"""

import argparse
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

from src.export_figures import export_figures
from src.mart import build_mart, write_mart

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = PROJECT_ROOT / 'notebooks'


def run_notebook(name):
    path = NOTEBOOKS / name
    nb = nbformat.read(path, as_version=4)
    NotebookClient(nb, timeout=1800, kernel_name='python3',
                   resources={'metadata': {'path': str(NOTEBOOKS)}}).execute()
    nbformat.write(nb, path)


def run_mart():
    write_mart(build_mart())


STEPS = [
    ('Очистка: аренда', lambda: run_notebook('data_clean_rentals.ipynb')),
    ('Очистка: вторичка', lambda: run_notebook('data_clean_secondary_market.ipynb')),
    ('Очистка: новостройки', lambda: run_notebook('data_clean_new_builds.ipynb')),
    ('Очистка: помесячная статистика районов', lambda: run_notebook('data_clean_district_prices_monthly.ipynb')),
    ('SQLite: таблицы и представления', lambda: run_notebook('sql_loading_tables.ipynb')),
    ('Витрина данных для дашборда', run_mart),
    ('Поверхностный анализ', lambda: run_notebook('surface_analysis.ipynb')),
    ('Глубокий анализ', lambda: run_notebook('deep_analysis.ipynb')),
    ('Графики для README', export_figures),
]


def main(argv=None):
    parser = argparse.ArgumentParser(description='Прогон всего проекта одной командой')
    parser.add_argument('--from', dest='start', type=int, default=1, help='номер шага, с которого начать')
    parser.add_argument('--list', action='store_true', help='показать шаги и выйти')
    args = parser.parse_args(argv)

    if args.list or not 1 <= args.start <= len(STEPS):
        for number, (title, _) in enumerate(STEPS, 1):
            print(f'{number}. {title}')
        return 0 if args.list else 2

    started = time.perf_counter()
    for number, (title, step) in enumerate(STEPS, 1):
        if number < args.start:
            continue
        print(f'[{number}/{len(STEPS)}] {title}...', flush=True)
        step_started = time.perf_counter()
        try:
            step()
        except CellExecutionError as error:
            print(f'\nШаг {number} упал на ячейке ноутбука:\n{error}', file=sys.stderr)
            print(f'После исправления: python -m src.pipeline --from {number}', file=sys.stderr)
            return 1
        except Exception as error:
            print(f'\nШаг {number} упал: {type(error).__name__}: {error}', file=sys.stderr)
            print(f'После исправления: python -m src.pipeline --from {number}', file=sys.stderr)
            return 1
        print(f'      готово за {time.perf_counter() - step_started:.0f} с', flush=True)

    print(f'\nВесь проект пересобран за {time.perf_counter() - started:.0f} с')
    return 0


if __name__ == '__main__':
    sys.exit(main())
