# Power BI Dashboard — Step-by-Step Build Guide

**Data source:** `data/powerbi/powerbi_export.csv`
**Dashboard:** 5 pages covering Executive KPIs, Products, Customer Segmentation, Cohort Retention, and Operations.

---

## Prerequisites

1. Install **Power BI Desktop** (free, Windows only) from [powerbi.microsoft.com](https://powerbi.microsoft.com/downloads/)
2. Run all 5 Jupyter notebooks in order to generate `powerbi_export.csv`
3. Confirm the CSV has 100,000+ rows before importing

---

## Part 1: Load Data into Power BI

### 1.1 Import the CSV

1. Open Power BI Desktop → **Get data** → **Text/CSV**
2. Navigate to `data/powerbi/powerbi_export.csv` → **Load**
3. Rename the table to `SalesData` (right-click the table in the Fields pane → Rename)

### 1.2 Set Data Types in Power Query (Transform Data)

Click **Transform data** and set these column types:

| Column | Type |
|---|---|
| `order_date` | Date/Time |
| `order_year` | Whole Number |
| `order_month` | Whole Number |
| `order_quarter` | Whole Number |
| `price` | Decimal Number |
| `freight_value` | Decimal Number |
| `total_item_value` | Decimal Number |
| `payment_value` | Decimal Number |
| `review_score` | Decimal Number |
| `delivery_days` | Whole Number |
| `is_high_value_customer` | Whole Number |

Click **Close & Apply**.

### 1.3 Create a Date Table (for YoY comparisons)

In the **Modeling** tab → **New table**:

```dax
DateTable = 
CALENDAR(
    DATE(2016, 1, 1),
    DATE(2018, 12, 31)
)
```

Add columns to the Date table:
```dax
Year = YEAR(DateTable[Date])
Month = MONTH(DateTable[Date])
Quarter = QUARTER(DateTable[Date])
MonthName = FORMAT(DateTable[Date], "MMM YYYY")
```

Create a relationship: `SalesData[order_date]` → `DateTable[Date]`

---

## Part 2: DAX Measures

Create these measures in a **New measure group** called `_Measures`. Select any table, click **New measure**.

### Core Revenue Measures

```dax
Total Revenue = SUM(SalesData[total_item_value])
```

```dax
Total Orders = DISTINCTCOUNT(SalesData[order_id])
```

```dax
Total Customers = DISTINCTCOUNT(SalesData[customer_id])
```

```dax
Avg Order Value = 
DIVIDE([Total Revenue], [Total Orders])
```

```dax
Avg Review Score = AVERAGE(SalesData[review_score])
```

```dax
Avg Delivery Days = AVERAGE(SalesData[delivery_days])
```

### Year-over-Year Measures

```dax
CY Revenue = 
CALCULATE(
    [Total Revenue],
    FILTER(
        ALL(DateTable),
        DateTable[Year] = MAX(DateTable[Year])
    )
)
```

```dax
PY Revenue = 
CALCULATE(
    [Total Revenue],
    FILTER(
        ALL(DateTable),
        DateTable[Year] = MAX(DateTable[Year]) - 1
    )
)
```

```dax
YoY Growth % = 
DIVIDE([CY Revenue] - [PY Revenue], [PY Revenue], 0)
```

```dax
YoY Growth % Label = 
FORMAT([YoY Growth %], "+0.0%;-0.0%;0.0%")
```

### Customer Segmentation Measures

```dax
High Value Revenue = 
CALCULATE(
    [Total Revenue],
    SalesData[is_high_value_customer] = 1
)
```

```dax
High Value Revenue % = 
DIVIDE([High Value Revenue], [Total Revenue], 0)
```

```dax
High Value Customers = 
CALCULATE(
    DISTINCTCOUNT(SalesData[customer_id]),
    SalesData[is_high_value_customer] = 1
)
```

### Logistics Measures

```dax
On Time Delivery % = 
DIVIDE(
    CALCULATE(COUNTROWS(SalesData), SalesData[delivery_days] <= 10),
    COUNTROWS(SalesData),
    0
)
```

---

## Part 3: Page-by-Page Build Instructions

---

### Page 1: Executive KPI Overview

**Rename page:** Right-click tab → Rename → "Executive Overview"

**Background:** Set to a dark or light theme under **View** → **Themes**.

#### Visual 1: KPI Cards (top row)

Insert 5 **Card** visuals in a row:
1. Field: `[Total Revenue]` | Title: "Total Revenue (BRL)"
2. Field: `[Total Orders]` | Title: "Total Orders"
3. Field: `[Avg Order Value]` | Title: "Avg Order Value"
4. Field: `[Total Customers]` | Title: "Total Customers"
5. Field: `[YoY Growth %]` | Title: "YoY Revenue Growth" | Format: percentage

**Conditional formatting on YoY Growth %:** Values > 0 → Green, < 0 → Red.

#### Visual 2: Monthly Revenue Trend (Line Chart)

- Visualization: **Line chart**
- X-axis: `DateTable[MonthName]` (sort by Month Number)
- Y-axis: `[Total Revenue]`
- Secondary Y-axis: `[Total Orders]`
- Legend: None (or `DateTable[Year]` for YoY overlay)
- Title: "Monthly Revenue Trend"

**To add YoY comparison lines:**
- Click the visual → **Analytics** pane → Add **Constant line** or use `DateTable[Year]` as a slicer.

#### Visual 3: Revenue by State (Filled Map)

- Visualization: **Filled Map**
- Location: `SalesData[customer_state]`
- Color saturation: `[Total Revenue]`
- Tooltip: `[Total Revenue]`, `[Total Orders]`
- Title: "Revenue by Brazilian State"

> Note: Power BI may need to recognize Brazilian state codes. If the map doesn't populate correctly, go to **Column tools** → **Data category** → **State or Province** for the `customer_state` column.

#### Visual 4: Revenue by Region (Bar Chart)

- Visualization: **Clustered bar chart**
- Y-axis: `SalesData[customer_region]`
- X-axis: `[Total Revenue]`
- Title: "Revenue by Region"

#### Slicers (right panel)

Add two **Slicer** visuals:
1. `DateTable[Year]` | Style: Dropdown
2. `SalesData[customer_region]` | Style: List

---

### Page 2: Product & Category Analytics

**Rename page:** "Product Analytics"

#### Visual 1: Top 20 Categories by Revenue (Horizontal Bar)

- Visualization: **Clustered bar chart**
- Y-axis: `SalesData[product_category_english]`
- X-axis: `[Total Revenue]`
- Filter (Visual level): Top N → Top 20 by `[Total Revenue]`
- Sort: Descending by revenue
- Title: "Top 20 Categories by Revenue"

**Conditional formatting:** Data bars on X-axis values (blue gradient).

#### Visual 2: Revenue Distribution Treemap

- Visualization: **Treemap**
- Category: `SalesData[product_category_english]`
- Values: `[Total Revenue]`
- Title: "Revenue by Category (Treemap)"

#### Visual 3: Avg Price vs Quantity Sold (Scatter Plot)

- Visualization: **Scatter chart**
- X-axis: `AVERAGE(SalesData[price])` (create measure: `Avg Item Price = AVERAGE(SalesData[price])`)
- Y-axis: Create measure: `Items Sold = COUNTROWS(SalesData)`
- Details: `SalesData[product_category_english]`
- Size: `[Total Revenue]`
- Title: "Category: Avg Price vs Volume"

#### Visual 4: Revenue Trend by Top 5 Categories (Line Chart)

- Visualization: **Line chart**
- X-axis: `DateTable[MonthName]`
- Y-axis: `[Total Revenue]`
- Legend: `SalesData[product_category_english]`
- Filter: Top 5 categories by revenue
- Title: "Monthly Revenue — Top 5 Categories"

#### Drill-down Hierarchy

In the Y-axis field of bar charts, create a hierarchy:
`customer_region` → `customer_state` → `customer_city`

Enable drill-down by clicking the fork/arrow icon on the visual.

#### Slicers

1. `DateTable[Year]` | Dropdown
2. `SalesData[customer_region]` | List

---

### Page 3: Customer Segmentation (RFM)

**Rename page:** "Customer Segments"

#### Visual 1: Customer Count per RFM Segment (Bar Chart)

- Visualization: **Clustered bar chart**
- X-axis: `SalesData[rfm_segment]`
- Y-axis: `[Total Customers]`
- Title: "Customers by RFM Segment"

**Conditional formatting:** Add data labels. Color each bar by segment using a fixed color scheme:
- Champions → Dark green
- Loyal Customers → Light green
- At Risk → Orange
- Hibernating → Red

#### Visual 2: Revenue by Segment (Donut Chart)

- Visualization: **Donut chart**
- Legend: `SalesData[rfm_segment]`
- Values: `[Total Revenue]`
- Title: "Revenue Share by RFM Segment"

#### Visual 3: Segment KPI Cards

Create 3 KPI cards:
1. `[High Value Customers]` | "High-Value Customers (Top 20%)"
2. `[High Value Revenue]` | "Revenue from Top 20%"
3. `[High Value Revenue %]` | "% Revenue from Top 20%" | Format: Percentage

#### Visual 4: Top 50 High-Value Customers (Table)

- Visualization: **Table**
- Columns: `customer_id`, `rfm_segment`, `[Total Revenue]`, `delivery_days`, `review_score`
- Filter (Visual level): `SalesData[is_high_value_customer]` = 1
- Sort: Descending by `[Total Revenue]`
- Enable conditional formatting: Green/Red on `review_score`

#### Visual 5: R vs M Scatter (Recency vs Spend)

Create two measures:
```dax
Avg Recency Days = AVERAGE(SalesData[delivery_days])
```

- Visualization: **Scatter chart**
- X-axis: `delivery_days` average
- Y-axis: `[Total Revenue]`
- Details: `SalesData[rfm_segment]`
- Color: by `rfm_segment`

#### Slicers

1. `SalesData[rfm_segment]` | List (multi-select)
2. `SalesData[customer_state]` | Dropdown

---

### Page 4: Cohort & Retention Analysis

**Rename page:** "Cohort Analysis"

#### Visual 1: Cohort Retention Matrix (Matrix Visual)

- Visualization: **Matrix**
- Rows: `SalesData[customer_cohort_month]`
- Columns: Need a period number column — add to the CSV or create a calculated column

**To create a period column:**
In Power BI → **New column** (on SalesData):
```dax
Order Period = FORMAT(SalesData[order_date], "YYYY-MM")
```

Then create a calculated table for the retention matrix (advanced):
```dax
CohortMatrix = 
SUMMARIZE(
    SalesData,
    SalesData[customer_cohort_month],
    SalesData[Order Period],
    "CustomerCount", DISTINCTCOUNT(SalesData[customer_id])
)
```

- Rows: `CohortMatrix[customer_cohort_month]`
- Columns: `CohortMatrix[Order Period]`
- Values: `CohortMatrix[CustomerCount]`

**Conditional formatting:** Gradient from white (0) to dark green (100%).

#### Visual 2: Retention KPI Cards

Create 3 Card visuals from your notebook output:

After running notebook 03, open `reports/kpi_summary.json` to get the values, then hard-code them as measures:

```dax
Avg 1Mo Retention = 0.XX   -- replace with actual value from kpi_summary.json
Avg 3Mo Retention = 0.XX
Avg 6Mo Retention = 0.XX
```

Display as:
1. "1-Month Retention" | Format: Percentage
2. "3-Month Retention" | Format: Percentage
3. "6-Month Retention" | Format: Percentage

#### Visual 3: Orders by Cohort Month (Stacked Bar)

- Visualization: **Stacked bar chart**
- X-axis: `SalesData[customer_cohort_month]`
- Y-axis: `[Total Orders]`
- Title: "Orders by Customer Cohort Month"

#### Visual 4: Cohort Size Over Time (Line)

- Visualization: **Line chart**
- X-axis: `SalesData[customer_cohort_month]`
- Y-axis: `[Total Customers]`
- Title: "New Customer Cohort Size by Month"

---

### Page 5: Operations & Logistics

**Rename page:** "Operations"

#### Visual 1: Delivery Time Distribution (Histogram)

Power BI doesn't have a native histogram, but you can simulate one:

1. Create a **Clustered column chart**
2. X-axis: Create a calculated column for delivery buckets:

```dax
Delivery Bucket = 
SWITCH(
    TRUE(),
    SalesData[delivery_days] <= 3,  "0–3 days",
    SalesData[delivery_days] <= 7,  "4–7 days",
    SalesData[delivery_days] <= 14, "8–14 days",
    SalesData[delivery_days] <= 21, "15–21 days",
    SalesData[delivery_days] <= 30, "22–30 days",
    "30+ days"
)
```

3. Y-axis: `COUNTROWS(SalesData)`
4. Sort X-axis manually by bucket order

#### Visual 2: Avg Review Score by Category (Bar Chart)

- Visualization: **Clustered bar chart**
- Y-axis: `SalesData[product_category_english]`
- X-axis: `[Avg Review Score]`
- Filter: Top 20 categories by order count
- Conditional formatting: Green (≥4.0) to Red (≤3.0)
- Title: "Avg Review Score by Category"

#### Visual 3: Avg Delivery Days by State (Filled Map)

- Visualization: **Filled Map**
- Location: `SalesData[customer_state]`
- Color saturation: `[Avg Delivery Days]`
- Color scale: Green (fast) → Red (slow)
- Title: "Avg Delivery Time by State"

#### Visual 4: Payment Method Split (Donut)

- Visualization: **Donut chart**
- Legend: `SalesData[payment_type]`
- Values: `COUNTROWS(SalesData)` — or `[Total Revenue]`
- Title: "Revenue by Payment Type"

#### Visual 5: Delivery Days vs Review Score (Scatter)

- Visualization: **Scatter chart**
- X-axis: `[Avg Delivery Days]`
- Y-axis: `[Avg Review Score]`
- Details: `SalesData[product_category_english]`
- Title: "Delivery Speed vs Customer Satisfaction"

#### Slicers

1. `DateTable[Year]` | Dropdown
2. `SalesData[customer_region]` | List
3. `SalesData[order_status]` | Dropdown

---

## Part 4: Global Settings

### Theme & Formatting

1. **View → Themes → Browse for themes** — import a JSON theme or use a built-in
2. Recommended: **Executive** or **Innovation** theme
3. Set font to **Segoe UI** throughout
4. Use consistent color palette:
   - Primary: `#0078D4` (Microsoft blue)
   - Positive: `#107C10` (green)
   - Negative: `#D83B01` (red)
   - Neutral: `#605E5C` (gray)

### Cross-Page Slicers (Sync)

To sync the Year slicer across all pages:
1. Select the slicer → **View → Sync slicers**
2. Enable sync for all 5 pages

### Drill-through Setup

On Page 2 (Products):
1. Add a **Drill-through** field: `SalesData[product_category_english]`
2. This lets you right-click any category on Page 1 and drill through to Page 2 filtered for that category

### Bookmarks for Executive Summary

1. **View → Bookmarks**
2. Create bookmarks for:
   - "All Years"
   - "2017 Only"
   - "2018 Only"
3. Add **Buttons** linked to each bookmark for presentation mode

---

## Part 5: Publishing

### Save & Export
1. **File → Save** as `SalesAnalytics.pbix`
2. **File → Export → Export to PDF** for a static report version
3. **Publish** to Power BI Service (requires a work/school Microsoft account) for online sharing

### Schedule Refresh (Power BI Service)
After publishing:
1. Open the dataset in Power BI Service
2. **Settings → Scheduled refresh** → Add daily refresh
3. This automates the weekly reporting described in the resume

---

## DAX Measure Quick Reference

| Measure | Formula |
|---|---|
| Total Revenue | `SUM(SalesData[total_item_value])` |
| Total Orders | `DISTINCTCOUNT(SalesData[order_id])` |
| Avg Order Value | `DIVIDE([Total Revenue], [Total Orders])` |
| YoY Growth % | `DIVIDE([CY Revenue] - [PY Revenue], [PY Revenue], 0)` |
| High Value Revenue % | `DIVIDE([High Value Revenue], [Total Revenue], 0)` |
| On Time Delivery % | `DIVIDE(CALCULATE(COUNTROWS(SalesData), SalesData[delivery_days]<=10), COUNTROWS(SalesData), 0)` |

---

## Screenshots Placeholder

> Add screenshots of your completed dashboard here. Suggested structure:

```
powerbi/
├── screenshots/
│   ├── page1_executive_overview.png
│   ├── page2_product_analytics.png
│   ├── page3_customer_segments.png
│   ├── page4_cohort_analysis.png
│   └── page5_operations.png
```

---

*Built for the Olist Brazilian E-Commerce dataset. Author: Keshav Kashyap, IIIT Kota.*
