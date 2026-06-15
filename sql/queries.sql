-- ============================================================
-- Olist E-Commerce Brasil — Queries de Análise de Faturamento
-- Autor: Augusto Matos
-- ============================================================


-- ------------------------------------------------------------
-- 1. KPIs Gerais
-- ------------------------------------------------------------
SELECT
    COUNT(DISTINCT o.order_id)                             AS total_pedidos,
    COUNT(DISTINCT o.customer_id)                          AS total_clientes,
    ROUND(SUM(oi.price + oi.freight_value), 2)             AS receita_total,
    ROUND(AVG(oi.price + oi.freight_value), 2)             AS ticket_medio,
    ROUND(AVG(r.review_score), 2)                          AS nota_media,
    COUNT(DISTINCT oi.seller_id)                           AS total_vendedores
FROM orders o
JOIN order_items  oi ON o.order_id = oi.order_id
LEFT JOIN reviews  r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered';


-- ------------------------------------------------------------
-- 2. Receita Mensal
-- ------------------------------------------------------------
SELECT
    STRFTIME('%Y-%m', o.order_purchase_timestamp) AS mes,
    COUNT(DISTINCT o.order_id)                     AS pedidos,
    ROUND(SUM(oi.price + oi.freight_value), 2)     AS receita
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp IS NOT NULL
GROUP BY mes
ORDER BY mes;


-- ------------------------------------------------------------
-- 3. Top 10 Categorias por Faturamento
-- ------------------------------------------------------------
SELECT
    COALESCE(c.product_category_name_english,
             p.product_category_name,
             'Sem Categoria')                       AS categoria,
    COUNT(DISTINCT o.order_id)                      AS pedidos,
    ROUND(SUM(oi.price), 2)                         AS receita,
    ROUND(AVG(oi.price), 2)                         AS ticket_medio,
    ROUND(AVG(r.review_score), 2)                   AS nota_media
FROM orders o
JOIN order_items  oi ON o.order_id    = oi.order_id
JOIN products      p ON oi.product_id = p.product_id
LEFT JOIN categories c ON p.product_category_name = c.product_category_name
LEFT JOIN reviews    r ON o.order_id  = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY categoria
ORDER BY receita DESC
LIMIT 10;


-- ------------------------------------------------------------
-- 4. Receita e Volume por Estado
-- ------------------------------------------------------------
SELECT
    cu.customer_state                           AS estado,
    COUNT(DISTINCT o.order_id)                  AS pedidos,
    ROUND(SUM(oi.price + oi.freight_value), 2)  AS receita,
    ROUND(AVG(oi.price + oi.freight_value), 2)  AS ticket_medio
FROM orders o
JOIN order_items oi ON o.order_id    = oi.order_id
JOIN customers   cu ON o.customer_id = cu.customer_id
WHERE o.order_status = 'delivered'
GROUP BY estado
ORDER BY receita DESC;


-- ------------------------------------------------------------
-- 5. Distribuição de Avaliações
-- ------------------------------------------------------------
SELECT
    review_score                                                           AS nota,
    COUNT(*)                                                               AS quantidade,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1)                    AS percentual
FROM reviews
GROUP BY review_score
ORDER BY review_score;


-- ------------------------------------------------------------
-- 6. Tempo de Entrega Real vs. Estimado por Estado
-- ------------------------------------------------------------
SELECT
    cu.customer_state AS estado,
    ROUND(AVG(
        JULIANDAY(o.order_delivered_customer_date) -
        JULIANDAY(o.order_purchase_timestamp)
    ), 1) AS dias_entrega_real,
    ROUND(AVG(
        JULIANDAY(o.order_estimated_delivery_date) -
        JULIANDAY(o.order_purchase_timestamp)
    ), 1) AS dias_entrega_estimado,
    COUNT(*) AS pedidos
FROM orders o
JOIN customers cu ON o.customer_id = cu.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY estado
HAVING pedidos >= 50
ORDER BY dias_entrega_real DESC;


-- ------------------------------------------------------------
-- 7. Análise de Formas de Pagamento
-- ------------------------------------------------------------
SELECT
    payment_type                        AS forma_pagamento,
    COUNT(DISTINCT order_id)            AS pedidos,
    ROUND(SUM(payment_value), 2)        AS valor_total,
    ROUND(AVG(payment_installments), 1) AS parcelas_medias
FROM payments
WHERE payment_type != 'not_defined'
GROUP BY payment_type
ORDER BY pedidos DESC;


-- ------------------------------------------------------------
-- 8. Clientes por Frequência de Compra
-- ------------------------------------------------------------
SELECT
    compras,
    COUNT(*) AS clientes
FROM (
    SELECT customer_unique_id, COUNT(*) AS compras
    FROM (
        SELECT c.customer_unique_id, o.order_id
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
    )
    GROUP BY customer_unique_id
)
GROUP BY compras
ORDER BY compras;


-- ------------------------------------------------------------
-- 9. Taxa de Cancelamento por Categoria
-- ------------------------------------------------------------
SELECT
    COALESCE(cat.product_category_name_english,
             p.product_category_name, 'Sem Categoria') AS categoria,
    COUNT(CASE WHEN o.order_status = 'canceled' THEN 1 END) AS cancelados,
    COUNT(*)                                                  AS total,
    ROUND(
        COUNT(CASE WHEN o.order_status = 'canceled' THEN 1 END) * 100.0 / COUNT(*),
    2) AS taxa_cancelamento
FROM orders o
JOIN order_items oi  ON o.order_id    = oi.order_id
JOIN products    p   ON oi.product_id = p.product_id
LEFT JOIN categories cat ON p.product_category_name = cat.product_category_name
GROUP BY categoria
HAVING total >= 100
ORDER BY taxa_cancelamento DESC
LIMIT 10;
