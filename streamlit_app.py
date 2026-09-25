"""Дашборд «Рынок недвижимости Москвы 2020–2026». Запуск: streamlit run streamlit_app.py"""

import streamlit as st

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
