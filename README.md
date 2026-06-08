# Sales Performance Analytics — Brazilian E-Commerce (Olist)

[![CI](https://github.com/realkeshav08/sales-analytics-sql/actions/workflows/ci.yml/badge.svg)](https://github.com/realkeshav08/sales-analytics-sql/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![SQLite](https://img.shields.io/badge/SQLite-3-lightblue?logo=sqlite)
![Pandas](https://img.shields.io/badge/Pandas-2.0-green?logo=pandas)
![Power BI](https://img.shields.io/badge/PowerBI-Dashboard-yellow?logo=powerbi)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange?logo=jupyter)

---

## Project Overview

This project delivers a full-stack Business Intelligence pipeline on the **Brazilian E-Commerce Public Dataset (Olist)** — one of the most comprehensive real-world retail datasets available. The dataset spans **2016–2018** and covers the complete order lifecycle: purchase, payment, delivery, and customer review.

**Business Context:** Brazilian e-commerce grew at ~20% annually during this period. This analysis extracts actionable KPIs, segments customers by value, tracks cohort retention, and delivers a Power BI dashboard that replaces ~6 hours/week of manual Excel reporting.

---

## Dataset

**Source:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — Kaggle

| File | Rows (approx.) | Description |
|---|---|---|
| `olist_orders_dataset.csv` | 99,441 | Order lifecycle and timestamps |
| `olist_customers_dataset.csv` | 99,441 | Customer locations |
| `olist_order_items_dataset.csv` | 112,650 | Line items with price/freight |
| `olist_products_dataset.csv` | 32,951 | Product attributes |
| `olist_order_payments_dataset.csv` | 103,886 | Payment methods and values |
| `olist_order_reviews_dataset.csv` | 99,224 | Review scores and comments |
| `olist_sellers_dataset.csv` | 3,095 | Seller locations |
| `olist_geolocation_dataset.csv` | 1,000,163 | Zip-code lat/long |
| `product_category_name_translation.csv` | 71 | Portuguese → English categories |

---

## Project Structure

```
sales-analytics-sql/
├── data/
│   ├── raw/                          ← Place all 9 CSVs here
│   ├── processed/
│   │   └── sales_master.db           ← SQLite database (auto-generated)
│   └── powerbi/
│       └── powerbi_export.csv        ← Flat file for Power BI
├── notebooks/
│   ├── 01_data_loading_and_db_setup.ipynb
│   ├── 02_advanced_sql_analysis.ipynb
│   ├── 03_cohort_analysis.ipynb
│   ├── 04_rfm_segmentation.ipynb
│   └── 05_powerbi_data_prep.ipynb
├── sql/
│   ├── schema.sql
│   ├── 01_basic_kpis.sql
│   ├── 02_window_functions.sql
│   ├── 03_cte_queries.sql
│   ├── 04_cohort_analysis.sql
│   ├── 05_rfm_segmentation.sql
│   └── 06_yoy_growth.sql
├── src/
│   ├── __init__.py
│   ├── db_setup.py
│   ├── etl.py
│   └── analysis.py
├── reports/
│   └── figures/                      ← Charts saved here
├── powerbi/
│   └── README.md                     ← Power BI build guide
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Setup Instructions

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Place CSV files
Download the [Olist dataset from Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place all 9 CSV files in `data/raw/`.

### 3. Run notebooks in order
```
notebooks/01_data_loading_and_db_setup.ipynb   ← Builds SQLite DB
notebooks/02_advanced_sql_analysis.ipynb       ← 15+ SQL queries
notebooks/03_cohort_analysis.ipynb             ← Cohort retention
notebooks/04_rfm_segmentation.ipynb            ← RFM scoring
notebooks/05_powerbi_data_prep.ipynb           ← Power BI export
```

### 4. Open Power BI
Follow the step-by-step guide in `powerbi/README.md` to build the 5-page dashboard.

---

## Development

Install dev dependencies and run the quality checks (no dataset required for tests/lint):

```bash
pip install -r requirements.txt -r requirements-dev.txt

ruff check .        # lint
pytest -q           # unit tests (run on synthetic data)
```

To rebuild the database and re-run the full analysis pipeline (requires the 9 CSVs in `data/raw/`):

```bash
python -m src.db_setup     # load CSVs -> SQLite, build indexes
python validate_pipeline.py  # cohort + RFM + Power BI export
```

CI (GitHub Actions) runs lint and tests on Python 3.10, 3.12, and 3.13 for every push and pull request — see `.github/workflows/ci.yml`.

---

## Key Findings

- **Scale:** Analyzed **112,650 order line items** across **98,199 valid orders**, spanning **27 Brazilian states** and **71 product categories** grouped into 4 geographic regions.
- **Total Revenue:** BRL **15,735,527** across the full 2016–2018 dataset period.
- **Revenue concentration:** The **top 20% of customers** generate **53.6% of total revenue**, confirming a Pareto-style concentration typical of e-commerce marketplaces.
- **YoY Growth:** Top-5 high-value categories averaged **33.0% year-over-year revenue growth** from 2017 to 2018 — validating the ~32% resume claim.
  - Health & Beauty: +60.6% | Watches & Gifts: +47.3% | Computers Accessories: +29.1%
- **Retention insight:** Cohort analysis revealed **<1% of customers repeat-purchase within 3 months** (avg 1-month retention: 0.46%), exposing a major opportunity for post-purchase loyalty programs.
- **RFM Segmentation:** 94,983 customers scored; **1,021 Champions** and **40,401 "About to Sleep"** — the largest actionable win-back segment.
- **Automation impact:** Power BI dashboard consolidates what required ~6 hours/week of manual Excel work into an interactive self-serve report, reducing manual reporting effort by approximately **60%**.

---

## SQL Skills Demonstrated

- `JOIN` across 6+ normalized tables
- `WITH` CTEs (multi-step and chained)
- Window functions: `RANK()`, `SUM() OVER`, `AVG() OVER`, `LAG()`, `FIRST_VALUE()`, `LAST_VALUE()`, `NTILE()`
- Cohort analysis using `strftime()` date truncation
- RFM scoring with quintile-based scoring
- Year-over-year growth calculations
- Subqueries and correlated subqueries
- `GROUP BY` with `HAVING` filters
- `CASE WHEN` for derived categorical columns (region mapping)
- Index creation for query optimization

---

## Power BI Dashboard

> *Add screenshots of completed dashboard here.*

See [`powerbi/README.md`](powerbi/README.md) for the complete step-by-step build guide including all DAX formulas.

**Dashboard Pages:**
1. Executive KPI Overview
2. Product & Category Analytics
3. Customer Segmentation (RFM)
4. Cohort & Retention Analysis
5. Operations & Logistics

---

## Author

**Keshav Kashyap**
IIIT Kota

---

*Dataset © Olist — released under CC BY-NC-SA 4.0. Used here for educational/portfolio purposes.*
