"""
Dashboard Interativo — Análise de Faturamento Olist
Autor: Augusto Matos

Como rodar:
    pip install -r requirements.txt
    python dashboard/app.py

Acesse: http://localhost:8050
"""

import sqlite3
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# ── Configuração ──────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'olist.db')
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'Olist — Análise de Faturamento'


# ── Funções de dados ──────────────────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH)


def load_receita_mensal(estado=None):
    filtro_estado = "AND cu.customer_state = ?" if estado else ""
    params = (estado,) if estado else ()
    query = f"""
        SELECT
            STRFTIME('%Y-%m', o.order_purchase_timestamp) AS mes,
            COUNT(DISTINCT o.order_id)                     AS pedidos,
            ROUND(SUM(oi.price + oi.freight_value), 2)     AS receita
        FROM orders o
        JOIN order_items oi ON o.order_id      = oi.order_id
        JOIN customers   cu ON o.customer_id   = cu.customer_id
        WHERE o.order_status = 'delivered'
          AND o.order_purchase_timestamp IS NOT NULL
          {filtro_estado}
        GROUP BY mes
        ORDER BY mes
    """
    conn = get_conn()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    df['mes'] = pd.to_datetime(df['mes'])
    return df[(df['mes'] >= '2017-01-01') & (df['mes'] <= '2018-08-01')]


def load_kpis(estado=None):
    filtro_estado = "AND cu.customer_state = ?" if estado else ""
    params = (estado,) if estado else ()
    query = f"""
        SELECT
            COUNT(DISTINCT o.order_id)                         AS pedidos,
            ROUND(SUM(oi.price + oi.freight_value), 2)         AS receita,
            ROUND(AVG(oi.price + oi.freight_value), 2)         AS ticket_medio,
            ROUND(AVG(r.review_score), 2)                      AS nota_media
        FROM orders o
        JOIN order_items oi ON o.order_id    = oi.order_id
        JOIN customers   cu ON o.customer_id = cu.customer_id
        LEFT JOIN reviews r ON o.order_id    = r.order_id
        WHERE o.order_status = 'delivered'
          {filtro_estado}
    """
    conn = get_conn()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df.iloc[0]


def load_categorias(estado=None):
    filtro_estado = "AND cu.customer_state = ?" if estado else ""
    params = (estado,) if estado else ()
    query = f"""
        SELECT
            COALESCE(c.product_category_name_english,
                     p.product_category_name, 'Outro')  AS categoria,
            ROUND(SUM(oi.price), 2)                     AS receita,
            ROUND(AVG(r.review_score), 2)               AS nota_media
        FROM orders o
        JOIN order_items  oi ON o.order_id    = oi.order_id
        JOIN products      p ON oi.product_id = p.product_id
        LEFT JOIN categories c ON p.product_category_name = c.product_category_name
        LEFT JOIN reviews    r ON o.order_id  = r.order_id
        JOIN customers       cu ON o.customer_id = cu.customer_id
        WHERE o.order_status = 'delivered'
          {filtro_estado}
        GROUP BY categoria
        ORDER BY receita DESC
        LIMIT 12
    """
    conn = get_conn()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


def load_estados():
    query = """
        SELECT DISTINCT customer_state AS estado
        FROM customers ORDER BY estado
    """
    conn = get_conn()
    df = pd.read_sql(query, conn)
    conn.close()
    return df['estado'].tolist()


def load_avaliacoes():
    query = """
        SELECT review_score AS nota, COUNT(*) AS quantidade
        FROM reviews GROUP BY review_score ORDER BY review_score
    """
    conn = get_conn()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# ── Layout ────────────────────────────────────────────────────────────────────
CARD_STYLE = {
    'borderRadius': '10px',
    'padding': '16px 20px',
    'background': '#fff',
    'border': '1.5px solid #e5e7eb',
    'textAlign': 'center'
}

def kpi_card(titulo, valor, cor='#4f46e5'):
    return html.Div([
        html.P(titulo, style={'fontSize': '12px', 'color': '#6b7280', 'margin': '0'}),
        html.H4(valor, style={'color': cor, 'margin': '4px 0 0', 'fontSize': '22px', 'fontWeight': '700'})
    ], style=CARD_STYLE)


