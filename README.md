# KPI Framework & Metric Ownership

Production KPI system with North Star decomposition, customer segmentation, and automated reporting.

**Target use case:** Weekly business review for product and growth teams  
**Dataset:** Instacart Market Basket (206K customers, 3.4M orders)  
**Tech stack:** Python, SQL (DuckDB), matplotlib/seaborn

---

## Quick Start

```bash
# Clone or download this repo
cd kpi-metric-ownership

# Install dependencies
pip install -r requirements.txt

# Download Instacart dataset from Kaggle
# https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis
# Extract CSVs to data/

# Run the analysis
python run_analysis.py

# Results saved to figures/ and reports/
```

**Runtime:** ~60 seconds on standard laptop

---

## Results Overview

### North Star: VPAC (Value per Active Customer)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **VPAC** | **162.02** items/customer | Customers purchase 16 orders × 10 items on average |
| Orders/Customer | 16.23 | Strong repeat purchase behavior |
| Items/Order | 9.98 | Healthy basket size |

### Customer Segmentation

| Segment | Customers | Orders | VPAC | Share of Orders |
|---------|-----------|--------|------|-----------------|
| Power Users (11+) | 41% | 82% | ~300 | Drives most volume |
| Regular (5-10) | 18% | 12% | ~110 | Growth opportunity |
| Occasional (2-4) | 21% | 5% | ~40 | Retention risk |
| One-time | 20% | 1% | ~10 | Failed onboarding |

**Key finding:** Top 41% of customers generate 82% of orders — retention is the critical lever.

### Health Check

| Guardrail Metric | Value | Status | Threshold |
|------------------|-------|--------|-----------|
| Reorder Rate | 44.4% | ✓ OK | >30% (loyalty indicator) |
| Small Basket Share | 18.5% | ✓ OK | <30% (quality bar) |
| Median Days Between Orders | 14.8 days | ✓ OK | 1-30 days |

All guardrails passing — no major quality or engagement concerns.

---

## What This Project Shows

**For Analytics Roles:**
- Metric system design (North Star → drivers → guardrails)
- Decomposition algebra (attributing changes to root causes)
- Threshold-based monitoring (not just tracking, but validating)
- Segment analysis with actionable results

**For Eng/Tech:**
- OOP Python (8 classes: MetricEngine, VPACDecomposer, DataQualityChecker, etc.)
- SQL proficiency (DuckDB with CTEs, window functions)
- Automated testing (pytest with edge cases)
- CLI design (args parsing, error handling, exit codes)

**For Business/Product:**
- Executive reporting (weekly review memos, visual storytelling)
- KPI ownership mapping (who reviews what, when)
- Operational playbook (what to do when metrics move)

---

## Project Structure

```
kpi-metric-ownership/
├── run_analysis.py          # Main entry point (CLI)
├── src/
│   ├── io/                  # DuckDB data loading
│   ├── metrics/             # MetricDefinition, MetricEngine
│   ├── quality/             # DataQualityChecker
│   ├── analysis/            # VPACDecomposer, CustomerSegmentation
│   ├── viz/                 # KPIVisualizer (5 charts)
│   └── reporting/           # KPIReportBuilder
├── sql/
│   ├── base_events.sql              # Order-level extraction
│   ├── kpi_user_aggregates.sql      # User-level KPIs
│   └── kpi_overall_summary.sql      # Company-wide summary
├── tests/
│   ├── test_metrics.py              # Metric computation tests
│   └── test_decomposition.py        # Driver attribution validation
├── docs/
│   ├── metric_dictionary.md         # Complete metric specs
│   └── kpi_playbook.md              # Operational guide
├── figures/                 # Generated visualizations
└── reports/                 # Weekly business reviews
```

---

## Core Components

### 1. Metric Definition System

Every metric has:
- Formula (algebraic)
- Computation function (Python)
- Owner (team responsible)
- Thresholds (for validation)
- Review cadence (weekly, bi-weekly)

Example:
```python
MetricDefinition(
    name='vpac',
    formula='Orders per Customer × Items per Order',
    owner='Product Growth',
    thresholds={'min': 0},
    review_cadence='Weekly'
)
```

See [`docs/metric_dictionary.md`](docs/metric_dictionary.md) for all 9 metrics.

### 2. Driver Decomposition

VPAC changes are automatically attributed to drivers:

