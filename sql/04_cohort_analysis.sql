-- =============================================================
-- 04_cohort_analysis.sql
-- Customer cohort analysis: groups customers by first-purchase
-- month and tracks repeat-purchase activity in subsequent months.
-- Executed in: notebooks/03_cohort_analysis.ipynb
-- =============================================================


-- Step 1: Assign each customer their cohort month (first purchase)
WITH first_purchase AS (
    SELECT
        c.customer_unique_id,
        MIN(strftime('%Y-%m', o.order_purchase_timestamp)) AS cohort_month
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_purchase_timestamp IS NOT NULL
      AND o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
),

-- Step 2: All orders with their cohort label attached
all_orders AS (
    SELECT
        c.customer_unique_id,
        fp.cohort_month,
        strftime('%Y-%m', o.order_purchase_timestamp) AS order_month
    FROM orders o
    JOIN customers c  ON o.customer_id = c.customer_id
    JOIN first_purchase fp ON c.customer_unique_id = fp.customer_unique_id
    WHERE o.order_purchase_timestamp IS NOT NULL
      AND o.order_status NOT IN ('canceled', 'unavailable')
),

-- Step 3: Compute period index (months since first purchase)
-- Uses SQLite date arithmetic via julianday
cohort_periods AS (
    SELECT
        cohort_month,
        order_month,
        customer_unique_id,
        -- Number of full months between cohort month and order month
        (
            (CAST(substr(order_month, 1, 4) AS INTEGER) * 12
             + CAST(substr(order_month, 6, 2) AS INTEGER))
            -
            (CAST(substr(cohort_month, 1, 4) AS INTEGER) * 12
             + CAST(substr(cohort_month, 6, 2) AS INTEGER))
        ) AS period_number
    FROM all_orders
),

-- Step 4: Count unique customers per cohort × period
cohort_counts AS (
    SELECT
        cohort_month,
        period_number,
        COUNT(DISTINCT customer_unique_id) AS customers
    FROM cohort_periods
    GROUP BY cohort_month, period_number
),

-- Step 5: Cohort sizes (period 0 = the baseline month)
cohort_sizes AS (
    SELECT cohort_month, customers AS cohort_size
    FROM cohort_counts
    WHERE period_number = 0
)

-- Final: retention count + rate for each cohort × period
SELECT
    cc.cohort_month,
    cs.cohort_size,
    cc.period_number,
    cc.customers                                          AS returning_customers,
    ROUND(100.0 * cc.customers / cs.cohort_size, 2)      AS retention_rate_pct
FROM cohort_counts cc
JOIN cohort_sizes cs ON cc.cohort_month = cs.cohort_month
WHERE cc.cohort_month >= '2017-01'   -- focus on complete cohort data
  AND cc.period_number <= 12
ORDER BY cc.cohort_month, cc.period_number;


-- ----------------------------------------------------------------
-- Summary: Average retention rates at 1, 3, and 6 months
-- ----------------------------------------------------------------
WITH first_purchase AS (
    SELECT
        c.customer_unique_id,
        MIN(strftime('%Y-%m', o.order_purchase_timestamp)) AS cohort_month
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_purchase_timestamp IS NOT NULL
      AND o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
),
all_orders AS (
    SELECT
        c.customer_unique_id,
        fp.cohort_month,
        strftime('%Y-%m', o.order_purchase_timestamp) AS order_month
    FROM orders o
    JOIN customers c  ON o.customer_id = c.customer_id
    JOIN first_purchase fp ON c.customer_unique_id = fp.customer_unique_id
    WHERE o.order_purchase_timestamp IS NOT NULL
      AND o.order_status NOT IN ('canceled', 'unavailable')
),
cohort_periods AS (
    SELECT
        cohort_month,
        customer_unique_id,
        (
            (CAST(substr(order_month, 1, 4) AS INTEGER) * 12
             + CAST(substr(order_month, 6, 2) AS INTEGER))
            -
            (CAST(substr(cohort_month, 1, 4) AS INTEGER) * 12
             + CAST(substr(cohort_month, 6, 2) AS INTEGER))
        ) AS period_number
    FROM all_orders
),
cohort_counts AS (
    SELECT cohort_month, period_number, COUNT(DISTINCT customer_unique_id) AS customers
    FROM cohort_periods
    GROUP BY cohort_month, period_number
),
cohort_sizes AS (
    SELECT cohort_month, customers AS cohort_size
    FROM cohort_counts
    WHERE period_number = 0
),
retention AS (
    SELECT
        cc.cohort_month,
        cs.cohort_size,
        cc.period_number,
        ROUND(100.0 * cc.customers / cs.cohort_size, 2) AS retention_rate_pct
    FROM cohort_counts cc
    JOIN cohort_sizes cs ON cc.cohort_month = cs.cohort_month
)
SELECT
    ROUND(AVG(CASE WHEN period_number = 1 THEN retention_rate_pct END), 2) AS avg_1mo_retention,
    ROUND(AVG(CASE WHEN period_number = 3 THEN retention_rate_pct END), 2) AS avg_3mo_retention,
    ROUND(AVG(CASE WHEN period_number = 6 THEN retention_rate_pct END), 2) AS avg_6mo_retention
FROM retention
WHERE cohort_month >= '2017-01';
