# KPI Framework & Metric Ownership

**A production-grade system for defining, computing, and monitoring key business metrics.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Project Overview

This project implements a complete KPI framework designed for **Product Growth + Finance** roles at FAANG-level companies. It demonstrates:

- **Metric System Design:** North Star metric with decomposable driver tree
- **OOP Architecture:** Clean separation of concerns with testable components
- **Production Analytics:** Data quality checks, validation, and reproducible pipelines
- **Business Communication:** Executive-ready visualizations and reports

### North Star Metric

**VPAC (Value per Active Customer)** = Orders per Customer × Items per Order

This captures both **purchase frequency** (orders per customer) and **basket depth** (items per order), providing a comprehensive value proxy when direct revenue is unavailable.

> **Note on Revenue Proxy:** Instacart does not include prices, so this project uses a value proxy commonly used in product analytics when direct revenue is unavailable. VPAC is directionally correlated with revenue and enables all the same decomposition and attribution analysis.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- 10GB disk space for dataset
- Terminal access

### Installation

```bash
# Clone or navigate to project directory
cd kpi-metric-ownership

# Install dependencies
pip install -r requirements.txt
```

### Run the Analysis

```bash
# Launch Jupyter notebook
jupyter notebook notebooks/kpi_review.ipynb
```

**Then run all cells** (Cell → Run All) to execute the complete analysis pipeline.

---

## 📊 Key Results

### Overall KPIs (Instacart Dataset)

| Metric | Value | Unit | Driven By |
|--------|-------|------|-----------|
| **VPAC (North Star)** | **[Computed]** | items/customer | Purchase frequency × Basket depth |
| Active Customers | 206,209 | customers | Full dataset |
| Orders per Customer | 16.89 | orders/customer | Retention & lifecycle marketing |
| Items per Order | 10.09 | items/order | Merchandising & UX |
| Reorder Rate | 59% | rate | Product loyalty |

### Customer Segments

| Segment | Customer % | Order % | VPAC |
|---------|-----------|---------|------|
| Power Users (11+ orders) | 41% | 82% | **[Highest]** |
| Regular (5-10 orders) | 18% | 12% | Medium |
| Occasional (2-4 orders) | 21% | 5% | Low |
| One-time | 20% | 1% | Lowest |

**Key Insight:** Power users represent 41% of customers but drive 82% of total orders, making retention the critical growth lever.

---

## 🏗️ Project Structure

```
kpi-metric-ownership/
├── sql/                        # SQL queries for metric computation
│   ├── base_events.sql        # Order-level event extraction
│   ├── kpi_user_level.sql     # User-level aggregation
│   └── kpi_summary.sql        # Overall KPI summary
│
├── src/                        # Core Python modules
│   ├── io/
│   │   └── data_loader.py     # DuckDB data loading
│   ├── metrics/
│   │   ├── definitions.py     # MetricDefinition dataclass & registry
│   │   └── compute.py         # MetricEngine for KPI computation
│   ├── quality/
│   │   └── checks.py          # DataQualityChecker
│   ├── analysis/
│   │   └── decomposition.py   # VPACDecomposer & segmentation
│   ├── viz/
│   │   └── charts.py          # KPIVisualizer for all charts
│   └── reporting/
│       └── memo.py            # KPIReportBuilder
│
├── notebooks/
│   └── kpi_review.ipynb       # End-to-end analysis notebook
│
├── docs/
│   ├── metric_dictionary.md   # Complete metric definitions
│   └── kpi_playbook.md        # Operational guide
│
├── tests/
│   ├── test_metrics.py        # Metric computation tests
│   └── test_decomposition.py  # Decomposition validation tests
│
├── figures/                    # Generated visualizations
├── reports/                    # Generated business reviews
├── data/                       # Instacart CSV files
└── requirements.txt
```

---

## 🔍 Core Components

### 1. Metric Definition System

**File:** `src/metrics/definitions.py`

```python
from src.metrics.definitions import create_metric_registry, MetricDefinition

# Get all metrics
registry = create_metric_registry()

# Access North Star
vpac_metric = registry['vpac']
print(vpac_metric.formula)  # "Orders per Customer × Items per Order"
```

**Key Classes:**
- `MetricDefinition`: Dataclass with name, formula, computation function, owner, thresholds
- `MetricGrain`: Enum for aggregation level (user, order, overall)
- `MetricType`: Enum for metric classification (north_star, driver, guardrail)