```
Δ VPAC = (Δ Orders/Customer × avg Items/Order) 
       + (avg Orders/Customer × Δ Items/Order) 
       + Interaction term
```

The decomposition is validated (components must sum to total change within 1%).

### 3. Data Quality Framework

Automated checks:
- Null rates (flag if >5%)
- Range validation (counts ≥0, rates in [0,1])
- Monotonic relationships (orders ≥ customers)
- Outlier detection (z-score method)

Runs on every execution. Warnings don't block, errors do.

### 4. Visualizations

All charts use matplotlib/seaborn (professional, clean):

| File | Description |
|------|-------------|
| `01_metric_tree.png` | North Star → drivers hierarchy |
| `02_vpac_waterfall.png` | Driver attribution (what moved) |
| `03_segment_comparison.png` | Customer cohorts |
| `04_kpi_health_grid.png` | Status dashboard |
| `05_dist_*.png` | Metric distributions |

Figures saved to `figures/` automatically.

---

## CLI Options

```bash
python run_analysis.py              # Full analysis
python run_analysis.py --quiet      # Minimal output
python run_analysis.py --skip-viz   # Faster (no charts)
python run_analysis.py --help       # See all options
```

Exit codes:
- `0` = success
- `1` = general error
- `130` = user interrupt

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_metrics.py -v
```

Tests cover:
- Metric computation accuracy
- Decomposition validation (components sum correctly)
- Edge cases (empty data, single customer)
- Threshold logic

---

## Limitations & Design Decisions

### No Revenue Data

Instacart doesn't include prices. We use **VPAC** (items/customer) as a value proxy.

**Why this works:**
- Items ordered ≈ revenue (directionally correlated)
- Same decomposition logic applies
- Common pattern when direct revenue unavailable

**Interview talking point:**
> "When revenue isn't available, you proxy with units. VPAC captures frequency × depth, which are the levers product teams actually control."

### Snapshot vs Time Series

The dataset is a point-in-time snapshot, not a time series.

**Implications:**
- Can't compute true week-over-week trends
- Simulated comparisons (power users vs occasional) instead
- Status indicators use thresholds, not deltas

**If this were production:**
- Add timestamps to orders table
- Implement rolling window aggregations
- Enable trend detection and anomaly flagging

### Missing Values in `days_since_prior_order`

First orders have NULL values (6.3% of dataset) — this is expected.

Handled by:
- Validation flags it as a warning (not error)
- Computation uses `AVG()` which skips NULLs
- Documented in metric dictionary

---

## Documentation

| File | Purpose |
|------|---------|
| `README.md` (this file) | Project overview, quick start |
| `docs/metric_dictionary.md` | Complete metric specs (formulas, owners, thresholds) |
| `docs/kpi_playbook.md` | Operational guide (how to interpret movements, what actions to take) |

All docs follow single-source-of-truth principle — no duplicated definitions.

---

## Skills Demonstrated

**SQL:**
- Complex aggregations (user-level rollups)
- CTEs for readability
- Properly documented queries (inputs, outputs, grain)

**Python OOP:**
- Clean class design (8 classes with clear responsibilities)
- Type hints throughout
- Comprehensive docstrings

**Data Engineering:**
- DuckDB for local analytics (BigQuery-compatible syntax)
- Automated validation pipelines
- Exit codes and error handling

**Business Communication:**
- Metric ownership matrix
- Executive summaries (weekly review memos)
- Playbooks for non-technical stakeholders

**Production Practices:**
- Centralized config (no magic numbers)
- Modular architecture (easy to extend)
- Automated testing
- CLI interface with proper arg parsing

---

## Next Steps (If Extending)

1. **Add time-series support** → compute real WoW/MoM trends
2. **Implement alerting** → email/Slack when thresholds breach
3. **Export to BI tool** → Tableau/Looker dashboard
4. **Add category decomposition** → which departments drive VPAC
5. **Cohort retention analysis** → track how segments evolve

---

## References

- **Dataset:** [Instacart Market Basket Analysis (Kaggle)](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis)
- **Decomposition method:** Midpoint attribution (symmetric driver analysis)
- **Visualization:** matplotlib 3.7+ / seaborn 0.12+

---

## Contact

**Author:** Heer Patel  
**Target roles:** Product Analyst, Business Analyst, Data Analyst  
**Portfolio context:** Finance major + Marketing minor at Texas A&M

Questions or feedback? Open an issue or reach out directly.

---

*Last updated: 2026-01-20*
