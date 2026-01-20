# KPI Metric Dictionary

**Purpose:** This document defines all metrics used in the KPI framework with complete specifications.

**Last Updated:** 2026-01-20

---

## North Star Metric

### VPAC (Value per Active Customer)

**Definition:** The average value generated per active customer, combining purchase frequency and basket depth.

**Formula:**
```
VPAC = Orders per Customer × Items per Order
```

**Grain:** Overall (aggregated across all customers)

**Metric Type:** North Star

**Unit:** items/customer

**Owner:** Product Growth

**Computation:**
1. Compute user-level metrics: orders per user, average items per order per user
2. Average across all active users

**Business Logic:**
- Instacart does not include prices, so this project uses a value proxy commonly used in product analytics when direct revenue is unavailable. We define the North Star as Value per Active Customer (VPAC) = Orders per Active Customer × Items per Order, which captures both purchase frequency and basket depth and is directionally correlated with revenue.

**Thresholds:**
- Minimum: 0

**Dependencies:** `orders_per_customer`, `items_per_order`

---

## Driver Metrics

### Active Customers

**Definition:** Number of unique customers who placed at least one order in the analysis period.

**Formula:**
```
Active Customers = COUNT(DISTINCT user_id)
```

**Grain:** Overall

**Metric Type:** Driver

**Unit:** customers

**Owner:** Marketing / Acquisition

**Computation:**
```sql
SELECT COUNT(DISTINCT user_id) FROM user_kpis
```

**Business Logic:**
- Includes all users with at least 1 order
- No time-based activity filter (uses full dataset)

**Thresholds:**
- Minimum: 1

**Edge Cases:**
- Users with 0 orders are excluded from the dataset

---

### Orders per Customer

**Definition:** Average number of orders per active customer (purchase frequency).

**Formula:**
```
Orders per Customer = AVG(orders per user)
```

**Grain:** Overall (averaged across users)

**Metric Type:** Driver

**Unit:** orders/customer

**Owner:** Product / Retention

**Computation:**
1. For each user: count total orders
2. Average across all active users

**Business Logic:**
- Directly measures purchase frequency
- Higher values indicate better retention

**Thresholds:**
- Minimum: 1.0 (all active customers have at least 1 order)

**Dependencies:** None

---

### Items per Order

**Definition:** Average basket size measured by number of items per order.

**Formula:**
```
Items per Order = AVG(items per order across all users)
```

**Grain:** Overall (averaged across users' average basket sizes)

**Metric Type:** Driver

**Unit:** items/order

**Owner:** Product / Merchandising

**Computation:**
1. For each user: compute average items per order
2. Average across all users

**Business Logic:**
- Measures basket depth
- Influenced by merchandising, product discovery, and UX

**Thresholds:**
- Minimum: 1.0 (all orders have at least 1 item)

**Dependencies:** None

---

## Supporting KPIs

### Total Orders

**Definition:** Total number of orders placed by all customers.

**Formula:**
```
Total Orders = SUM(orders)
```

**Grain:** Overall

**Metric Type:** Diagnostic

**Unit:** orders

**Owner:** Product Growth

**Thresholds:**
- Minimum: 0

---

### Total Items

**Definition:** Total number of items ordered across all orders.

**Formula:**
```
Total Items = SUM(items)
```

**Grain:** Overall

**Metric Type:** Diagnostic

**Unit:** items

**Owner:** Product Growth

**Thresholds:**
- Minimum: 0

---

### Reorder Rate

**Definition:** Percentage of items that are reorders (loyalty indicator).

**Formula:**
```
Reorder Rate = Reordered Items / Total Items
```

**Grain:** Overall

**Metric Type:** Diagnostic

**Unit:** rate (0 to 1)

**Owner:** Product / Retention

**Business Logic:**
- Measures customer loyalty and product-market fit
- Higher reorder rate indicates satisfied, returning customers

**Thresholds:**
- Minimum: 0.0
- Maximum: 1.0

---

## Guardrail Metrics

### Small Basket Share

**Definition:** Percentage of orders with ≤3 items (detects low-quality growth).

**Formula:**
```
Small Basket Share = Orders with ≤3 items / Total Orders
```

**Grain:** Overall

**Metric Type:** Guardrail

**Unit:** rate (0 to 1)

**Owner:** Product Quality

**Business Logic:**
- High share of small baskets may indicate:
  - Low engagement
  - Poor merchandising
  - Acquisition of low-quality users

**Thresholds:**
- Maximum: 0.30 (alert if >30% are small baskets)

**Action Trigger:**
If this metric exceeds 30%, investigate:
- Recent acquisition channels
- Product discovery UX
- Merchandising campaigns

---

### Median Days Between Orders

**Definition:** Median number of days between consecutive orders (frequency health check).

**Formula:**
```
Median Days Between Orders = MEDIAN(days_since_prior_order)
```

**Grain:** Overall

**Metric Type:** Guardrail

**Unit:** days

**Owner:** Product / Retention

**Business Logic:**
- Lower values indicate higher purchase frequency
- Sudden increases may signal retention issues

**Thresholds:**
- Minimum: 1

**Action Trigger:**
If this metric increases significantly week-over-week, investigate:
- Product availability issues
- Competitive activity
- Seasonal effects

---

## Metric Ownership Matrix

| Metric | Team Owner | Review Cadence |
|--------|-----------|----------------|
| VPAC | Product Growth | Weekly |
| Active Customers | Marketing / Acquisition | Weekly |
| Orders per Customer | Product / Retention | Weekly |
| Items per Order | Product / Merchandising | Weekly |
| Reorder Rate | Product / Retention | Bi-weekly |
| Small Basket Share | Product Quality | Weekly |
| Median Days Between Orders | Product / Retention | Weekly |

---

## Data Lineage

```
Raw Data (Instacart CSVs)
    ↓
orders.csv + order_products.csv + products.csv
    ↓
SQL: base_events.sql (order-level aggregation)
    ↓
SQL: kpi_user_level.sql (user-level aggregation)
    ↓
Python: MetricEngine.compute_all_metrics()
    ↓
Final KPI Values
```

---

## Validation Rules

1. **Monotonic Relationships:**
   - `Total Orders >= Active Customers` (some customers order multiple times)
   - `Total Items >= Total Orders` (all orders have at least 1 item)

2. **Range Checks:**
   - All count metrics >= 0
   - All rate metrics between 0 and 1

3. **Null Handling:**
   - `days_since_prior_order` is NULL for first orders (expected)
   - All other metrics should not be NULL

4. **Decomposition Validation:**
   - Sum of driver contributions must equal total VPAC change within 1% tolerance

---

*This metric dictionary is the single source of truth for all KPI definitions in the framework.*