### 2. Metric Computation Engine

**File:** `src/metrics/compute.py`

```python
from src.metrics.compute import MetricEngine

engine = MetricEngine(data_loader)
metrics_df = engine.compute_all_metrics()
north_star = engine.get_north_star()
```

**Features:**
- Computes all metrics from user-level data
- Returns North Star with component breakdown
- Validates against thresholds

### 3. VPAC Decomposition

**File:** `src/analysis/decomposition.py`

```python
from src.analysis.decomposition import VPACDecomposer

decomposer = VPACDecomposer()
result = decomposer.decompose_vpac_change(period1_metrics, period2_metrics)

# Automatically validates that components sum to total change
decomposer.validate_decomposition(result, tolerance=0.01)
```

**Decomposition Formula:**
```
Δ VPAC = (Δ Orders/Customer × avg Items/Order) 
       + (avg Orders/Customer × Δ Items/Order) 
       + Interaction
```

### 4. Data Quality Checks

**File:** `src/quality/checks.py`

```python
from src.quality.checks import DataQualityChecker

checker = DataQualityChecker(max_missing_rate=0.05)
results = checker.run_all_checks(df, "dataset_name")
print(checker.get_summary_report())
```

**Checks:**
- Null/missing rates per column
- Numeric range validation
- Monotonic relationship verification (e.g., orders >= customers)
- Outlier detection (z-score & IQR methods)

### 5. Visualizations

**File:** `src/viz/charts.py`

All visualizations use **matplotlib + seaborn** for clean, professional output.

**Available Charts:**
1. **Metric Tree:** North Star → Driver hierarchy with values
2. **Waterfall Chart:** Driver attribution for VPAC changes
3. **Segment Comparison:** VPAC, customer share, order share by segment
4. **KPI Health Grid:** Leadership table with all metrics
5. **Distribution Plots:** User-level metric distributions

---

## 📈 Visualizations

All generated figures are saved to `figures/`:

| File | Description |
|------|-------------|
| `01_metric_tree.png` | North Star hierarchy with components |
| `02_vpac_waterfall.png` | Driver attribution waterfall |
| `03_segment_comparison.png` | Customer segment analysis |
| `04_kpi_health_grid.png` | KPI summary table |
| `05_dist_*.png` | Metric distributions |

---

## 🧪 Testing

Run unit tests to validate metric computation and decomposition logic:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_metrics.py -v
pytest tests/test_decomposition.py -v
```

**Test Coverage:**
- ✅ Metric registry creation
- ✅ Metric computation accuracy
- ✅ VPAC decomposition validation (components sum to total)
- ✅ Single-driver attribution
- ✅ Data quality checks

---

## 📚 Documentation

### Metric Dictionary

**File:** `docs/metric_dictionary.md`

Complete specification for all metrics including:
- Formula & computation logic
- Grain & aggregation level
- Owner & review cadence
- Thresholds & validation rules
- Edge case handling

### KPI Playbook

**File:** `docs/kpi_playbook.md`

Operational guide for using metrics:
- How to read metric movements
- Diagnostic workflows (what to do when VPAC moves)
- Recommended actions by scenario
- Weekly review checklist
- Troubleshooting guide

---

## 🔧 Configuration

All parameters are centralized in `src/config.py` for reproducibility:

```python
# Time parameters
WEEK_START_DAY = 0  # Monday

# Metric thresholds
SMALL_BASKET_THRESHOLD = 3  # items
ANOMALY_Z_THRESHOLD = 2.5

# Visual styling
COLOR_POSITIVE = "#2ecc71"
COLOR_NEGATIVE = "#e74c3c"
FIGSIZE_STANDARD = (12, 6)
```

---

## 💼 Business Use Cases

### Weekly Business Review

```python
from src.reporting.memo import KPIReportBuilder

report_builder = KPIReportBuilder()
report = report_builder.create_weekly_business_review(
    metrics_df=metrics_df,
    north_star_info=north_star_info,
    decomposition=decomposition,
    key_insights=["insight 1", "insight 2"],
    save=True
)
```

**Output:** `reports/weekly_business_review.md`

### Customer Segmentation

```python
from src.analysis.decomposition import CustomerSegmentation

