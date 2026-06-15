"""
Script para gerar screenshots estáticos do dashboard para o README.
Uso: python generate_screenshots.py
"""

import os
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'olist.db')
OUT_DIR = os.path.join(os.path.dirname(__file__), 'images')
os.makedirs(OUT_DIR, exist_ok=True)


def conn():
    return sqlite3.connect(DB_PATH)


def load_receita_mensal():
    q = """
        SELECT STRFTIME('%Y-%m', o.order_purchase_timestamp) AS mes,
               COUNT(DISTINCT o.order_id)                    AS pedidos,
               ROUND(SUM(oi.price + oi.freight_value), 2)    AS receita
        FROM orders o
        JOIN order_items oi ON o.order_id    = oi.order_id
        JOIN customers   cu ON o.customer_id = cu.customer_id
        WHERE o.order_status = 'delivered'
          AND o.order_purchase_timestamp IS NOT NULL
        GROUP BY mes ORDER BY mes
    """
    c = conn()
    df = pd.read_sql(q, c)
    c.close()
    df['mes'] = pd.to_datetime(df['mes'])
    return df[(df['mes'] >= '2017-01-01') & (df['mes'] <= '2018-08-01')]


def load_kpis():
    q = """
        SELECT COUNT(DISTINCT o.order_id)                AS pedidos,
               ROUND(SUM(oi.price + oi.freight_value),2) AS receita,
               ROUND(AVG(oi.price + oi.freight_value),2) AS ticket_medio,
               ROUND(AVG(r.review_score),2)              AS nota_media
        FROM orders o
        JOIN order_items oi ON o.order_id    = oi.order_id
        JOIN customers   cu ON o.customer_id = cu.customer_id
        LEFT JOIN reviews r ON o.order_id    = r.order_id
        WHERE o.order_status = 'delivered'
    """
    c = conn()
    df = pd.read_sql(q, c)
    c.close()
    return df.iloc[0]


def load_categorias():
    q = """
        SELECT COALESCE(c.product_category_name_english,
                        p.product_category_name, 'Outro') AS categoria,
               ROUND(SUM(oi.price), 2)                    AS receita,
               ROUND(AVG(r.review_score), 2)              AS nota_media
        FROM orders o
        JOIN order_items oi ON o.order_id    = oi.order_id
        JOIN products     p ON oi.product_id = p.product_id
        LEFT JOIN categories c ON p.product_category_name = c.product_category_name
        LEFT JOIN reviews    r ON o.order_id  = r.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY categoria ORDER BY receita DESC LIMIT 12
    """
    c = conn()
    df = pd.read_sql(q, c)
    c.close()
    return df


def load_avaliacoes():
    q = "SELECT review_score AS nota, COUNT(*) AS quantidade FROM reviews GROUP BY nota ORDER BY nota"
    c = conn()
    df = pd.read_sql(q, c)
    c.close()
    return df


def load_estados():
    q = """
        SELECT cu.customer_state AS estado,
               COUNT(DISTINCT o.order_id) AS pedidos,
               ROUND(SUM(oi.price + oi.freight_value),2) AS receita
        FROM orders o
        JOIN order_items oi ON o.order_id    = oi.order_id
        JOIN customers   cu ON o.customer_id = cu.customer_id
        WHERE o.order_status = 'delivered'
        GROUP BY estado ORDER BY receita DESC LIMIT 15
    """
    c = conn()
    df = pd.read_sql(q, c)
    c.close()
    return df


LAYOUT = dict(plot_bgcolor='white', paper_bgcolor='white',
              font=dict(family='Arial', size=13),
              margin=dict(l=40, r=40, t=60, b=40))


