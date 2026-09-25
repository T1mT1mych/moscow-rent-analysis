import streamlit as st

from dashboard.charts import distribution_by_part, segment_by_year
from dashboard.data import NEW, OLD, PARTS, fmt_num
from dashboard.loaders import load_districts, load_segment_medians

districts = load_districts()
medians = load_segment_medians()

st.title('Старая и Новая Москва')
st.markdown('Новая Москва — это округа ТАО, НАО и Зеленоград. По ценам это отдельный рынок, '
            'а не дешёвый край общего: разброс цен двух частей города почти не пересекается.')

st.subheader('Цены по годам')
no_premium = st.toggle('Без премиум-сегмента', value=False, key='no_premium',
                       help='Премиум-сегмент — самые дорогие объекты своего года. В Новой Москве их нет, '
                            'в старой они сосредоточены в центре.')
column = 'median_price_sqm_no_premium' if no_premium else 'median_price_sqm_all'
all_period = medians[medians['period'] == 'ALL'].set_index(['segment', 'moscow_part'])[column]

for segment, unit in [('Вторичка', '₽/м²'), ('Новостройки', '₽/м²'), ('Аренда', '₽/м² в месяц')]:
    ratio = all_period[(segment, OLD)] / all_period[(segment, NEW)]
    with st.container(border=True):
        st.markdown(f'**{segment}** — в старой Москве в {fmt_num(ratio, 1)} раза дороже '
                    f'({fmt_num(all_period[(segment, OLD)])} против {fmt_num(all_period[(segment, NEW)])} {unit}, '
                    'медианы за весь период)')
        st.plotly_chart(segment_by_year(medians, segment, column, f'Медиана, {unit}'), key=f'seg_{segment}')

st.subheader('Окупаемость покупки')
payback = districts.groupby('moscow_part')['payback_years'].median()
left, right = st.columns([3, 2])
with left:
    st.plotly_chart(distribution_by_part(districts, 'payback_years'))
with right:
    st.markdown(f'''
Районы Новой Москвы окупаются быстрее: медиана **{fmt_num(payback[NEW], 1)} лет** против
**{fmt_num(payback[OLD], 1)}**. Разница держится в каждом году с 2021 по 2026 и внутри каждого
типа дома, числа комнат и вида ремонта, так что дело не в составе жилья.

Почему — вопрос открытый. Средний уровень совпадает с тем, что даёт низкая цена: в дешёвых районах
аренда относительно цены выше. Но внутри самой Новой Москвы окупаемость от цены почти не зависит:
ТАО почти вдвое дешевле НАО, а окупаются они одинаково.

С 2024 года разрыв сокращается: вторичка в Новой Москве дорожала быстрее аренды.
''')

st.subheader('Наценка новостроек над вторичкой')
premium = districts.groupby('moscow_part')[['newbuild_premium_pct', 'newbuild_premium_rub']].median()
left, right = st.columns(2)
with left:
    st.markdown('**В процентах**')
    st.plotly_chart(distribution_by_part(districts, 'newbuild_premium_pct'), key='premium_pct')
with right:
    st.markdown('**В рублях за м²**')
    st.plotly_chart(distribution_by_part(districts, 'newbuild_premium_rub'), key='premium_rub')
st.markdown(f'''
В процентах новостройки Новой Москвы «дороже» относительно вторички: медиана
**{fmt_num(premium.loc[NEW, "newbuild_premium_pct"], 1)}%** против
**{fmt_num(premium.loc[OLD, "newbuild_premium_pct"], 1)}%**. Но в рублях наоборот:
**{fmt_num(premium.loc[NEW, "newbuild_premium_rub"])}** против
**{fmt_num(premium.loc[OLD, "newbuild_premium_rub"])} ₽/м²**. Процент выше только потому, что база —
цена вторички — в Новой Москве вдвое с лишним ниже. Поэтому наценку честнее смотреть в обеих единицах.
''')

with st.expander('Таблица по районам'):
    table = districts[['district', 'okrug_ru', 'moscow_part', 'payback_years',
                       'newbuild_premium_pct', 'newbuild_premium_rub']]
    st.dataframe(
        table.sort_values(['moscow_part', 'payback_years']), hide_index=True,
        column_config={
            'district': 'Район', 'okrug_ru': 'Округ', 'moscow_part': 'Часть города',
            'payback_years': st.column_config.NumberColumn('Окупаемость, лет', format='%.1f'),
            'newbuild_premium_pct': st.column_config.NumberColumn('Наценка, %', format='%.1f'),
            'newbuild_premium_rub': st.column_config.NumberColumn('Наценка, ₽/м²', format='localized'),
        },
    )
