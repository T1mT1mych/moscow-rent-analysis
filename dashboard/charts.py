"""
Графики дашборда (Plotly)

Правила оформления общие для всех графиков:
- старая и Новая Москва всегда одного и того же цвета (PART_COLORS), на любой странице
- величина на карте — одна синяя шкала от светлого к тёмному
- одна ось Y на график: разные единицы измерения — разные графики, а не вторая ось
- у каждой точки подсказка при наведении; таблица с теми же числами — на странице рядом
"""

import plotly.graph_objects as go

from dashboard.data import METRICS, NEUTRAL, PART_COLORS, PARTS, SEQUENTIAL, fmt_num

MOSCOW_CENTER = {'lat': 55.60, 'lon': 37.40}


def _layout(fig, ytitle=None, height=420, legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        separators=', ',
        hoverlabel=dict(bgcolor='white', font_size=13),
        showlegend=legend,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0, title=None),
    )
    if ytitle is not None:
        fig.update_yaxes(title=ytitle)
    fig.update_yaxes(tickformat=',~f')
    fig.update_xaxes(title=None)
    return fig


def _metric_title(metric):
    label, unit, _ = METRICS[metric]
    return f'{label}, {unit}'


def _digits(metric):
    return 1 if metric in ('payback_years', 'newbuild_premium_pct', 'to_center_km') else 0


def district_map(districts, metric):
    """Районы точками на карте, цвет — значение метрики; районы без значения серые"""
    digits = _digits(metric)
    has_value = districts[metric].notna()
    fig = go.Figure()

    for subset, is_empty in [(districts[~has_value], True), (districts[has_value], False)]:
        if subset.empty:
            continue
        values = subset[metric].map(lambda v: fmt_num(v, digits))
        customdata = list(zip(subset['okrug_ru'], subset['moscow_part'], values))
        marker = dict(size=13, opacity=0.9)
        if is_empty:
            marker['color'] = NEUTRAL
        else:
            marker.update(color=subset[metric], colorscale=SEQUENTIAL,
                          colorbar=dict(title=_metric_title(metric), thickness=12, tickformat=',~f'))
        fig.add_trace(go.Scattermap(
            lat=subset['lat'], lon=subset['lon'], mode='markers', marker=marker,
            text=subset['name'], customdata=customdata,
            name='нет данных' if is_empty else METRICS[metric][0],
            hovertemplate='<b>%{text}</b> · %{customdata[0]}<br>%{customdata[1]}<br>'
                          + METRICS[metric][0] + ': %{customdata[2]} ' + METRICS[metric][1]
                          + '<extra></extra>',
        ))

    fig.update_layout(map=dict(style='open-street-map', center=MOSCOW_CENTER, zoom=7.9))
    return _layout(fig, height=560, legend=not has_value.all())


def district_ranking(districts, metric, top_n, highest=True):
    """Горизонтальные столбики: N районов с самыми высокими или низкими значениями"""
    data = districts.dropna(subset=[metric])
    data = data.nlargest(top_n, metric) if highest else data.nsmallest(top_n, metric)
    data = data.sort_values(metric, ascending=highest)
    digits = _digits(metric)

    fig = go.Figure()
    for part in PARTS:
        side = data[data['moscow_part'] == part]
        if side.empty:
            continue
        fig.add_trace(go.Bar(
            x=side[metric], y=side['label'], orientation='h', name=part,
            marker=dict(color=PART_COLORS[part], cornerradius=4),
            text=side[metric].map(lambda v: fmt_num(v, digits)), textposition='outside',
            cliponaxis=False,
            hovertemplate='<b>%{y}</b><br>' + METRICS[metric][0] + ': %{text} '
                          + METRICS[metric][1] + '<extra></extra>',
        ))
    fig.update_yaxes(categoryorder='array', categoryarray=list(data['label']))
    fig.update_xaxes(title=_metric_title(metric), tickformat=',~f')
    fig.update_layout(bargap=0.25)
    return _layout(fig, height=max(300, 26 * len(data) + 90))


def parts_over_time(table, ytitle, digits=0):
    """Линии старой и Новой Москвы по месяцам"""
    fig = go.Figure()
    for part in PARTS:
        if part not in table:
            continue
        fig.add_trace(go.Scatter(
            x=table.index, y=table[part], mode='lines', name=part,
            line=dict(color=PART_COLORS[part], width=2),
            hovertemplate=f'{part}: %{{y:,.{digits}f}}<extra></extra>',
        ))
    fig.update_layout(hovermode='x unified')
    fig.update_xaxes(hoverformat='%B %Y')
    return _layout(fig, ytitle=ytitle)


def key_rate_chart(series):
    """Ключевая ставка ЦБ отдельным графиком — у неё другая единица, чем у цен"""
    fig = go.Figure(go.Scatter(
        x=series.index, y=series.values, mode='lines', line=dict(color=NEUTRAL, width=2, shape='hv'),
        name='Ключевая ставка ЦБ', hovertemplate='%{y:.2f}%<extra></extra>',
    ))
    fig.update_layout(hovermode='x unified')
    fig.update_xaxes(hoverformat='%B %Y')
    return _layout(fig, ytitle='Ключевая ставка, %', height=240, legend=False)


def district_vs_part(district_series, part_series, district, part, ytitle):
    """Район на фоне медианы своей части города"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=part_series.index, y=part_series.values, mode='lines', name=f'Медиана: {part}',
        line=dict(color=NEUTRAL, width=2), hovertemplate='медиана части города: %{y:,.0f}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=district_series.index, y=district_series.values, mode='lines', name=district,
        line=dict(color=PART_COLORS[part], width=2.5), hovertemplate=district + ': %{y:,.0f}<extra></extra>',
    ))
    fig.update_layout(hovermode='x unified')
    fig.update_xaxes(hoverformat='%B %Y')
    return _layout(fig, ytitle=ytitle, height=340)


def segment_by_year(medians, segment, column, ytitle):
    """Медиана цены сегмента по годам: старая и Новая Москва"""
    data = medians[(medians['segment'] == segment) & (medians['period'] != 'ALL')]
    fig = go.Figure()
    for part in PARTS:
        side = data[data['moscow_part'] == part].sort_values('period')
        fig.add_trace(go.Scatter(
            x=side['period'], y=side[column], mode='lines+markers', name=part,
            line=dict(color=PART_COLORS[part], width=2), marker=dict(size=8),
            customdata=side['n_listings'],
            hovertemplate=part + ': %{y:,.0f}<br>объявлений: %{customdata:,}<extra></extra>',
        ))
    fig.update_layout(hovermode='x unified')
    fig.update_xaxes(type='category')
    return _layout(fig, ytitle=ytitle, height=320)


def distribution_by_part(districts, metric):
    """Каждый район — точка; видно и уровень, и разброс внутри каждой части города"""
    digits = _digits(metric)
    fig = go.Figure()
    for part in PARTS:
        side = districts[(districts['moscow_part'] == part) & districts[metric].notna()]
        fig.add_trace(go.Box(
            y=side[metric], name=part, boxpoints='all', jitter=0.45, pointpos=0,
            marker=dict(color=PART_COLORS[part], size=8, opacity=0.75),
            line=dict(color=PART_COLORS[part], width=1.5), fillcolor='rgba(0,0,0,0)',
            text=side['name'], customdata=side[metric].map(lambda v: fmt_num(v, digits)),
            hovertemplate='<b>%{text}</b><br>%{customdata} ' + METRICS[metric][1] + '<extra></extra>',
        ))
    return _layout(fig, ytitle=_metric_title(metric), height=380, legend=False)
