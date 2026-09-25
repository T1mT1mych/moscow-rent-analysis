"""Загрузка витрины с кешем Streamlit: CSV читаются один раз на всё время работы сервера"""

import pandas as pd
import streamlit as st

from dashboard.data import MART_DIR, meta_dict, prepare_district_month, prepare_districts


@st.cache_data
def load_districts():
    return prepare_districts(pd.read_csv(MART_DIR / 'mart_districts.csv'))


@st.cache_data
def load_district_month():
    return prepare_district_month(pd.read_csv(MART_DIR / 'mart_district_month.csv'), load_districts())


@st.cache_data
def load_segment_medians():
    return pd.read_csv(MART_DIR / 'mart_segment_medians.csv', dtype={'period': str})


@st.cache_data
def load_meta():
    return meta_dict(pd.read_csv(MART_DIR / 'mart_meta.csv'))
