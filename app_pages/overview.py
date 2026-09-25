import streamlit as st

from dashboard.data import METRICS, NEW, OLD, PARTS, fmt_num, part_summary, plural_ru
from dashboard.loaders import load_districts, load_meta, load_segment_medians

districts = load_districts()
summary = part_summary(districts, load_segment_medians())
meta = load_meta()

st.title('Рынок недвижимости Москвы, 2020–2026')
st.caption('Аренда, вторичное жильё и новостройки: около 78 тысяч объявлений по 129 районам')

st.info(
    '**Данные полусинтетические.** Реальны координаты районов и метро, ключевая ставка ЦБ '
    'и базовые цены по округам, а сами объявления сгенерированы автором датасета моделью '
    'ценообразования. Поэтому все числа здесь — закономерности внутри датасета, '
    'а не точные факты о рынке Москвы.',
    icon=':material/info:',
)

st.subheader('Две части города — два разных рынка')
columns = st.columns(2, border=True)
for column, part in zip(columns, PARTS):
    s = summary[part]
    with column:
        n = s['districts']
        st.markdown(f'**{part}** · {n} {plural_ru(n, "район", "района", "районов")}')
        with st.container(horizontal=True):
            st.metric('Вторичка, медиана', f'{fmt_num(s["price_median"])} ₽/м²')
            st.metric('Новостройки, медиана', f'{fmt_num(s["newbuild_median"])} ₽/м²')
            st.metric('Аренда, медиана', f'{fmt_num(s["rent_median"])} ₽/м² в мес.')
        with st.container(horizontal=True):
            st.metric('Окупаемость покупки', f'{fmt_num(s["payback_median"], 1)} лет',
                      help=METRICS['payback_years'][2])
            st.metric('Наценка новостроек', f'{fmt_num(s["premium_pct_median"], 1)}%',
                      help=METRICS['newbuild_premium_pct'][2])
            st.metric('Наценка в рублях', f'{fmt_num(s["premium_rub_median"])} ₽/м²',
                      help=METRICS['newbuild_premium_rub'][2])
st.caption('Окупаемость и наценка — медианы по районам, без премиум-сегмента. '
           'Цены и аренда — медианы по всем объявлениям за весь период.')

old, new = summary[OLD], summary[NEW]
st.subheader('Главное')
st.markdown(f'''
- **Цену определяет место, а не само жильё.** Хрущёвка в центре стоит дороже сталинки
  в любом другом округе, а по цене районы складываются в три кольца вокруг центра — это видно на карте.
- **Новая Москва в {fmt_num(old["price_median"] / new["price_median"], 1)} раза дешевле старой на вторичке**
  и окупается быстрее: {fmt_num(new["payback_median"], 1)} лет против {fmt_num(old["payback_median"], 1)}.
  Почему именно так, данные до конца не объясняют — подробности на странице «Старая и Новая Москва».
- **Новостройки дороже вторички в среднем на треть.** В Новой Москве наценка выше в процентах,
  но ниже в рублях: база там меньше, и тот же рублёвый разрыв даёт больший процент.
- **Цены выросли примерно на 55% с 2020 года и с 2024-го стоят на месте.** Провалы совпадают
  с подъёмами ключевой ставки ЦБ — это видно на странице «Динамика цен».
- **Для сдачи в аренду центр — не лучший выбор:** в дорогих районах аренда растёт медленнее цены,
  поэтому окупаемость длиннее.
''')

st.subheader('Что где смотреть')
st.markdown('''
- **Карта районов** — любая метрика на карте Москвы и рейтинг районов по ней
- **Карточка района** — все показатели одного района и его цены во времени на фоне своей части города
- **Динамика цен** — как менялись цены и аренда с 2020 года и как это связано со ставкой ЦБ
- **Старая и Новая Москва** — подробное сравнение двух частей города
''')

with st.expander('Что означают показатели'):
    for label, unit, text in METRICS.values():
        st.markdown(f'**{label}** ({unit}) — {text}')

st.divider()
st.caption(
    'Источник: [Moscow Real Estate: Sales & Rentals (2020–2026)]'
    '(https://www.kaggle.com/datasets/sergionefedov/moscow-real-estate-sales-and-rentals-20202026), '
    f'Kaggle, лицензия Apache 2.0. Витрина данных собрана {".".join(reversed(meta.get("built_at", "—")[:10].split("-")))}. '
    'Код и полный анализ: [github.com/T1mT1mych/moscow-rent-analysis]'
    '(https://github.com/T1mT1mych/moscow-rent-analysis).'
)
