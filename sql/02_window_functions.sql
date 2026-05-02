-- =============================================================
-- 02_window_functions.sql
-- Advanced window function queries demonstrating RANK, SUM OVER,
-- AVG OVER, FIRST_VALUE, LAST_VALUE, and LAG.
-- Executed in: notebooks/02_advanced_sql_analysis.ipynb
-- =============================================================


-- Query 6: Rank Top 5 Products within Each Category by Revenue
-- RANK() OVER (PARTITION BY category ORDER BY revenue DESC)
WITH product_revenue AS (
    SELECT
        COALESCE(ct.product_category_name_english, p.product_category_name) AS category,
        oi.product_id,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS product_revenue,
        COUNT(DISTINCT oi.order_id)                 AS orders_count
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct
        ON p.product_category_name = ct.product_category_name
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY category, oi.product_id
),
ranked AS (
    SELECT
        category,
        product_id,
        product_revenue,
        orders_count,
        RANK() OVER (PARTITION BY category ORDER BY product_revenue DESC) AS rank_in_category
    FROM product_revenue
)
SELECT *
FROM ranked
WHERE rank_in_category <= 5
ORDER BY category, rank_in_category;


-- Query 7: Running Total of Monthly Revenue
-- SUM() OVER (ORDER BY month) — cumulative revenue across the period
WITH monthly AS (
    SELECT
        strftime('%Y-%m', o.order_purchase_timestamp) AS month,
        ROUND(SUM(oi.price + oi.freight_value), 2)    AS monthly_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_purchase_timestamp IS NOT NULL
      AND o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY month
)
SELECT
    month,
    monthly_revenue,
    ROUND(SUM(monthly_revenue) OVER (ORDER BY month), 2) AS running_total_revenue
FROM monthly
ORDER BY month;


-- Query 8: Each Customer's Order Value vs. State Average
-- AVG() OVER (PARTITION BY customer_state) — benchmarks individual orders
WITH order_totals AS (
    SELECT
        o.order_id,
        c.customer_unique_id,
        c.customer_state,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS order_value
    FROM orders o
    JOIN customers c    ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY o.order_id, c.customer_unique_id, c.customer_state
)
SELECT
    order_id,
    customer_unique_id,
    customer_state,
    order_value,
    ROUND(AVG(order_value) OVER (PARTITION BY customer_state), 2) AS state_avg_order_value,
    ROUND(order_value - AVG(order_value) OVER (PARTITION BY customer_state), 2) AS diff_from_state_avg
FROM order_totals
ORDER BY customer_state, order_value DESC
LIMIT 500;


-- Query 9: First and Last Order Date per Customer
-- FIRST_VALUE / LAST_VALUE over customer's order history
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY c.customer_unique_id
            ORDER BY o.order_purchase_timestamp
        ) AS rn_asc,
        ROW_NUMBER() OVER (
            PARTITION BY c.customer_unique_id
            ORDER BY o.order_purchase_timestamp DESC
        ) AS rn_desc
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_purchase_timestamp IS NOT NULL
)
SELECT
    customer_unique_id,
    MAX(CASE WHEN rn_asc  = 1 THEN order_purchase_timestamp END) AS first_order_date,
    MAX(CASE WHEN rn_desc = 1 THEN order_purchase_timestamp END) AS last_order_date,
    COUNT(order_id)                                               AS total_orders
FROM customer_orders
GROUP BY customer_unique_id
HAVING total_orders >= 2
ORDER BY total_orders DESC
LIMIT 200;


-- Query 10: Days Between Consecutive Orders per Customer (LAG)
-- LAG(order_date) OVER (PARTITION BY customer ORDER BY order_date)
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_purchase_timestamp                          AS order_date,
        LAG(o.order_purchase_timestamp) OVER (
            PARTITION BY c.customer_unique_id
            ORDER BY o.order_purchase_timestamp
        )                                                   AS prev_order_date
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_purchase_timestamp IS NOT NULL
)
SELECT
    customer_unique_id,
    order_date,
    prev_order_date,
    ROUND(
        (julianday(order_date) - julianday(prev_order_date)), 0
    ) AS days_since_prev_order
FROM customer_orders
WHERE prev_order_date IS NOT NULL
ORDER BY days_since_prev_order ASC
LIMIT 300;
