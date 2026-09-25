import streamlit as st

from dashboard.charts import key_rate_chart, parts_over_time
from dashboard.data import (NEW, OFFICIAL_SERIES_NOTE, OLD, SEGMENTS, fmt_num, key_rate_series,
                            part_monthly_median, to_index)
from dashboard.loaders import load_district_month

monthly = load_district_month()

st.title('Динамика цен')

with st.container(horizontal=True, vertical_alignment='bottom'):
    segment = st.segmented_control('Сегмент', list(SEGMENTS), default='secondary',
                                   format_func=lambda s: SEGMENTS[s][0], key='segment') or 'secondary'
    scale = st.segmented_control('Шкала', ['Рубли', 'Рост, январь 2020 = 100'], default='Рубли',
                                 key='scale') or 'Рубли'

label, column, unit = SEGMENTS[segment]
table = part_monthly_median(monthly, column)
as_index = scale != 'Рубли'
shown = to_index(table) if as_index else table
ytitle = 'Индекс, январь 2020 = 100' if as_index else f'{label}, {unit}'

growth = to_index(table).iloc[-1] - 100
last = table.index[-1].strftime('%m.%Y')
with st.container(horizontal=True):
    for part in (OLD, NEW):
        st.metric(f'{part}: рост с 01.2020 по {last}', f'+{fmt_num(growth[part], 1)}%', border=True)

st.plotly_chart(parts_over_time(shown, ytitle, digits=1 if as_index else 0))
st.caption(f'{label}: медиана по районам каждой части города. Шкала «рост» выравнивает обе линии '
           'на старте и показывает, где цены росли быстрее. ' + OFFICIAL_SERIES_NOTE)

st.subheader('Ключевая ставка ЦБ')
st.plotly_chart(key_rate_chart(key_rate_series(monthly)))
st.caption('Отдельный график, а не вторая ось на графике цен: у ставки другая единица измерения, '
           'и совмещение двух шкал создаёт видимость связи там, где её надо проверять. В анализе проекта '
           'связь проверена: цены реагируют на изменение ставки примерно через месяц, провалы начала 2022 '
           'и конца 2024 совпадают с подъёмами ставки до 21%.')

with st.expander('Таблица: среднегодовые значения'):
    yearly = table.groupby(table.index.year).mean().round(1 if segment == 'rent' else 0)
    yearly.index.name = 'Год'
    rate = key_rate_series(monthly)
    yearly['Ключевая ставка, %'] = rate.groupby(rate.index.year).mean().round(2)
    st.dataframe(yearly, column_config={c: st.column_config.NumberColumn(format='localized')
                                        for c in yearly.columns})
