-- =============================================================
-- schema.sql
-- Documents the SQLite schema for sales_master.db
-- Auto-populated by src/db_setup.py from Olist CSV files.
-- =============================================================

-- Orders: one row per order (99,441 rows)
CREATE TABLE IF NOT EXISTS orders (
    order_id                        TEXT PRIMARY KEY,
    customer_id                     TEXT,
    order_status                    TEXT,
    order_purchase_timestamp        TEXT,   -- ISO datetime
    order_approved_at               TEXT,
    order_delivered_carrier_date    TEXT,
    order_delivered_customer_date   TEXT,
    order_estimated_delivery_date   TEXT
);

-- Customers: unique customer per location (99,441 rows)
CREATE TABLE IF NOT EXISTS customers (
    customer_id         TEXT PRIMARY KEY,
    customer_unique_id  TEXT,
    customer_zip_code   TEXT,
    customer_city       TEXT,
    customer_state      TEXT
);

-- Order Items: line items — multiple per order (112,650 rows)
CREATE TABLE IF NOT EXISTS order_items (
    order_id        TEXT,
    order_item_id   INTEGER,
    product_id      TEXT,
    seller_id       TEXT,
    shipping_limit_date TEXT,
    price           REAL,
    freight_value   REAL
);

-- Products: product catalog (32,951 rows)
CREATE TABLE IF NOT EXISTS products (
    product_id                  TEXT PRIMARY KEY,
    product_category_name       TEXT,
    product_name_length         INTEGER,
    product_description_length  INTEGER,
    product_photos_qty          INTEGER,
    product_weight_g            REAL,
    product_length_cm           REAL,
    product_height_cm           REAL,
    product_width_cm            REAL
);

-- Payments: may contain multiple rows per order (103,886 rows)
CREATE TABLE IF NOT EXISTS payments (
    order_id                TEXT,
    payment_sequential      INTEGER,
    payment_type            TEXT,
    payment_installments    INTEGER,
    payment_value           REAL
);

-- Reviews: customer review scores and text (99,224 rows)
CREATE TABLE IF NOT EXISTS reviews (
    review_id               TEXT,
    order_id                TEXT,
    review_score            INTEGER,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TEXT,
    review_answer_timestamp TEXT
);

-- Sellers: seller location data (3,095 rows)
CREATE TABLE IF NOT EXISTS sellers (
    seller_id           TEXT PRIMARY KEY,
    seller_zip_code     TEXT,
    seller_city         TEXT,
    seller_state        TEXT
);

-- Geolocation: zip code → lat/long (1,000,163 rows)
CREATE TABLE IF NOT EXISTS geolocation (
    geolocation_zip_code_prefix TEXT,
    geolocation_lat             REAL,
    geolocation_lng             REAL,
    geolocation_city            TEXT,
    geolocation_state           TEXT
);

-- Category Translation: Portuguese → English (71 rows)
CREATE TABLE IF NOT EXISTS category_translation (
    product_category_name           TEXT PRIMARY KEY,
    product_category_name_english   TEXT
);

-- =============================================================
-- Indexes (created by db_setup.py after data load)
-- =============================================================
CREATE INDEX IF NOT EXISTS idx_orders_customer   ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_items_order       ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_items_product     ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_items_seller      ON order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_payments_order    ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_order     ON reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_customers_state   ON customers(customer_state);
CREATE INDEX IF NOT EXISTS idx_sellers_state     ON sellers(seller_state);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(product_category_name);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_ts         ON orders(order_purchase_timestamp);
