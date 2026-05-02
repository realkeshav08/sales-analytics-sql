-- =============================================================
-- 03_cte_queries.sql
-- Multi-step CTEs demonstrating complex analytical patterns:
-- high-value customer identification, moving averages, and
-- cross-year retention (customers active in both 2017 and 2018).
-- Executed in: notebooks/02_advanced_sql_analysis.ipynb
-- =============================================================


-- Query 11: High-Value Customers (Top 20%) and Their Preferred Categories
-- Step 1 CTE: compute total revenue per customer
-- Step 2 CTE: find the 80th percentile threshold
-- Step 3 CTE: filter to top-20% customers
-- Step 4: join to order items to find their top categories
WITH customer_revenue AS (
    SELECT
        c.customer_unique_id,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS total_spent
    FROM orders o
    JOIN customers c    ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
),
threshold AS (
    -- 80th percentile of customer spend
    SELECT total_spent AS p80
    FROM customer_revenue
    ORDER BY total_spent
    LIMIT 1 OFFSET (
        SELECT CAST(COUNT(*) * 0.8 AS INTEGER) FROM customer_revenue
    )
),
high_value_customers AS (
    SELECT cr.customer_unique_id, cr.total_spent
    FROM customer_revenue cr, threshold t
    WHERE cr.total_spent >= t.p80
),
customer_category_spend AS (
    SELECT
        hvc.customer_unique_id,
        hvc.total_spent,
        COALESCE(ct.product_category_name_english, p.product_category_name) AS category,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS category_spend,
        RANK() OVER (
            PARTITION BY hvc.customer_unique_id
            ORDER BY SUM(oi.price + oi.freight_value) DESC
        ) AS category_rank
    FROM high_value_customers hvc
    JOIN orders o       ON o.customer_id IN (
                             SELECT customer_id FROM customers
                             WHERE customer_unique_id = hvc.customer_unique_id
                           )
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p     ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct
        ON p.product_category_name = ct.product_category_name
    GROUP BY hvc.customer_unique_id, category
)
SELECT
    customer_unique_id,
    total_spent,
    category          AS preferred_category,
    category_spend,
    category_rank
FROM customer_category_spend
WHERE category_rank = 1
ORDER BY total_spent DESC
LIMIT 100;


-- Query 12: Monthly Revenue → 3-Month Moving Average → Growth Flag
-- Demonstrates chained CTE pipeline
WITH monthly_revenue AS (
    SELECT
        strftime('%Y-%m', o.order_purchase_timestamp) AS month,
        ROUND(SUM(oi.price + oi.freight_value), 2)   AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_purchase_timestamp IS NOT NULL
      AND o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY month
),
moving_avg AS (
    SELECT
        month,
        revenue,
        ROUND(
            AVG(revenue) OVER (
                ORDER BY month
                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
            ), 2
        ) AS revenue_3mo_avg
    FROM monthly_revenue
),
growth_flag AS (
    SELECT
        month,
        revenue,
        revenue_3mo_avg,
        LAG(revenue_3mo_avg) OVER (ORDER BY month) AS prev_3mo_avg,
        CASE
            WHEN revenue_3mo_avg > LAG(revenue_3mo_avg) OVER (ORDER BY month)
            THEN 'Growing'
            ELSE 'Declining'
        END AS growth_trend
    FROM moving_avg
)
SELECT *
FROM growth_flag
ORDER BY month;


-- Query 13: Retained Customers — Active in Both 2017 AND 2018
-- Finds customers who placed at least one order in 2017 and one in 2018
WITH orders_2017 AS (
    SELECT DISTINCT c.customer_unique_id
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE strftime('%Y', o.order_purchase_timestamp) = '2017'
      AND o.order_status NOT IN ('canceled', 'unavailable')
),
orders_2018 AS (
    SELECT DISTINCT c.customer_unique_id
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE strftime('%Y', o.order_purchase_timestamp) = '2018'
      AND o.order_status NOT IN ('canceled', 'unavailable')
),
retained AS (
    SELECT a.customer_unique_id
    FROM orders_2017 a
    INNER JOIN orders_2018 b ON a.customer_unique_id = b.customer_unique_id
),
retained_spend AS (
    SELECT
        r.customer_unique_id,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS total_spend_all_years,
        COUNT(DISTINCT o.order_id)                  AS total_orders
    FROM retained r
    JOIN customers c    ON c.customer_unique_id = r.customer_unique_id
    JOIN orders o       ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY r.customer_unique_id
)
SELECT
    COUNT(*)                         AS retained_customer_count,
    ROUND(AVG(total_spend_all_years), 2) AS avg_lifetime_value,
    ROUND(AVG(total_orders), 2)       AS avg_orders_per_retained_customer,
    ROUND(SUM(total_spend_all_years), 2) AS total_revenue_from_retained
FROM retained_spend;
