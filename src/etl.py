"""
ETL (Extract, Transform, Load) utilities.

Handles data cleaning, region mapping, derived column computation,
and building the denormalized Power BI export table.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import create_engine


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "sales_master.db"
POWERBI_DIR = BASE_DIR / "data" / "powerbi"


# Brazilian state → region mapping
STATE_REGION_MAP: dict[str, str] = {
    # North
    "AM": "North", "PA": "North", "RO": "North", "RR": "North",
    "AC": "North", "AP": "North", "TO": "North",
    # Northeast
    "BA": "Northeast", "CE": "Northeast", "MA": "Northeast", "PB": "Northeast",
    "PE": "Northeast", "PI": "Northeast", "RN": "Northeast", "SE": "Northeast",
    "AL": "Northeast",
    # Central-West
    "GO": "Central-West", "MT": "Central-West", "MS": "Central-West", "DF": "Central-West",
    # South & Southeast
    "SP": "South/Southeast", "RJ": "South/Southeast", "MG": "South/Southeast",
    "ES": "South/Southeast", "PR": "South/Southeast", "SC": "South/Southeast",
    "RS": "South/Southeast",
}


def get_engine():
    """Return SQLAlchemy engine for the project SQLite database."""
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def map_region(state: str) -> str:
    """Map a Brazilian state abbreviation to its macro-region.

    Args:
        state: Two-letter state abbreviation (uppercase).

    Returns:
        Region name string.
    """
    return STATE_REGION_MAP.get(str(state).upper(), "Other")


def compute_delivery_days(df: pd.DataFrame) -> pd.Series:
    """Compute delivery time in days from purchase to delivery.

    Args:
        df: DataFrame containing order timestamp columns.

    Returns:
        Series of delivery days (float, NaN where delivery not recorded).
    """
    # Column is aliased to order_date in the flat table SQL
    purchase_col = "order_date" if "order_date" in df.columns else "order_purchase_timestamp"
    purchase = pd.to_datetime(df[purchase_col], errors="coerce")
    delivered = pd.to_datetime(df["order_delivered_customer_date"], errors="coerce")
    return (delivered - purchase).dt.days


def build_master_flat_table(engine) -> pd.DataFrame:
    """Build the fully denormalized flat table used for Power BI export.

    Joins orders → customers → order_items → products → category_translation
    → payments → reviews and computes derived columns.

    Args:
        engine: SQLAlchemy engine connected to sales_master.db.

    Returns:
        DataFrame with 100,000+ rows, one row per order line item.
    """
    query = """
    SELECT
        o.order_id,
        o.order_purchase_timestamp        AS order_date,
        o.order_status,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,

        c.customer_id,
        c.customer_unique_id,
        c.customer_state,
        c.customer_city,

        oi.order_item_id,
        oi.product_id,
        oi.seller_id,
        oi.price,
        oi.freight_value,
        (oi.price + oi.freight_value)     AS total_item_value,

        p.product_category_name,
        ct.product_category_name_english,
        p.product_weight_g,

        s.seller_state,

        pay.payment_type,
        pay.payment_installments,
        pay.payment_value,

        r.review_score

    FROM orders o
    LEFT JOIN customers c
        ON o.customer_id = c.customer_id
    LEFT JOIN order_items oi
        ON o.order_id = oi.order_id
    LEFT JOIN products p
        ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct
        ON p.product_category_name = ct.product_category_name
    LEFT JOIN sellers s
        ON oi.seller_id = s.seller_id
    LEFT JOIN (
        SELECT order_id,
               payment_type,
               payment_installments,
               SUM(payment_value) AS payment_value
        FROM payments
        GROUP BY order_id
    ) pay ON o.order_id = pay.order_id
    LEFT JOIN (
        SELECT order_id, AVG(review_score) AS review_score
        FROM reviews
        GROUP BY order_id
    ) r ON o.order_id = r.order_id
    WHERE oi.order_id IS NOT NULL
    """
    df = pd.read_sql_query(query, engine)

    # --- Derived columns ---
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["order_year"] = df["order_date"].dt.year
    df["order_month"] = df["order_date"].dt.month
    df["order_quarter"] = df["order_date"].dt.quarter
    df["order_month_label"] = df["order_date"].dt.to_period("M").astype(str)

    df["customer_region"] = df["customer_state"].map(map_region)

    df["product_weight_kg"] = df["product_weight_g"].fillna(0) / 1000.0

    df["delivery_days"] = compute_delivery_days(df)

    # Fallback English category name
    df["product_category_english"] = (
        df["product_category_name_english"]
        .fillna(df["product_category_name"])
        .fillna("unknown")
    )

    return df


def attach_rfm_segments(df: pd.DataFrame, engine) -> pd.DataFrame:
    """Join RFM segment labels onto the flat table.

    Expects an rfm_segments table in the database (created by notebook 04).

    Args:
        df: Master flat table DataFrame.
        engine: SQLAlchemy engine.

    Returns:
        DataFrame with rfm_segment and is_high_value_customer columns added.
    """
    try:
        rfm = pd.read_sql_query(
            "SELECT customer_unique_id, rfm_segment, is_high_value FROM rfm_segments",
            engine,
        )
        df = df.merge(rfm, on="customer_unique_id", how="left")
        df["rfm_segment"] = df["rfm_segment"].fillna("Unscored")
        df["is_high_value_customer"] = df["is_high_value"].fillna(0).astype(int)
        df.drop(columns=["is_high_value"], inplace=True, errors="ignore")
    except Exception:
        df["rfm_segment"] = "Unscored"
        df["is_high_value_customer"] = 0
    return df


def attach_cohort_month(df: pd.DataFrame, engine) -> pd.DataFrame:
    """Join customer cohort month (first purchase month) onto the flat table.

    Args:
        df: Master flat table DataFrame.
        engine: SQLAlchemy engine.

    Returns:
        DataFrame with customer_cohort_month column added.
    """
    try:
        cohort = pd.read_sql_query(
            "SELECT customer_unique_id, cohort_month AS customer_cohort_month FROM customer_cohorts",
            engine,
        )
        df = df.merge(cohort, on="customer_unique_id", how="left")
        df["customer_cohort_month"] = df["customer_cohort_month"].fillna("Unknown")
    except Exception:
        df["customer_cohort_month"] = "Unknown"
    return df


def export_powerbi_csv(df: pd.DataFrame) -> Path:
    """Save the Power BI export table as CSV and XLSX.

    Args:
        df: Fully prepared flat DataFrame.

    Returns:
        Path to the saved CSV file.
    """
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = POWERBI_DIR / "powerbi_export.csv"
    xlsx_path = POWERBI_DIR / "powerbi_export.xlsx"

    # Select and order final columns
    final_cols = [
        "order_id", "order_date", "order_year", "order_month", "order_quarter",
        "order_month_label", "order_status",
        "customer_id", "customer_unique_id", "customer_state", "customer_city",
        "customer_region",
        "product_id", "product_category_english", "product_weight_kg",
        "seller_id", "seller_state",
        "price", "freight_value", "total_item_value",
        "payment_type", "payment_installments", "payment_value",
        "review_score",
        "delivery_days",
        "rfm_segment", "customer_cohort_month", "is_high_value_customer",
    ]
    export_df = df[[c for c in final_cols if c in df.columns]]

    export_df.to_csv(csv_path, index=False)
    export_df.to_excel(xlsx_path, index=False, engine="openpyxl")
    print(f"Power BI export: {len(export_df):,} rows")
    print(f"  CSV  -> {csv_path}")
    print(f"  XLSX -> {xlsx_path}")
    return csv_path