# Segment by order frequency
segments = CustomerSegmentation.segment_by_order_frequency(user_kpis)

# Segment by basket size
basket_segments = CustomerSegmentation.segment_by_basket_size(user_kpis)
```

---

## 🎓 Skills Demonstrated

This project showcases skills relevant to **Business/Data Analyst** and **Product Analyst** roles:

### Technical Skills
- ✅ **SQL:** Complex aggregations, CTEs, window functions
- ✅ **Python OOP:** Classes, dataclasses, type hints, modularity
- ✅ **Data Quality:** Validation, outlier detection, monotonic checks
- ✅ **Testing:** pytest, fixtures, parametrization
- ✅ **Visualization:** matplotlib, seaborn, professional charts

### Business Skills
- ✅ **Metric Design:** North Star selection, driver decomposition
- ✅ **Attribution Analysis:** Decomposing changes into root causes
- ✅ **Segmentation:** Customer cohorts, behavioral analysis
- ✅ **Communication:** Executive summaries, business reviews, playbooks

### Production Practices
- ✅ **Reproducibility:** Centralized config, documented parameters
- ✅ **Modularity:** Clean separation of data, logic, visualization
- ✅ **Documentation:** Inline comments, README, metric dictionary
- ✅ **Validation:** Automated checks, decomposition validation

---

## 🔬 Data Quality Checks

The framework implements comprehensive data quality validation:

| Check Type | Example | Threshold |
|------------|---------|-----------|
| Missing Values | Null rate per column | < 5% |
| Range Validation | Count metrics ≥ 0 | Hard constraint |
| Monotonic Relationships | Orders ≥ Customers | Hard constraint |
| Decomposition Sum | Components sum to total | < 1% error  |

**Example Output:**
```
✓ Passed: 24 checks
✗ Failed: 2 checks
  ⚠️  days_since_prior_order has 10.2% missing values (expected for first orders)
```

---

## 🚢 Deployment Considerations

While this is an analytics project (not a production app), it follows production best practices:

1. **Centralized Configuration:** All parameters in `config.py`
2. **Modular Design:** Easy to swap data sources or add new metrics
3. **Validation Layer:** Automated checks prevent bad data from propagating
4. **Documentation:** Self-documenting code + external docs
5. **Testing:** Unit tests ensure metric logic is correct

**To productionize:**
- Add time-series logic for true WoW comparisons
- Schedule notebook execution (Airflow, cron)
- Export to BI tool (Tableau, Looker)
- Add alerting on threshold breaches

---

## 📝 Reproducibility

To reproduce this analysis from scratch:

1. **Download Instacart Dataset:**
   - [Kaggle: Instacart Market Basket Analysis](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis)
   - Extract CSVs to `data/` directory

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Analysis:**
   ```bash
   jupyter notebook notebooks/kpi_review.ipynb
   ```

All parameters are configured in `src/config.py` and can be adjusted without code changes.

---

## 🤝 Metric Ownership

| Metric | Owner Team | Review Frequency |
|--------|-----------|------------------|
| VPAC (North Star) | Product Growth | Weekly |
| Active Customers | Marketing | Weekly |
| Orders per Customer | Retention PM | Weekly |
| Items per Order | Merchandising PM | Weekly |
| Reorder Rate | Retention PM | Bi-weekly |
| Small Basket Share | Product Quality | Weekly |

---

## 📖 References

- **Dataset:** [Instacart Market Basket Analysis (Kaggle)](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis)
- **Metric Decomposition:** Uses midpoint attribution for symmetric driver analysis
- **Visualization:** matplotlib + seaborn for professional, clean charts

---

## 🏆 Key Takeaways

1. **VPAC as North Star:** Combines frequency and basket depth without requiring revenue data
2. **Driver Attribution:** Decomposition shows which levers to pull (retention vs merchandising)
3. **Segment Insights:** Power users drive 82% of orders despite being 41% of customers
4. **Data Quality Matters:** Automated validation catches issues before they reach leadership
5. **Production-Ready:** Modular, tested, documented code ready for weekly business reviews

---

## 📧 Contact

**Author:** Heer Patel  
**Target Roles:** Business Analyst, Data Analyst, Product Analyst  
**Context:** Finance + Marketing background

---

*This project demonstrates production-level analytics skills for FAANG-level product and finance teams.*
