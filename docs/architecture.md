# Architecture Documentation

Technical deep dive into the KPI Framework system design.

---

## System Overview

The KPI Framework is a production analytics system that:
1. Loads grocery marketplace data (Instacart) into DuckDB
2. Computes 9 metrics including North Star (VPAC)
3. Performs driver decomposition to attribute changes
4. Generates executive visualizations and reports
5. Validates data quality and metric logic

---

## Core Components

### 1. Metric Definition System

**File:** `src/metrics/definitions.py`

Every metric is defined as a `MetricDefinition` dataclass:

```python
@dataclass
class MetricDefinition:
    name: str                    # Internal identifier
    display_name: str            # Human-readable name
    grain: MetricGrain          # USER | ORDER | OVERALL
    metric_type: MetricType     # NORTH_STAR | DRIVER | GUARDRAIL
    formula: str                 # Mathematical definition
    computation_fn: Callable     # Python function to compute
    unit: str                    # customers, orders, rate, etc.
    owner: str                   # Responsible team
    description: str             # What it measures
    thresholds: Dict            # min/max for validation
    dependencies: List[str]      # Other metrics this depends on
```

**Registry Pattern:**  
`create_metric_registry()` returns a dict of all metrics. This is the single source of truth referenced by:
- MetricEngine (computation)
- Visualizations (display)
- Tests (validation)
- Documentation (metric dictionary)

### 2. Metric Computation Engine

**File:** `src/metrics/compute.py`

```python
class MetricEngine:
    def compute_all_metrics() -> pd.DataFrame
    def compute_metric(name: str) -> Any
    def compare_periods(p1, p2) -> pd.DataFrame
    def get_north_star() -> Dict
```

**Data Flow:**
1. SQL queries load user-level KPIs (`_get_user_kpis()`)
2. Each metric's `computation_fn` runs on that data
3. Results validated against thresholds
4. Returned as structured DataFrame

**Period Comparison:**  
The `compare_periods()` method enables WoW/MoM analysis by computing metrics on two datasets and returning absolute + percent changes.

### 3. VPAC Decomposition

**File:** `src/analysis/decomposition.py`

**Formula:**
```
Δ VPAC = (Δ Orders/Customer × avg Items/Order) 
       + (avg Orders/Customer × Δ Items/Order) 
       + Interaction
```

**Implementation:**

```python
class VPACDecomposer:
    def decompose_vpac_change(period1, period2) -> DecompositionResult
    def validate_decomposition(result) -> bool
    def prepare_waterfall_data(result) -> pd.DataFrame
```

**Validation:**  
Sum of driver contributions must equal total VPAC change within 1% tolerance. This catches computation errors.

**Use Case:**  
When VPAC moves, decomposition tells you whether it's frequency (orders/customer) or depth (items/order) driving the change. This determines which team (Retention vs Merchandising) should act.

### 4. Data Quality Framework

**File:** `src/quality/checks.py`

```python
class DataQualityChecker:
    def check_null_rates(df, col) -> bool
    def check_row_count(df, min, max) -> bool
    def check_numeric_range(df, col, min, max) -> bool
    def check_monotonic(df, col1, col2) -> bool
    def detect_outliers(df, col, method='zscore') -> List
    def run_all_checks(df) -> List[CheckResult]
```

**Check Types:**
- **Null rates:** Flag columns with >5% missing values
- **Range validation:** Counts ≥0, rates in [0,1]
- **Monotonic relationships:** orders ≥ customers (logical constraint)
- **Outlier detection:** z-score and IQR methods

**Result Classification:**
- **ERROR:** Blocks analysis (e.g., all values NULL)
- **WARNING:** Logged but doesn't block (e.g., first orders have NULL days_since_prior)

### 5. Visualization System

**Files:**
- `src/viz/charts.py` - Individual charts
- `src/viz/dashboard.py` - Executive 2x2 panel

**Charts:**

| Chart | Purpose | Technical Note |
|-------|---------|----------------|
| Metric Tree | Shows North Star → drivers | Uses matplotlib FancyBoxPatch for visual hierarchy |
| Waterfall | Driver attribution | Stacked bars with cumulative positioning |
| Segment Comparison | VPAC by customer cohort | Horizontal bars sorted by value |
| Health Grid | KPI status table | Color-coded cells (green=OK, red=WARNING) |
| Distributions | User-level metric histograms | Shows mean/median lines |
| Executive Dashboard | 2x2 combining all views | GridSpec layout for subplots |

**Design Principles:**
- Clean, minimal styling (no chart junk)
- Color-blind friendly palette
- Annotations for key values
- Saved at 300 DPI for presentations

### 6. Reporting System

**File:** `src/reporting/memo.py`

```python
class KPIReportBuilder:
    def create_weekly_business_review(
        metrics_df,
        north_star_info,
        decomposition,
        key_insights
    ) -> str
```

**Output Format:** Markdown with:
- Executive summary (North Star value + components)
- Driver attribution (what moved and why)
- Full KPI table
- Key insights (bullet points)
- Recommended actions

**Use Case:** Auto-generate weekly business review for leadership. Can be converted to PDF or Slack message.

---

## SQL Layer

### Query Structure

**1. base_events.sql**
- **Input:** `orders`, `order_products`
- **Output:** One row per order with aggregated product metrics
- **Grain:** ORDER
- **Key Logic:** Aggregate items per order, compute reorder rate at order level

