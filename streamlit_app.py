"""Дашборд «Рынок недвижимости Москвы 2020–2026». Запуск: streamlit run streamlit_app.py"""

import importlib
import sys
from pathlib import Path

import streamlit as st

# порядок важен: модуль перезагружается после тех, из которых он импортирует имена
LOCAL_MODULES = ['src.names', 'dashboard.data', 'dashboard.charts', 'dashboard.loaders']
MART_DIR = Path(__file__).resolve().parent / 'data' / 'mart'


def refresh_local_modules():
    """
    Перезагружает вспомогательные модули, если их файлы изменились на диске

    Streamlit Cloud после push подтягивает новые файлы и перезапускает страницы,
    но уже импортированные модули остаются в памяти в старой версии — новая страница
    просит у старого модуля имя, которого в нём нет, и падает с ImportError.
    Этот файл выполняется заново при каждом открытии страницы, поэтому проверка здесь
    обновляет модули без ручного перезапуска приложения. Если поменялись модули
    или CSV витрины, кеш данных сбрасывается.
    """
    changed = False
    for name in LOCAL_MODULES:
        module = sys.modules.get(name)
        if module is None:
            continue
        mtime = Path(module.__file__).stat().st_mtime
        if getattr(module, '_source_mtime', None) != mtime:
            module = importlib.reload(module)
            module._source_mtime = mtime
            changed = True

    mart_mtime = max((p.stat().st_mtime for p in MART_DIR.glob('*.csv')), default=None)
    if changed or getattr(st, '_mart_mtime', None) != mart_mtime:
        st.cache_data.clear()
        st._mart_mtime = mart_mtime


refresh_local_modules()

st.set_page_config(page_title='Недвижимость Москвы 2020–2026', page_icon=':material/apartment:', layout='wide')

page = st.navigation(
    [
        st.Page('app_pages/overview.py', title='Обзор', icon=':material/home:', default=True),
        st.Page('app_pages/map.py', title='Карта районов', icon=':material/map:'),
        st.Page('app_pages/district.py', title='Карточка района', icon=':material/location_on:'),
        st.Page('app_pages/dynamics.py', title='Динамика цен', icon=':material/show_chart:'),
        st.Page('app_pages/old_vs_new.py', title='Старая и Новая Москва', icon=':material/compare_arrows:'),
    ],
    position='top',
)
page.run()
