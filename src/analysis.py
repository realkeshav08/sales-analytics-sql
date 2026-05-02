"""
Analysis helper functions.

Reusable utilities for cohort analysis, RFM scoring,
chart saving, and KPI calculation used across notebooks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns


BASE_DIR = Path(__file__).resolve().parent.parent
FIGURES_DIR = BASE_DIR / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

PALETTE = "viridis"
sns.set_theme(style="whitegrid", palette=PALETTE)


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def save_fig(fig: plt.Figure, filename: str) -> Path:
    """Save a matplotlib figure to reports/figures/.

    Args:
        fig: The figure to save.
        filename: File name (with extension, e.g. 'cohort_heatmap.png').

    Returns:
        Path where the file was saved.
    """
    path = FIGURES_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figure saved: {path}")
    return path


# ---------------------------------------------------------------------------
# Cohort analysis
# ---------------------------------------------------------------------------

def build_cohort_table(orders_df: pd.DataFrame) -> pd.DataFrame:
    """Build a cohort retention table from order data.

    Groups customers by their first-purchase month and tracks how many
    return in subsequent months (month index 0, 1, 2, ...).

    Args:
        orders_df: DataFrame with columns customer_unique_id and order_purchase_timestamp.

    Returns:
        Pivot table (cohort_month × period_number) with retention counts.
    """
    df = orders_df.copy()
    df["order_purchase_timestamp"] = pd.to_datetime(
        df["order_purchase_timestamp"], errors="coerce"
    )
    df = df.dropna(subset=["order_purchase_timestamp", "customer_unique_id"])

    df["order_period"] = df["order_purchase_timestamp"].dt.to_period("M")

    # First purchase month per customer
    cohort_map = (
        df.groupby("customer_unique_id")["order_period"]
        .min()
        .rename("cohort_month")
    )
    df = df.join(cohort_map, on="customer_unique_id")

    df["period_number"] = (
        df["order_period"].astype(int) - df["cohort_month"].astype(int)
    )

    cohort_data = (
        df.groupby(["cohort_month", "period_number"])["customer_unique_id"]
        .nunique()
        .reset_index()
        .rename(columns={"customer_unique_id": "customers"})
    )

    cohort_pivot = cohort_data.pivot(
        index="cohort_month", columns="period_number", values="customers"
    )
    return cohort_pivot


def build_retention_rates(cohort_pivot: pd.DataFrame) -> pd.DataFrame:
    """Convert cohort counts to retention percentages.

    Args:
        cohort_pivot: Cohort pivot table (counts) from build_cohort_table().

    Returns:
        DataFrame of retention rates (0–100%).
    """
    cohort_sizes = cohort_pivot[0]
    retention = cohort_pivot.divide(cohort_sizes, axis=0) * 100
    return retention


def plot_cohort_heatmap(retention: pd.DataFrame, max_periods: int = 12) -> plt.Figure:
    """Plot a cohort retention heatmap.

    Args:
        retention: Retention rate DataFrame from build_retention_rates().
        max_periods: Number of periods (months) to display.

    Returns:
        Matplotlib Figure object.
    """
    data = retention.iloc[:, : max_periods + 1].copy()
    data.index = data.index.astype(str)

    fig, ax = plt.subplots(figsize=(14, max(6, len(data) // 3)))
    sns.heatmap(
        data,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd_r",
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": "Retention %"},
        vmin=0,
        vmax=100,
    )
    ax.set_title("Customer Cohort Retention Heatmap (%)", fontsize=14, pad=12)
    ax.set_xlabel("Months Since First Purchase", fontsize=11)
    ax.set_ylabel("Cohort Month", fontsize=11)
    plt.tight_layout()
    return fig


def compute_avg_retention(retention: pd.DataFrame) -> dict[str, float]:
    """Compute average retention rates at months 1, 3, and 6.

    Args:
        retention: Retention rate DataFrame.

    Returns:
        Dict with keys 'm1', 'm3', 'm6'.
    """
    result: dict[str, float] = {}
    for label, col in [("m1", 1), ("m3", 3), ("m6", 6)]:
        if col in retention.columns:
            result[label] = round(retention[col].dropna().mean(), 2)
        else:
            result[label] = 0.0
    return result


# ---------------------------------------------------------------------------
# RFM scoring
# ---------------------------------------------------------------------------

def compute_rfm(orders_df: pd.DataFrame, items_df: pd.DataFrame) -> pd.DataFrame:
    """Compute Recency, Frequency, Monetary values per customer.

    Args:
        orders_df: Orders table with customer_unique_id and order_purchase_timestamp.
        items_df: Order items table with order_id, price, freight_value.

    Returns:
        DataFrame with columns: customer_unique_id, recency, frequency, monetary.
    """
    orders = orders_df.copy()
    orders["order_purchase_timestamp"] = pd.to_datetime(
        orders["order_purchase_timestamp"], errors="coerce"
    )
    orders = orders.dropna(subset=["order_purchase_timestamp", "customer_unique_id"])

    # Revenue per order
    items = items_df.copy()
    items["order_revenue"] = items["price"] + items["freight_value"]
    order_revenue = items.groupby("order_id")["order_revenue"].sum().reset_index()

    df = orders.merge(order_revenue, on="order_id", how="inner")

    snapshot_date = df["order_purchase_timestamp"].max()

    rfm = (
        df.groupby("customer_unique_id")
        .agg(
            recency=("order_purchase_timestamp", lambda x: (snapshot_date - x.max()).days),
            frequency=("order_id", "nunique"),
            monetary=("order_revenue", "sum"),
        )
        .reset_index()
    )
    return rfm


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """Add quintile scores (1–5) for R, F, M and combine into rfm_score.

    Higher R score = more recent (lower recency days).
    Higher F, M scores = higher frequency / monetary.

    Args:
        rfm: DataFrame from compute_rfm().

    Returns:
        DataFrame with r_score, f_score, m_score, rfm_score columns added.
    """
    rfm = rfm.copy()

    # Recency: lower days = better = score 5
    rfm["r_score"] = pd.qcut(rfm["recency"], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]).astype(int)

    rfm["rfm_score"] = rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)
    return rfm


def assign_segment(row: pd.Series) -> str:
    """Assign an RFM segment label based on R, F, M scores.

    Args:
        row: Series with r_score, f_score, m_score integer columns.

    Returns:
        Segment label string.
    """
    r, f, m = row["r_score"], row["f_score"], row["m_score"]

    if r >= 5 and f >= 5 and m >= 5:
        return "Champions"
    elif r >= 4 and f >= 4 and m >= 3:
        return "Loyal Customers"
    elif r >= 3 and f >= 3 and m >= 3:
        return "Potential Loyalists"
    elif r >= 4 and f <= 1 and m <= 2:
        return "New Customers"
    elif r >= 3 and f <= 2 and m <= 3:
        return "Promising"
    elif r <= 2 and f >= 4 and m >= 4:
        return "At Risk"
    elif r <= 2 and f >= 3 and m >= 3:
        return "Needs Attention"
    elif r <= 2 and f <= 2 and m <= 2:
        return "Hibernating"
    else:
        return "About to Sleep"


def label_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    """Apply segment labels to a scored RFM DataFrame.

    Args:
        rfm: Scored RFM DataFrame from score_rfm().

    Returns:
        DataFrame with rfm_segment column added.
    """
    rfm = rfm.copy()
    rfm["rfm_segment"] = rfm.apply(assign_segment, axis=1)

    # Top-20% by monetary value
    threshold = rfm["monetary"].quantile(0.80)
    rfm["is_high_value"] = (rfm["monetary"] >= threshold).astype(int)
    return rfm


# ---------------------------------------------------------------------------
# Plotting helpers for RFM
# ---------------------------------------------------------------------------

def plot_segment_distribution(rfm: pd.DataFrame) -> plt.Figure:
    """Bar chart of customer count per RFM segment.

    Args:
        rfm: DataFrame with rfm_segment column.

    Returns:
        Matplotlib Figure.
    """
    counts = rfm["rfm_segment"].value_counts().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    counts.plot(kind="barh", ax=ax, color=sns.color_palette(PALETTE, len(counts)))
    ax.set_title("Customer Count by RFM Segment", fontsize=13)
    ax.set_xlabel("Number of Customers")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    for bar in ax.patches:
        ax.text(
            bar.get_width() + 10,
            bar.get_y() + bar.get_height() / 2,
            f"{int(bar.get_width()):,}",
            va="center", fontsize=9,
        )
    plt.tight_layout()
    return fig


def plot_segment_revenue(rfm: pd.DataFrame) -> plt.Figure:
    """Pie chart of revenue contribution by RFM segment.

    Args:
        rfm: DataFrame with rfm_segment and monetary columns.

    Returns:
        Matplotlib Figure.
    """
    revenue = rfm.groupby("rfm_segment")["monetary"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 9))
    wedges, texts, autotexts = ax.pie(
        revenue,
        labels=revenue.index,
        autopct="%1.1f%%",
        startangle=140,
        colors=sns.color_palette(PALETTE, len(revenue)),
        pctdistance=0.82,
    )
    ax.set_title("Revenue Contribution by RFM Segment", fontsize=13, pad=16)
    plt.tight_layout()
    return fig
