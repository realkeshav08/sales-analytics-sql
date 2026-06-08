"""Unit tests for src/analysis.py cohort and RFM helpers (synthetic data)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis import (
    assign_segment,
    build_cohort_table,
    build_retention_rates,
    compute_avg_retention,
    compute_rfm,
    label_segments,
    score_rfm,
)

# ---------------------------------------------------------------------------
# Cohort analysis
# ---------------------------------------------------------------------------


def _cohort_orders():
    # Two customers. C1 buys in Jan then returns in Feb; C2 only buys in Jan.
    return pd.DataFrame(
        {
            "customer_unique_id": ["C1", "C1", "C2"],
            "order_purchase_timestamp": [
                "2017-01-15",
                "2017-02-10",
                "2017-01-20",
            ],
        }
    )


def test_build_cohort_table_counts():
    pivot = build_cohort_table(_cohort_orders())
    # Single cohort (2017-01) with 2 customers at period 0.
    assert pivot.loc[pivot.index[0], 0] == 2
    # Only C1 returns at period 1.
    assert pivot.loc[pivot.index[0], 1] == 1


def test_build_retention_rates_percentages():
    pivot = build_cohort_table(_cohort_orders())
    retention = build_retention_rates(pivot)
    assert retention.loc[retention.index[0], 0] == 100.0
    assert retention.loc[retention.index[0], 1] == 50.0


def test_compute_avg_retention_keys_and_missing_periods():
    pivot = build_cohort_table(_cohort_orders())
    retention = build_retention_rates(pivot)
    avg = compute_avg_retention(retention)
    assert set(avg) == {"m1", "m3", "m6"}
    # No period 3 or 6 exists in this tiny dataset -> defaults to 0.0.
    assert avg["m3"] == 0.0
    assert avg["m6"] == 0.0


# ---------------------------------------------------------------------------
# RFM
# ---------------------------------------------------------------------------


def _rfm_inputs(n=200, seed=0):
    rng = np.random.default_rng(seed)
    orders = pd.DataFrame(
        {
            "customer_unique_id": [f"C{i}" for i in range(n)],
            "order_id": [f"O{i}" for i in range(n)],
            "order_purchase_timestamp": pd.to_datetime("2018-01-01")
            + pd.to_timedelta(rng.integers(0, 300, n), unit="D"),
        }
    )
    items = pd.DataFrame(
        {
            "order_id": [f"O{i}" for i in range(n)],
            "price": rng.uniform(10, 500, n),
            "freight_value": rng.uniform(0, 50, n),
        }
    )
    return orders, items


def test_compute_rfm_columns_and_nonnegative():
    orders, items = _rfm_inputs()
    rfm = compute_rfm(orders, items)
    assert set(rfm.columns) == {
        "customer_unique_id",
        "recency",
        "frequency",
        "monetary",
    }
    assert (rfm["recency"] >= 0).all()
    assert (rfm["frequency"] >= 1).all()
    assert (rfm["monetary"] > 0).all()


def test_score_rfm_scores_in_range():
    orders, items = _rfm_inputs()
    scored = score_rfm(compute_rfm(orders, items))
    for col in ("r_score", "f_score", "m_score"):
        assert scored[col].between(1, 5).all()
    assert scored["rfm_score"].str.len().eq(3).all()


def test_score_rfm_robust_to_tied_recency():
    """Regression test: many identical recency values must not break qcut."""
    rfm = pd.DataFrame(
        {
            "customer_unique_id": [f"C{i}" for i in range(50)],
            "recency": [7] * 50,  # all identical -> would break naive qcut
            "frequency": list(range(50)),
            "monetary": [float(i) for i in range(50)],
        }
    )
    scored = score_rfm(rfm)  # must not raise
    assert scored["r_score"].between(1, 5).all()


def test_assign_segment_champions_and_hibernating():
    champion = pd.Series({"r_score": 5, "f_score": 5, "m_score": 5})
    hibernating = pd.Series({"r_score": 1, "f_score": 1, "m_score": 1})
    assert assign_segment(champion) == "Champions"
    assert assign_segment(hibernating) == "Hibernating"


def test_label_segments_high_value_flag():
    orders, items = _rfm_inputs()
    labeled = label_segments(score_rfm(compute_rfm(orders, items)))
    assert "rfm_segment" in labeled.columns
    assert set(labeled["is_high_value"].unique()) <= {0, 1}
    # Roughly the top 20% are flagged high value.
    share = labeled["is_high_value"].mean()
    assert 0.1 <= share <= 0.3
