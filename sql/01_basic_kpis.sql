-- =============================================================
-- 01_basic_kpis.sql
-- Fundamental business KPIs extracted from the Olist dataset.
-- Executed in: notebooks/02_advanced_sql_analysis.ipynb
-- =============================================================


-- Query 1: Overall KPI Summary
-- Total orders, total revenue, average order value, unique customers
SELECT
    COUNT(DISTINCT o.order_id)          AS total_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2) AS total_revenue,
    ROUND(AVG(order_rev.order_total), 2)  AS avg_order_value,
    COUNT(DISTINCT c.customer_unique_id)  AS unique_customers
FROM orders o
JOIN customers c  ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN (
    SELECT order_id, SUM(price + freight_value) AS order_total
    FROM order_items
    GROUP BY order_id
) order_rev ON o.order_id = order_rev.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable');


-- Query 2: Top 20 Product Categories by Revenue
-- Full join chain: order_items → products → category_translation
SELECT
    COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category,
    COUNT(DISTINCT o.order_id)                            AS total_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2)            AS total_revenue,
    ROUND(AVG(oi.price), 2)                               AS avg_item_price
FROM order_items oi
JOIN orders o       ON oi.order_id = o.order_id
JOIN products p     ON oi.product_id = p.product_id
LEFT JOIN category_translation ct
    ON p.product_category_name = ct.product_category_name
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY category
ORDER BY total_revenue DESC
LIMIT 20;


-- Query 3: Revenue by Brazilian Region
-- Maps 27 states into 4 macro-regions using CASE WHEN
SELECT
    CASE
        WHEN c.customer_state IN ('AM','PA','RO','RR','AC','AP','TO') THEN 'North'
        WHEN c.customer_state IN ('BA','CE','MA','PB','PE','PI','RN','SE','AL') THEN 'Northeast'
        WHEN c.customer_state IN ('GO','MT','MS','DF')                  THEN 'Central-West'
        ELSE 'South/Southeast'
    END AS region,
    COUNT(DISTINCT o.order_id)                   AS total_orders,
    COUNT(DISTINCT c.customer_unique_id)          AS unique_customers,
    ROUND(SUM(oi.price + oi.freight_value), 2)   AS total_revenue,
    ROUND(AVG(oi.price), 2)                       AS avg_item_price
FROM orders o
JOIN customers c    ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY region
ORDER BY total_revenue DESC;


-- Query 4: Monthly Revenue Trend (full dataset period)
-- Uses strftime() to extract year-month from ISO timestamp
SELECT
    strftime('%Y-%m', o.order_purchase_timestamp) AS order_month,
    COUNT(DISTINCT o.order_id)                    AS total_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2)    AS monthly_revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_purchase_timestamp IS NOT NULL
  AND o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY order_month
ORDER BY order_month;


-- Query 5: Top 10 Sellers by Revenue and Order Count
SELECT
    oi.seller_id,
    s.seller_state,
    s.seller_city,
    COUNT(DISTINCT oi.order_id)                  AS total_orders,
    ROUND(SUM(oi.price + oi.freight_value), 2)   AS total_revenue,
    ROUND(AVG(oi.price), 2)                       AS avg_price_per_item
FROM order_items oi
JOIN sellers s ON oi.seller_id = s.seller_id
JOIN orders o  ON oi.order_id = o.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY oi.seller_id, s.seller_state, s.seller_city
ORDER BY total_revenue DESC
LIMIT 10;