**2. kpi_user_aggregates.sql**
- **Input:** `base_events` (from query 1)
- **Output:** One row per user with lifetime metrics
- **Grain:** USER
- **Key Logic:** SUM/AVG/MEDIAN aggregations across all orders per user

**3. kpi_overall_summary.sql**
- **Input:** `kpi_user_aggregates` (from query 2)
- **Output:** Single row with company-wide metrics
- **Grain:** OVERALL
- **Key Logic:** Final aggregation across all users

### Why This Layering?

Each layer has a clear grain and purpose:
- **ORDER → USER → OVERALL** mirrors how metrics are computed
- Intermediate tables can be cached for performance
- Each query is independently testable

---

## Data Model

### Instacart Schema

```
orders:
  - order_id (PK)
  - user_id (FK)
  - order_number
  - order_dow (day of week)
  - order_hour_of_day
  - days_since_prior_order (NULL for first orders)

order_products:
  - order_id (FK)
  - product_id (FK)
  - add_to_cart_order
  - reordered (0/1 flag)

products:
  - product_id (PK)
  - product_name
  - aisle_id (FK)
  - department_id (FK)
```

### Derived Metrics

From this raw data, we compute:

**Order-level:**
- items_in_order
- reordered_items_in_order
- order_reorder_rate
- is_small_basket (≤3 items)

**User-level:**
- orders (count)
- items (sum)
- avg_basket_size
- reorder_rate (overall)
- small_basket_share
- median_days_since_prior

**Overall:**
- All user-level metrics averaged
- VPAC = orders_per_customer × items_per_order

---

## Testing Strategy

### Test Files

**test_metrics.py**
- Registry creation
- Metric computation accuracy
- VPAC formula validation (components multiply correctly)
- Threshold enforcement

**test_decomposition.py**
- Decomposition sums to total
- Single-driver attribution
- Validation catches bad math

**test_edge_cases.py**
- Single customer scenario
- No reorders (all first-time buyers)
- All reorders (ceiling case)
- Extreme power user (1000 orders)
- NULL handling

### Test Philosophy

**Unit tests** validate:
1. Individual metric formulas are correct
2. Decomposition math is sound
3. Edge cases don't break the system

**Integration** (manual via run_analysis.py):
1. End-to-end pipeline runs without errors
2. Generated figures exist and are non-empty
3. Reports contain expected sections

---

## Configuration

**File:** `src/config.py`

All magic numbers and parameters centralized:

```python
# Time parameters
WEEK_START_DAY = 0  # Monday

# Metric thresholds
SMALL_BASKET_THRESHOLD = 3  # items
ANOMALY_Z_THRESHOLD = 2.5
REORDER_RATE_MIN = 0.30

# Visual styling
COLOR_POSITIVE = "#2ecc71"
COLOR_NEGATIVE = "#e74c3c"
FIGSIZE_STANDARD = (12, 6)

# Paths
FIGURES_DIR = Path("figures")
REPORTS_DIR = Path("reports")
```

**Why This Matters:**  
Changing thresholds or styling doesn't require editing code. All adjustments happen in one file.

---

## Error Handling

### Graceful Degradation

**Metric computation errors:**
- Try to compute each metric independently
- If one fails, log error but continue with others
- Return partial results rather than crashing

**SQL errors:**
- Validate tables exist before querying
- Provide helpful error messages (e.g., "Download data from Kaggle")
- Use try/except with informative exceptions

**Validation failures:**
- Distinguish ERROR vs WARNING
- Warnings don't block, errors do
- All failures logged with context

### Exit Codes

- `0` = success
- `1` = general failure
- `130` = user interrupt (Ctrl+C)

---

## Deployment Considerations

**Not a production app, but follows production practices:**

1. **Reproducibility:** All config centralized
2. **Modularity:** Easy to swap data sources
3. **Validation:** Automated checks prevent bad data
4. **Documentation:** Self-documenting code + external docs
5. **Testing:** Unit tests ensure correctness

**To productionize:**
- Add time-series logic for true WoW
- Schedule execution (Airflow, cron)
- Export to BI tool (Tableau, Looker)
- Add alerting on threshold breaches
- Store results in database

---

## Performance

**Current runtime:** ~60 seconds on standard laptop

**Bottlenecks:**
1. CSV loading (32M order line items)
2. User-level aggregation (206K users)
3. Visualization rendering (matplotlib overhead)

**Optimization opportunities:**
- Parquet instead of CSV (5-10x faster loading)
- Pre-aggregate to weekly granularity
- Parallel metric computation
- Skip-viz flag already implemented

---

## Extension Points

### Adding a New Metric

1. Add computation function to `definitions.py`
2. Add MetricDefinition to registry
3. Document in `metric_dictionary.md`
4. Add test in `test_metrics.py`

### Adding a New Visualization

1. Add method to `KPIVisualizer` in `charts.py`
2. Call from `run_analysis.py`
3. Document in README

### Adding Time-Series Support

1. Modify SQL queries to include `date` dimension
2. Update `MetricEngine` to accept date filters
3. Implement `compare_periods()` with real dates
4. Add trend chart to visualizations

---

*For operational usage, see `docs/kpi_playbook.md`  
For metric specs, see `docs/metric_dictionary.md`*
