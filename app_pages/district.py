import streamlit as st

from dashboard.charts import district_vs_part
from dashboard.data import METRICS, OFFICIAL_SERIES_NOTE, SEGMENTS, fmt_num, recommendation_note
from dashboard.loaders import load_district_month, load_districts, load_meta

districts = load_districts()
monthly = load_district_month()
meta = load_meta()

st.title('Карточка района')

labels = sorted(districts['label'])
default = next((i for i, l in enumerate(labels) if l.startswith('Хамовники')), 0)
chosen = st.selectbox('Район', labels, index=default, key='district')
row = districts[districts['label'] == chosen].iloc[0]
part = row['moscow_part']
peers = districts[districts['moscow_part'] == part]

st.markdown(f'**{row["name"]}** · {row["okrug_ru"]} · {part} · '
            f'в среднем {fmt_num(row["to_center_km"], 1)} км до центра')


def delta_vs_part(column, digits=0, suffix=''):
    diff = row[column] - peers[column].median()
    if diff != diff:
        return None
    sign = '+' if diff >= 0 else '-'
    return f'{sign}{fmt_num(abs(diff), digits)}{suffix} к медиане части города'


with st.container(horizontal=True):
    st.metric('Цена вторички', f'{fmt_num(row["avg_price_sqm_all"])} ₽/м²',
              delta_vs_part('avg_price_sqm_all'), delta_color='off', border=True,
              help=METRICS['avg_price_sqm_all'][2])
    st.metric('Без премиум-сегмента', f'{fmt_num(row["avg_price_sqm_no_premium"])} ₽/м²',
              delta_vs_part('avg_price_sqm_no_premium'), delta_color='off', border=True,
              help=METRICS['avg_price_sqm_no_premium'][2])
    st.metric('Аренда', f'{fmt_num(row["avg_rent_sqm_all"])} ₽/м² в мес.',
              delta_vs_part('avg_rent_sqm_all'), delta_color='off', border=True,
              help=METRICS['avg_rent_sqm_all'][2])

with st.container(horizontal=True):
    st.metric('Окупаемость покупки', f'{fmt_num(row["payback_years"], 1)} лет',
              delta_vs_part('payback_years', 1, ' г.'), delta_color='inverse', border=True,
              help=METRICS['payback_years'][2])
    if row['n_new_builds'] > 0 and row['newbuild_premium_pct'] == row['newbuild_premium_pct']:
        st.metric('Наценка новостроек', f'{fmt_num(row["newbuild_premium_pct"], 1)}%',
                  delta_vs_part('newbuild_premium_pct', 1, ' п.п.'), delta_color='off', border=True,
                  help=METRICS['newbuild_premium_pct'][2])
        st.metric('Наценка в рублях', f'{fmt_num(row["newbuild_premium_rub"])} ₽/м²',
                  delta_vs_part('newbuild_premium_rub'), delta_color='off', border=True,
                  help=METRICS['newbuild_premium_rub'][2])
    else:
        st.metric('Наценка новостроек', '—', 'новостроек в районе нет', delta_color='off', border=True)

st.markdown(f'Оценка по окупаемости: **{row["recommendation"]}**', help=recommendation_note(part, meta))
st.caption(f'Объявлений в районе: вторичка {row["n_secondary"]}, аренда {row["n_rentals"]}, '
           f'новостройки {row["n_new_builds"]}.')

st.subheader('Цены во времени')
segment = st.segmented_control('Сегмент', list(SEGMENTS), default='secondary',
                               format_func=lambda s: SEGMENTS[s][0], key='segment') or 'secondary'
seg_label, column, unit = SEGMENTS[segment]

series = monthly[monthly['district'] == row['district']].set_index('month')[column]
part_median = monthly[monthly['moscow_part'] == part].groupby('month')[column].median()
st.plotly_chart(district_vs_part(series, part_median, row['name'], part, f'{seg_label}, {unit}'))
st.caption('Серая линия — медиана по всем районам той же части города. ' + OFFICIAL_SERIES_NOTE)

with st.expander('Таблица по годам'):
    yearly = (monthly[monthly['district'] == row['district']]
              .assign(Год=lambda d: d['month'].dt.year)
              .groupby('Год')[[s[1] for s in SEGMENTS.values()]].mean().round(0))
    yearly.columns = [f'{s[0]}, {s[2]}' for s in SEGMENTS.values()]
    st.dataframe(yearly, column_config={c: st.column_config.NumberColumn(format='localized')
                                        for c in yearly.columns})