# ── 1. Dashboard overview (composição 2×2) ───────────────────────────────────
def gera_overview():
    receita = load_receita_mensal()
    receita = receita.copy()
    receita['mes'] = receita['mes'].dt.strftime('%Y-%m')
    cats = load_categorias()
    avals = load_avaliacoes()
    estados = load_estados()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Receita Mensal (R$)',
            'Top Categorias por Faturamento',
            'Distribuição de Avaliações',
            'Top 15 Estados — Faturamento',
        ),
        vertical_spacing=0.14,
        horizontal_spacing=0.10,
    )

    # Receita mensal
    fig.add_trace(go.Scatter(
        x=receita['mes'], y=receita['receita'],
        mode='lines+markers', name='Receita',
        line=dict(color='#4f46e5', width=2.5),
        fill='tozeroy', fillcolor='rgba(79,70,229,0.10)',
        showlegend=False,
    ), row=1, col=1)

    # Categorias (horizontal bar)
    top10 = cats.head(10).sort_values('receita')
    fig.add_trace(go.Bar(
        x=top10['receita'], y=top10['categoria'],
        orientation='h',
        marker=dict(color=top10['receita'], colorscale='Blues'),
        showlegend=False,
    ), row=1, col=2)

    # Avaliações
    cores_avals = ['#ef4444', '#f97316', '#eab308', '#84cc16', '#22c55e']
    fig.add_trace(go.Bar(
        x=(avals['nota'].astype(str) + ' ⭐'),
        y=avals['quantidade'],
        marker_color=cores_avals,
        showlegend=False,
    ), row=2, col=1)

    # Estados
    fig.add_trace(go.Bar(
        x=estados['estado'], y=estados['receita'],
        marker=dict(color=estados['receita'], colorscale='Purples'),
        showlegend=False,
    ), row=2, col=2)

    fig.update_layout(
        height=820, width=1200,
        title=dict(text='🛒  Olist — Análise de Faturamento  |  2017–2018',
                   font=dict(size=18, color='#1a1a2e'), x=0.5),
        **LAYOUT,
    )
    fig.update_yaxes(tickprefix='R$ ', row=1, col=1)
    fig.update_xaxes(tickprefix='R$ ', row=1, col=2)
    fig.update_yaxes(tickprefix='R$ ', row=2, col=2)

    path = os.path.join(OUT_DIR, 'dashboard_overview.png')
    fig.write_image(path, scale=2)
    print(f'Salvo: {path}')


# ── 2. Receita mensal em destaque ────────────────────────────────────────────
def gera_receita():
    receita = load_receita_mensal()
    receita = receita.copy()
    receita['mes'] = receita['mes'].dt.strftime('%Y-%m')
    kpis = load_kpis()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=receita['mes'], y=receita['receita'],
        mode='lines+markers',
        line=dict(color='#4f46e5', width=3),
        fill='tozeroy', fillcolor='rgba(79,70,229,0.10)',
        marker=dict(size=6),
    ))
    # Anotação de pico
    idx_max = receita['receita'].idxmax()
    fig.add_annotation(
        x=str(receita.loc[idx_max, 'mes']),
        y=receita.loc[idx_max, 'receita'],
        text=f"Pico: R$ {receita.loc[idx_max,'receita']:,.0f}",
        showarrow=True, arrowhead=2,
        font=dict(color='#4f46e5', size=12),
        bgcolor='white', bordercolor='#4f46e5',
    )
    fig.update_layout(
        title=f"Receita Mensal  |  Total: R$ {kpis['receita']:,.0f}  |  {int(kpis['pedidos']):,} pedidos entregues",
        yaxis=dict(tickprefix='R$ '),
        height=400, width=900,
        **LAYOUT,
    )
    path = os.path.join(OUT_DIR, 'receita_mensal.png')
    fig.write_image(path, scale=2)
    print(f'Salvo: {path}')


# ── 3. Top categorias ────────────────────────────────────────────────────────
def gera_categorias():
    cats = load_categorias()
    fig = px.bar(
        cats.sort_values('receita'),
        x='receita', y='categoria', orientation='h',
        color='nota_media', color_continuous_scale='RdYlGn',
        range_color=[1, 5], text='receita',
        labels={'receita': 'Receita (R$)', 'categoria': 'Categoria', 'nota_media': 'Nota'},
        title='Top 12 Categorias por Faturamento  (cor = satisfação média)',
    )
    fig.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
    fig.update_layout(height=500, width=900, **LAYOUT)
    path = os.path.join(OUT_DIR, 'categorias.png')
    fig.write_image(path, scale=2)
    print(f'Salvo: {path}')


if __name__ == '__main__':
    print('Gerando imagens…')
    gera_overview()
    gera_receita()
    gera_categorias()
    print('Concluído! Imagens salvas em images/')
