-- =============================================================
-- 05_rfm_segmentation.sql
-- RFM (Recency, Frequency, Monetary) customer segmentation.
-- Uses NTILE(5) window function to score each dimension 1–5,
-- then assigns business segment labels via CASE WHEN.
-- Executed in: notebooks/04_rfm_segmentation.ipynb
-- =============================================================


-- Step 1: Compute raw RFM values per customer
WITH rfm_base AS (
    SELECT
        c.customer_unique_id,
        -- Days since last order (relative to the latest order in dataset)
        CAST(
            julianday((SELECT MAX(order_purchase_timestamp) FROM orders))
            - julianday(MAX(o.order_purchase_timestamp))
        AS INTEGER)                              AS recency,
        COUNT(DISTINCT o.order_id)               AS frequency,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS monetary
    FROM orders o
    JOIN customers c    ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
      AND o.order_purchase_timestamp IS NOT NULL
    GROUP BY c.customer_unique_id
),

-- Step 2: Score each dimension into quintiles using NTILE(5)
-- Recency:  lower days → better → score 5  (NTILE reversed)
-- Frequency, Monetary: higher → better → score 5 (NTILE normal)
rfm_scored AS (
    SELECT
        customer_unique_id,
        recency,
        frequency,
        monetary,
        -- For recency: ORDER BY DESC so the most recent gets bucket 1 → we flip to 5
        6 - NTILE(5) OVER (ORDER BY recency DESC)  AS r_score,   -- high = recent
        NTILE(5) OVER (ORDER BY frequency ASC)      AS f_score,   -- high = frequent
        NTILE(5) OVER (ORDER BY monetary ASC)       AS m_score    -- high = high spend
    FROM rfm_base
),

-- Step 3: Combine into RFM score string and assign segment labels
rfm_segments AS (
    SELECT
        customer_unique_id,
        recency,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        CAST(r_score AS TEXT) || CAST(f_score AS TEXT) || CAST(m_score AS TEXT) AS rfm_score,
        CASE
            WHEN r_score >= 5 AND f_score >= 5 AND m_score >= 5
                THEN 'Champions'
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 3
                THEN 'Loyal Customers'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3
                THEN 'Potential Loyalists'
            WHEN r_score >= 4 AND f_score <= 1 AND m_score <= 2
                THEN 'New Customers'
            WHEN r_score >= 3 AND f_score <= 2 AND m_score <= 3
                THEN 'Promising'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4
                THEN 'At Risk'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3
                THEN 'Needs Attention'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2
                THEN 'Hibernating'
            ELSE 'About to Sleep'
        END AS rfm_segment
    FROM rfm_scored
)

-- Final output
SELECT *
FROM rfm_segments
ORDER BY monetary DESC;


-- ----------------------------------------------------------------
-- Segment Summary: count and revenue per segment
-- ----------------------------------------------------------------
WITH rfm_base AS (
    SELECT
        c.customer_unique_id,
        CAST(
            julianday((SELECT MAX(order_purchase_timestamp) FROM orders))
            - julianday(MAX(o.order_purchase_timestamp))
        AS INTEGER)                              AS recency,
        COUNT(DISTINCT o.order_id)               AS frequency,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS monetary
    FROM orders o
    JOIN customers c    ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
      AND o.order_purchase_timestamp IS NOT NULL
    GROUP BY c.customer_unique_id
),
rfm_scored AS (
    SELECT
        customer_unique_id, recency, frequency, monetary,
        6 - NTILE(5) OVER (ORDER BY recency DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)    AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)     AS m_score
    FROM rfm_base
),
rfm_labeled AS (
    SELECT *,
        CASE
            WHEN r_score >= 5 AND f_score >= 5 AND m_score >= 5 THEN 'Champions'
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Potential Loyalists'
            WHEN r_score >= 4 AND f_score <= 1 AND m_score <= 2 THEN 'New Customers'
            WHEN r_score >= 3 AND f_score <= 2 AND m_score <= 3 THEN 'Promising'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'Needs Attention'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Hibernating'
            ELSE 'About to Sleep'
        END AS rfm_segment
    FROM rfm_scored
)
SELECT
    rfm_segment,
    COUNT(*)                            AS customer_count,
    ROUND(AVG(recency), 1)              AS avg_recency_days,
    ROUND(AVG(frequency), 2)            AS avg_orders,
    ROUND(AVG(monetary), 2)             AS avg_revenue,
    ROUND(SUM(monetary), 2)             AS total_revenue,
    ROUND(100.0 * SUM(monetary) / (SELECT SUM(monetary) FROM rfm_base), 2) AS revenue_pct
FROM rfm_labeled
GROUP BY rfm_segment
ORDER BY total_revenue DESC;


-- ----------------------------------------------------------------
-- Pareto: Top 20% customers vs. their revenue share
-- ----------------------------------------------------------------
WITH rfm_base AS (
    SELECT
        c.customer_unique_id,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS monetary
    FROM orders o
    JOIN customers c    ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
),
threshold AS (
    SELECT monetary AS p80_value
    FROM rfm_base
    ORDER BY monetary
    LIMIT 1 OFFSET (
        SELECT CAST(COUNT(*) * 0.8 AS INTEGER) FROM rfm_base
    )
)
SELECT
    COUNT(CASE WHEN r.monetary >= t.p80_value THEN 1 END)  AS top20_pct_customers,
    COUNT(*)                                                AS total_customers,
    ROUND(100.0 * SUM(CASE WHEN r.monetary >= t.p80_value THEN r.monetary ELSE 0 END)
          / SUM(r.monetary), 2)                             AS top20_revenue_pct,
    ROUND(SUM(r.monetary), 2)                               AS total_revenue
FROM rfm_base r, threshold t;
