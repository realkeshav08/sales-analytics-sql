"""
End-to-end validation script.
Runs cohort analysis, RFM, and Power BI export — equivalent to notebooks 03-05.
"""
import json
import sys
import warnings

# Suppress only the noisy third-party deprecation chatter from pandas/seaborn so
# the pipeline output stays readable. Real warnings (e.g. RuntimeWarning from our
# own numeric code) are still shown.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, ".")

import matplotlib

matplotlib.use("Agg")
from pathlib import Path

import pandas as pd

from src.analysis import (
    build_cohort_table,
    build_retention_rates,
    compute_avg_retention,
    label_segments,
    plot_cohort_heatmap,
    plot_segment_distribution,
    plot_segment_revenue,
    save_fig,
    score_rfm,
)
from src.db_setup import get_engine
from src.etl import (
    attach_cohort_month,
    attach_rfm_segments,
    build_master_flat_table,
    export_powerbi_csv,
)

engine = get_engine()
reports_dir = Path("reports")
reports_dir.mkdir(exist_ok=True)

# ============================================================
# COHORT ANALYSIS
# ============================================================
print("\n=== Cohort Analysis ===")
orders_sql = (
    "SELECT o.order_id, c.customer_unique_id, o.order_purchase_timestamp "
    "FROM orders o JOIN customers c ON o.customer_id=c.customer_id "
    "WHERE o.order_purchase_timestamp IS NOT NULL "
    "  AND o.order_status NOT IN ('canceled','unavailable')"
)
orders_df = pd.read_sql_query(orders_sql, engine)
orders_df["order_purchase_timestamp"] = pd.to_datetime(
    orders_df["order_purchase_timestamp"], errors="coerce"
)
orders_df = orders_df.dropna(subset=["order_purchase_timestamp"])
print(f"  Orders loaded: {len(orders_df):,}")

cohort_pivot = build_cohort_table(orders_df)
cohort_filtered = cohort_pivot[cohort_pivot.index.astype(str) >= "2017-01"]
retention = build_retention_rates(cohort_filtered)
avg_ret = compute_avg_retention(retention)
print(f"  Avg 1-month retention: {avg_ret['m1']:.2f}%")
print(f"  Avg 3-month retention: {avg_ret['m3']:.2f}%")
print(f"  Avg 6-month retention: {avg_ret['m6']:.2f}%")

fig = plot_cohort_heatmap(retention, max_periods=12)
save_fig(fig, "cohort_retention_heatmap.png")

# Save cohort map to DB
cohort_map_sql = (
    "SELECT c.customer_unique_id, "
    "       MIN(strftime('%Y-%m', o.order_purchase_timestamp)) AS cohort_month "
    "FROM orders o JOIN customers c ON o.customer_id=c.customer_id "
    "WHERE o.order_purchase_timestamp IS NOT NULL "
    "  AND o.order_status NOT IN ('canceled','unavailable') "
    "GROUP BY c.customer_unique_id"
)
cohort_map = pd.read_sql_query(cohort_map_sql, engine)
cohort_map.to_sql("customer_cohorts", engine, if_exists="replace", index=False)
print(f"  customer_cohorts table: {len(cohort_map):,} rows")

# ============================================================
# RFM SEGMENTATION
# ============================================================
print("\n=== RFM Segmentation ===")
rfm_sql = (
    "SELECT c.customer_unique_id, "
    "  CAST(julianday((SELECT MAX(order_purchase_timestamp) FROM orders)) "
    "       - julianday(MAX(o.order_purchase_timestamp)) AS INTEGER) AS recency, "
    "  COUNT(DISTINCT o.order_id) AS frequency, "
    "  ROUND(SUM(oi.price + oi.freight_value), 2) AS monetary "
    "FROM orders o "
    "JOIN customers c    ON o.customer_id = c.customer_id "
    "JOIN order_items oi ON o.order_id = oi.order_id "
    "WHERE o.order_status NOT IN ('canceled','unavailable') "
    "  AND o.order_purchase_timestamp IS NOT NULL "
    "GROUP BY c.customer_unique_id"
)
rfm_base = pd.read_sql_query(rfm_sql, engine)
print(f"  Customers scored: {len(rfm_base):,}")

rfm_scored  = score_rfm(rfm_base)
rfm_labeled = label_segments(rfm_scored)

print("  Segment distribution:")
for seg, cnt in rfm_labeled["rfm_segment"].value_counts().items():
    print(f"    {seg:<25} {cnt:>6,}")

total_rev = rfm_labeled["monetary"].sum()
hv_rev    = rfm_labeled[rfm_labeled["is_high_value"] == 1]["monetary"].sum()
hv_pct    = hv_rev / total_rev * 100
print(f"  Top-20% revenue share: {hv_pct:.1f}%")

fig1 = plot_segment_distribution(rfm_labeled)
save_fig(fig1, "rfm_segment_sizes.png")
fig2 = plot_segment_revenue(rfm_labeled)
save_fig(fig2, "rfm_revenue_contribution.png")

rfm_db = rfm_labeled[[
    "customer_unique_id", "recency", "frequency", "monetary",
    "r_score", "f_score", "m_score", "rfm_score", "rfm_segment", "is_high_value",
]].copy()
rfm_db.to_sql("rfm_segments", engine, if_exists="replace", index=False)
print(f"  rfm_segments table: {len(rfm_db):,} rows")

# ============================================================
# POWER BI EXPORT
# ============================================================
print("\n=== Power BI Export ===")
flat = build_master_flat_table(engine)
flat = attach_rfm_segments(flat, engine)
flat = attach_cohort_month(flat, engine)
csv_path = export_powerbi_csv(flat)

# Validate
exported = pd.read_csv(csv_path)
print(f"  Export rows: {len(exported):,}")
assert len(exported) >= 100_000, f"Expected 100k+ rows, got {len(exported):,}"
print("  Validation PASSED: 100,000+ rows confirmed.")

# ============================================================
# UPDATE KPI SUMMARY
# ============================================================
kpi_path = reports_dir / "kpi_summary.json"
existing = json.loads(kpi_path.read_text()) if kpi_path.exists() else {}
existing["cohort_retention"] = avg_ret
existing["rfm"] = {
    "total_customers_scored": int(len(rfm_labeled)),
    "high_value_pct_of_revenue": round(float(hv_pct), 1),
    "segment_counts": {k: int(v) for k, v in rfm_labeled["rfm_segment"].value_counts().items()},
}

rev_by_year = flat.groupby("order_year")["total_item_value"].sum()
existing["executive_kpis"] = {
    "total_revenue_brl":    round(float(flat["total_item_value"].sum()), 2),
    "total_orders":         int(flat["order_id"].nunique()),
    "avg_order_value_brl":  round(float(flat.groupby("order_id")["total_item_value"].sum().mean()), 2),
    "total_customers":      int(flat["customer_id"].nunique()),
    "product_categories":   int(flat["product_category_english"].nunique()),
    "states_covered":       int(flat["customer_state"].nunique()),
    "powerbi_export_rows":  int(len(exported)),
}
if 2017 in rev_by_year.index and 2018 in rev_by_year.index:
    yoy = (rev_by_year[2018] - rev_by_year[2017]) / rev_by_year[2017] * 100
    existing["executive_kpis"]["yoy_total_growth_pct"] = round(float(yoy), 1)

kpi_path.write_text(json.dumps(existing, indent=2, default=str))
print(f"\n  KPI summary written to {kpi_path}")
print("\n=== All validations passed. Pipeline complete. ===")