app.layout = dbc.Container([

    # Cabeçalho
    dbc.Row([
        dbc.Col(html.H3('🛒 Olist — Análise de Faturamento',
                        style={'color': '#1a1a2e', 'fontWeight': '700', 'margin': '0'})),
        dbc.Col(html.P('Dataset: Brazilian E-Commerce | 2017–2018',
                       style={'color': '#6b7280', 'textAlign': 'right', 'margin': '8px 0 0'}))
    ], align='center', className='mb-3 mt-3'),

    # Filtro de Estado
    dbc.Row([
        dbc.Col([
            html.Label('Filtrar por Estado:', style={'fontWeight': '600', 'fontSize': '13px'}),
            dcc.Dropdown(
                id='filtro-estado',
                options=[{'label': 'Todos os estados', 'value': 'TODOS'}] +
                        [{'label': e, 'value': e} for e in load_estados()],
                value='TODOS',
                clearable=False,
                style={'fontSize': '13px'}
            )
        ], md=3)
    ], className='mb-3'),

    # KPI Cards
    dbc.Row(id='kpi-cards', className='mb-3 g-2'),

    # Receita Mensal + Avaliações
    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico-receita'), md=8),
        dbc.Col(dcc.Graph(id='grafico-avaliacoes'), md=4),
    ], className='mb-3'),

    # Top Categorias
    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico-categorias'), md=12),
    ], className='mb-3'),

], fluid=True, style={'backgroundColor': '#f9fafb', 'minHeight': '100vh', 'padding': '0 24px'})


# ── Callbacks ─────────────────────────────────────────────────────────────────
@app.callback(
    Output('kpi-cards', 'children'),
    Output('grafico-receita', 'figure'),
    Output('grafico-categorias', 'figure'),
    Output('grafico-avaliacoes', 'figure'),
    Input('filtro-estado', 'value')
)
def atualizar_dashboard(estado):
    estado_filtro = None if estado == 'TODOS' else estado

    # KPIs
    kpis = load_kpis(estado_filtro)
    cards = [
        dbc.Col(kpi_card('Total de Pedidos', f"{int(kpis['pedidos']):,}"), md=3),
        dbc.Col(kpi_card('Receita Total', f"R$ {kpis['receita']:,.0f}"), md=3),
        dbc.Col(kpi_card('Ticket Médio', f"R$ {kpis['ticket_medio']:,.2f}", '#06b6d4'), md=3),
        dbc.Col(kpi_card('Nota Média', f"⭐ {kpis['nota_media']:.2f}", '#22c55e'), md=3),
    ]

    # Receita Mensal
    receita = load_receita_mensal(estado_filtro)
    fig_receita = go.Figure()
    fig_receita.add_trace(go.Scatter(
        x=receita['mes'], y=receita['receita'],
        mode='lines+markers', name='Receita',
        line=dict(color='#4f46e5', width=2),
        fill='tozeroy', fillcolor='rgba(79,70,229,0.08)'
    ))
    fig_receita.update_layout(
        title='Receita Mensal (R$)', height=320,
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(tickprefix='R$ ')
    )

    # Categorias
    cats = load_categorias(estado_filtro)
    fig_cats = px.bar(
        cats.sort_values('receita'),
        x='receita', y='categoria', orientation='h',
        color='nota_media', color_continuous_scale='RdYlGn',
        range_color=[1, 5], text='receita',
        labels={'receita': 'Receita (R$)', 'categoria': 'Categoria', 'nota_media': 'Nota'},
        title='Top Categorias por Faturamento (cor = satisfação)'
    )
    fig_cats.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
    fig_cats.update_layout(
        height=420, plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=20, r=80, t=40, b=20)
    )

    # Avaliações
    avals = load_avaliacoes()
    cores = ['#ef4444', '#f97316', '#eab308', '#84cc16', '#22c55e']
    fig_avals = go.Figure(go.Bar(
        x=avals['nota'].astype(str) + ' ⭐',
        y=avals['quantidade'],
        marker_color=cores
    ))
    fig_avals.update_layout(
        title='Avaliações', height=320,
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return cards, fig_receita, fig_cats, fig_avals


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
