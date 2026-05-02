"""
Database setup module.

Creates the SQLite database, loads all CSV files as tables,
creates indexes on foreign keys, and validates row counts.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = PROCESSED_DIR / "sales_master.db"
REPORTS_DIR = BASE_DIR / "reports"


# ---------------------------------------------------------------------------
# CSV → table mapping
# ---------------------------------------------------------------------------
CSV_TABLE_MAP: dict[str, str] = {
    "olist_orders_dataset.csv": "orders",
    "olist_customers_dataset.csv": "customers",
    "olist_order_items_dataset.csv": "order_items",
    "olist_products_dataset.csv": "products",
    "olist_order_payments_dataset.csv": "payments",
    "olist_order_reviews_dataset.csv": "reviews",
    "olist_sellers_dataset.csv": "sellers",
    "olist_geolocation_dataset.csv": "geolocation",
    "product_category_name_translation.csv": "category_translation",
}

# Expected minimum row counts for validation
EXPECTED_ROWS: dict[str, int] = {
    "orders": 90_000,
    "customers": 90_000,
    "order_items": 100_000,
    "products": 30_000,
    "payments": 100_000,
    "reviews": 90_000,
    "sellers": 3_000,
    "geolocation": 900_000,
    "category_translation": 60,
}

# Datetime columns per table
DATETIME_COLS: dict[str, list[str]] = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}


def get_engine():
    """Return a SQLAlchemy engine connected to the SQLite database."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def load_csv(file_name: str, parse_dates: bool = True) -> pd.DataFrame:
    """Load a single CSV from the raw data directory.

    Args:
        file_name: CSV filename (not full path).
        parse_dates: Whether to attempt parsing datetime columns.

    Returns:
        DataFrame with data from the CSV.
    """
    path = RAW_DIR / file_name
    table = CSV_TABLE_MAP[file_name]
    date_cols = DATETIME_COLS.get(table, []) if parse_dates else []

    df = pd.read_csv(
        path,
        parse_dates=date_cols if date_cols else False,
        infer_datetime_format=True,
        low_memory=False,
    )
    return df


def create_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes on foreign key columns for query performance."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_items_seller ON order_items(seller_id)",
        "CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_order ON reviews(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(customer_state)",
        "CREATE INDEX IF NOT EXISTS idx_sellers_state ON sellers(seller_state)",
        "CREATE INDEX IF NOT EXISTS idx_products_category ON products(product_category_name)",
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status)",
        "CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts ON orders(order_purchase_timestamp)",
    ]
    for ddl in indexes:
        conn.execute(ddl)
    conn.commit()
    print(f"  Created {len(indexes)} indexes.")


def load_all_tables(engine) -> dict[str, int]:
    """Load every CSV into the database and return actual row counts.

    Args:
        engine: SQLAlchemy engine.

    Returns:
        Dict mapping table name → actual row count loaded.
    """
    row_counts: dict[str, int] = {}

    for csv_file, table_name in CSV_TABLE_MAP.items():
        print(f"  Loading {csv_file} → {table_name} ...", end=" ", flush=True)
        df = load_csv(csv_file)
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        count = len(df)
        row_counts[table_name] = count
        print(f"{count:,} rows")

    return row_counts


def validate_row_counts(row_counts: dict[str, int]) -> bool:
    """Validate that loaded row counts meet minimum thresholds.

    Args:
        row_counts: Dict of table → actual count.

    Returns:
        True if all tables pass validation.
    """
    all_pass = True
    print("\nRow count validation:")
    print(f"  {'Table':<25} {'Actual':>10}  {'Min Expected':>14}  {'Status'}")
    print("  " + "-" * 60)
    for table, minimum in EXPECTED_ROWS.items():
        actual = row_counts.get(table, 0)
        status = "PASS" if actual >= minimum else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  {table:<25} {actual:>10,}  {minimum:>14,}  {status}")
    return all_pass


def save_kpi_summary(row_counts: dict[str, int]) -> None:
    """Write a JSON summary of row counts to reports/kpi_summary.json."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = REPORTS_DIR / "kpi_summary.json"
    summary = {"table_row_counts": row_counts}
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\n  KPI summary written to {summary_path}")


def setup_database() -> dict[str, int]:
    """Full database setup pipeline: load CSVs, index, validate.

    Returns:
        Row counts dict.
    """
    print("=" * 60)
    print("Sales Analytics — Database Setup")
    print("=" * 60)

    engine = get_engine()
    print(f"\nDatabase: {DB_PATH}\n")

    print("Step 1: Loading CSV files...")
    row_counts = load_all_tables(engine)

    print("\nStep 2: Creating indexes...")
    with sqlite3.connect(DB_PATH) as conn:
        create_indexes(conn)

    print("\nStep 3: Validation...")
    validate_row_counts(row_counts)

    save_kpi_summary(row_counts)

    total = row_counts.get("orders", 0) + row_counts.get("order_items", 0)
    print(f"\nTotal orders + order_items rows: {total:,}")
    print("Database setup complete.")
    return row_counts


if __name__ == "__main__":
    setup_database()
