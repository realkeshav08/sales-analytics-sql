-- =============================================================
-- 06_yoy_growth.sql
-- Year-over-year (YoY) revenue growth analysis by product
-- category and by customer acquisition rate per state.
-- Executed in: notebooks/02_advanced_sql_analysis.ipynb
-- =============================================================


-- Query 14: YoY Revenue Growth by Category
-- Compares 2017 vs 2018 revenue for each category.
-- Focuses on the top 5 categories (high-value segments) to
-- verify the ~32% growth claim in the resume.
WITH category_yearly AS (
    SELECT
        COALESCE(ct.product_category_name_english, p.product_category_name) AS category,
        strftime('%Y', o.order_purchase_timestamp)                            AS order_year,
        ROUND(SUM(oi.price + oi.freight_value), 2)                           AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p     ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct
        ON p.product_category_name = ct.product_category_name
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
      AND o.order_purchase_timestamp IS NOT NULL
      AND strftime('%Y', o.order_purchase_timestamp) IN ('2017', '2018')
    GROUP BY category, order_year
),
pivoted AS (
    SELECT
        category,
        SUM(CASE WHEN order_year = '2017' THEN revenue ELSE 0 END) AS revenue_2017,
        SUM(CASE WHEN order_year = '2018' THEN revenue ELSE 0 END) AS revenue_2018
    FROM category_yearly
    GROUP BY category
),
-- Identify the top 5 categories by combined revenue (2017+2018)
top_categories AS (
    SELECT category
    FROM pivoted
    ORDER BY (revenue_2017 + revenue_2018) DESC
    LIMIT 5
)
SELECT
    p.category,
    p.revenue_2017,
    p.revenue_2018,
    ROUND(p.revenue_2018 - p.revenue_2017, 2)                                    AS revenue_delta,
    CASE
        WHEN p.revenue_2017 > 0
        THEN ROUND(100.0 * (p.revenue_2018 - p.revenue_2017) / p.revenue_2017, 1)
        ELSE NULL
    END                                                                           AS yoy_growth_pct,
    CASE WHEN t.category IS NOT NULL THEN 'Yes' ELSE 'No' END                    AS is_top5_high_value
FROM pivoted p
LEFT JOIN top_categories t ON p.category = t.category
WHERE p.revenue_2017 > 0 AND p.revenue_2018 > 0
ORDER BY yoy_growth_pct DESC
LIMIT 20;


-- Query 15: YoY Customer Acquisition Rate by State
-- How many NEW customers (first-ever order) were acquired in 2017 vs 2018
WITH first_orders AS (
    SELECT
        c.customer_unique_id,
        c.customer_state,
        MIN(strftime('%Y', o.order_purchase_timestamp)) AS acquisition_year
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_purchase_timestamp IS NOT NULL
      AND o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id, c.customer_state
),
state_yearly AS (
    SELECT
        customer_state,
        acquisition_year,
        COUNT(*) AS new_customers
    FROM first_orders
    WHERE acquisition_year IN ('2017', '2018')
    GROUP BY customer_state, acquisition_year
),
pivoted_state AS (
    SELECT
        customer_state,
        SUM(CASE WHEN acquisition_year = '2017' THEN new_customers ELSE 0 END) AS new_2017,
        SUM(CASE WHEN acquisition_year = '2018' THEN new_customers ELSE 0 END) AS new_2018
    FROM state_yearly
    GROUP BY customer_state
)
SELECT
    customer_state,
    new_2017,
    new_2018,
    (new_2018 - new_2017)                                           AS delta,
    CASE
        WHEN new_2017 > 0
        THEN ROUND(100.0 * (new_2018 - new_2017) / new_2017, 1)
        ELSE NULL
    END                                                             AS yoy_acquisition_growth_pct
FROM pivoted_state
WHERE new_2017 > 0
ORDER BY yoy_acquisition_growth_pct DESC;
