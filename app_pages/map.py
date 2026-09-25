import streamlit as st

from dashboard.charts import district_map, district_ranking
from dashboard.data import METRICS, PARTS, plural_ru
from dashboard.loaders import load_districts

districts = load_districts()

st.title('Карта районов')

with st.container(horizontal=True, vertical_alignment='bottom'):
    metric = st.selectbox('Показатель', list(METRICS), format_func=lambda m: METRICS[m][0], key='metric')
    part = st.segmented_control('Часть города', ['Вся Москва'] + PARTS, default='Вся Москва', key='part')
    okrugs = st.multiselect('Округа', sorted(districts['okrug_ru'].unique()), placeholder='все округа',
                            key='okrugs')

label, unit, explanation = METRICS[metric]
st.caption(explanation)

view = districts
if part and part != 'Вся Москва':
    view = view[view['moscow_part'] == part]
if okrugs:
    view = view[view['okrug_ru'].isin(okrugs)]

if view.empty:
    st.warning('Под выбранные фильтры не попал ни один район.')
    st.stop()

missing = view[metric].isna().sum()
if missing:
    st.caption(f'Серые точки — {missing} {plural_ru(missing, "район", "района", "районов")}, где показатель '
               'не считается: там нет ни одного объявления новостройки.')

st.plotly_chart(district_map(view, metric), config={'scrollZoom': True})

st.subheader('Рейтинг районов')
with st.container(horizontal=True, vertical_alignment='bottom'):
    direction = st.segmented_control('Показать', ['Самые высокие', 'Самые низкие'], default='Самые высокие',
                                     key='direction')
    available = int(view[metric].notna().sum())
    top_n = st.slider('Сколько районов', 1, available, min(15, available), key='top_n') if available > 1 else available

if available:
    st.plotly_chart(district_ranking(view, metric, top_n, highest=direction != 'Самые низкие'))

with st.expander('Таблица по всем выбранным районам'):
    table = view[['name', 'okrug_ru', 'moscow_part', metric]].sort_values(metric, ascending=False)
    st.dataframe(
        table, hide_index=True,
        column_config={
            'name': 'Район', 'okrug_ru': 'Округ', 'moscow_part': 'Часть города',
            metric: st.column_config.NumberColumn(f'{label}, {unit}', format='localized'),
        },
    )
