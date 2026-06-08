"""Unit tests for src/etl.py pure helpers (no database/dataset required)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.etl import compute_delivery_days, map_region


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("SP", "South/Southeast"),
        ("sp", "South/Southeast"),  # case-insensitive
        ("AM", "North"),
        ("BA", "Northeast"),
        ("GO", "Central-West"),
        ("ZZ", "Other"),  # unknown code
        ("", "Other"),
    ],
)
def test_map_region(state, expected):
    assert map_region(state) == expected


def test_map_region_handles_non_string():
    # NaN / None should not raise and should fall back to "Other".
    assert map_region(None) == "Other"
    assert map_region(float("nan")) == "Other"


def test_compute_delivery_days_basic():
    df = pd.DataFrame(
        {
            "order_date": ["2018-01-01", "2018-01-10"],
            "order_delivered_customer_date": ["2018-01-05", "2018-01-12"],
        }
    )
    result = compute_delivery_days(df)
    assert list(result) == [4, 2]


def test_compute_delivery_days_missing_delivery_is_nan():
    df = pd.DataFrame(
        {
            "order_date": ["2018-01-01"],
            "order_delivered_customer_date": [None],
        }
    )
    result = compute_delivery_days(df)
    assert result.isna().all()


def test_compute_delivery_days_falls_back_to_raw_timestamp_column():
    # When the aliased "order_date" column is absent it should use the raw name.
    df = pd.DataFrame(
        {
            "order_purchase_timestamp": ["2018-01-01"],
            "order_delivered_customer_date": ["2018-01-04"],
        }
    )
    result = compute_delivery_days(df)
    assert list(result) == [3]
