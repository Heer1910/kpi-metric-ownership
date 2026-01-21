# KPI Framework & Metric Ownership

Production KPI system for growth analytics. Tracks North Star (VPAC) with driver decomposition, customer segmentation, and automated reporting.

**Business Context:** Grocery marketplace (Instacart-like) with 206K customers and 3.4M orders. No revenue data available, so VPAC proxies value through order frequency × basket size.

**North Star:** VPAC = 162 items/customer (Orders per Customer × Items per Order)

**Key Findings:**
- Power users (11+ orders) are 41% of customers but drive **82% of orders** — retention is the primary lever
- Reorder rate at 44% indicates strong product-market fit
- Small basket share at 18% confirms acquisition quality is healthy

**Decision:** Focus retention initiatives on moving occasional users (2-4 orders) to power user status. Every 1-point increase in orders/customer drives ~10 points of VPAC.

---

## Quick Start

```bash
# Setup
make setup

# Run analysis (generates all KPIs and visuals)
make run
```

**Runtime:** ~60 seconds

---

## Key Artifacts

**Executive Dashboard:**  
[`figures/00_executive_dashboard.png`](figures/00_executive_dashboard.png) - 2x2 view with metric tree, waterfall, segments, KPI summary

**Business Review:**  
[`reports/weekly_business_review.md`](reports/weekly_business_review.md) - Automated weekly memo with insights

**Visualizations:**
- [`01_metric_tree.png`](figures/01_metric_tree.png) - North Star breakdown
- [`02_vpac_waterfall.png`](figures/02_vpac_waterfall.png) - Driver attribution
- [`03_segment_comparison.png`](figures/03_segment_comparison.png) - Customer cohorts
- [`04_kpi_health_grid.png`](figures/04_kpi_health_grid.png) - Status dashboard

**Documentation:**
- [`docs/metric_dictionary.md`](docs/metric_dictionary.md) - Complete metric specs
- [`docs/kpi_playbook.md`](docs/kpi_playbook.md) - How to use metrics operationally
- [`docs/architecture.md`](docs/architecture.md) - Technical deep dive

---

## Results Summary

| Metric | Value | Status | Insight |
|--------|-------|--------|---------|
| **VPAC** | **162.02** | ✓ | Driven by frequency (16 orders/customer) |
| Active Customers | 206,209 | ✓ | Full dataset |
| Orders/Customer | 16.23 | ✓ | **Primary driver** of VPAC |
| Items/Order | 9.98 | ✓ | Secondary lever |
| Reorder Rate | 44.4% | ✓ | Strong loyalty signal |
| Small Basket Share | 18.5% | ✓ | Below 30% threshold |

**Segment Breakdown:**

| Segment | Customers | Share of Orders | VPAC | Action |
|---------|-----------|-----------------|------|--------|
| Power Users (11+) | 41% | 82% | ~300 | Retain at all costs |
| Regular (5-10) | 18% | 12% | ~110 | Upsell to power |
| Occasional (2-4) | 21% | 5% | ~40 | **Retention opportunity** |
| One-time | 20% | 1% | ~10 | Fix onboarding |

---

## What This Shows

**For Analytics Roles:**
- Metric system design (North Star → drivers → guardrails)
- Driver decomposition with validated attribution
- Threshold-based monitoring (not just tracking)

**For Tech Roles:**
- Production Python (OOP, type hints, error handling)
- SQL proficiency (DuckDB, CTEs, aggregations)
- CLI design with proper arg parsing

**For Product/Business:**
- Weekly business review automation
- KPI ownership mapping
- Operational playbook for metric movements

---

## Project Structure

```
kpi-metric-ownership/
├── run_analysis.py          # Main entry point
├── Makefile                 # Simple commands (make setup, make run)
├── src/                     # Core modules (8 Python files)
│   ├── metrics/            # MetricEngine, definitions
│   ├── analysis/           # VPACDecomposer, segmentation
│   ├── viz/                # Charts + executive dashboard
│   └── reporting/          # Weekly review generator
├── sql/                     # DuckDB queries (3 files)
├── tests/                   # Unit tests (20 passing)
├── docs/                    # Metric dictionary, playbook, architecture
├── figures/                 # Generated visuals
└── reports/                 # Generated business reviews
```

See [`docs/architecture.md`](docs/architecture.md) for detailed component documentation.

---

## Testing

```bash
make test

# 20 tests passing:
# - Metric computation accuracy
# - Decomposition validation (components sum to total)
# - Edge cases (single customer, extreme values, NULL handling)
# - Threshold logic
```

---

## CLI Options

```bash
python run_analysis.py              # Full analysis
python run_analysis.py --quiet      # Minimal output
python run_analysis.py --skip-viz   # Skip charts (faster)
python run_analysis.py --help       # All options
```

---

## Design Decisions

**Why VPAC (not revenue)?**  
Instacart dataset has no prices. VPAC = items/customer is directionally correlated with revenue and uses metrics product teams actually control (frequency × depth).

**Why snapshot (not time-series)?**  
Dataset is point-in-time. For WoW trends, we simulate by comparing customer cohorts (power users vs occasional). In production, this would use real time windows.

**Why DuckDB (not BigQuery)?**  
Local execution, no cloud credentials needed. Uses BigQuery-compatible SQL syntax for easy migration.

---

## Tech Stack

- **Python 3.9+** - OOP design, type hints, dataclasses
- **DuckDB** - In-memory SQL analytics (BigQuery syntax)
- **matplotlib/seaborn** - Professional visualizations
- **pytest** - Test coverage with edge cases

**Dependencies:** `pandas`, `numpy`, `matplotlib`, `seaborn`, `duckdb`, `pytest`

---

## Limitations

- No revenue data → VPAC is a proxy (directionally correlated)
- Snapshot dataset → can't compute true WoW trends
- ~6% NULL values in `days_since_prior_order` (expected for first orders)

All limitations documented in metric dictionary with business justification.

---

## Contact

**Author:** Heer Patel  
**Target Roles:** Product Analyst, Business Analyst, Data Analyst  
**Background:** Finance + Marketing at Texas A&M

**Repo:** https://github.com/Heer1910/kpi-metric-ownership

---

*Last updated: 2026-01-20*
