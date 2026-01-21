# SQL Queries Documentation

This directory contains the SQL queries that power the KPI framework. All queries use DuckDB syntax (BigQuery-compatible).

---

## Execution Order

Run queries in this sequence:

1. **`base_events.sql`** - Extract order-level events
2. **`kpi_user_aggregates.sql`** - Aggregate to user level
3. **`kpi_overall_summary.sql`** - Company-wide summary

Each query depends on the output of the previous one.

---

## Query Overview

### 1. base_events.sql

**Purpose:** Extract order-level events with product aggregations

**Input Tables:**
- `orders` (user_id, order_id, order_number, days_since_prior_order, etc.)
- `order_products` (order_id, product_id, reordered)

**Output Table:** `base_events`
- **Grain:** ONE ROW PER ORDER
- **Columns:** order_id, user_id, items_in_order, reorder_rate, is_small_basket, etc.

**Expected Row Count:** ~3.4M orders

**Key Logic:**
- Aggregate items per order
- Calculate order-level reorder rate
- Flag small baskets (≤3 items)

### 2. kpi_user_aggregates.sql

**Purpose:** Aggregate order metrics to user level

**Input Tables:**
- `base_events` (from query 1)

**Output Table:** `user_kpis`
- **Grain:** ONE ROW PER USER
- **Columns:** user_id, orders, items, avg_basket_size, reorder_rate, small_basket_share, etc.

**Expected Row Count:** ~206K users

**Key Logic:**
- SUM orders and items per user
- Calculate avg basket size (items / orders)
- Compute overall reorder rate
- Calculate small basket share

**Stable Column Names (Used by Python):**
- `orders_per_customer` - for VPAC calculation
- `avg_basket_size` - maps to items_per_order
- `reorder_rate` - user-level reorder rate
- `small_basket_share` - quality metric

### 3. kpi_overall_summary.sql

**Purpose:** Company-wide KPI summary

**Input Tables:**
- `user_kpis` (from query 2)

**Output Table:** `overall_summary`
- **Grain:** ONE ROW (company total)
- **Columns:** active_customers, total_orders, vpac, orders_per_customer, items_per_order, etc.

**Expected Row Count:** 1 row

**Key Logic:**
- COUNT distinct users
- SUM total orders and items
- Calculate VPAC = AVG(orders_per_customer) × AVG(items_per_order)

---

## Validation Queries

Run these after each query to ensure data quality:

### After base_events.sql

```sql
-- Row count should match orders with products
SELECT COUNT(*) FROM base_events;  -- Expected: ~3.4M

-- All item counts should be positive
SELECT COUNT(*) FROM base_events WHERE items_in_order <= 0;  -- Expected: 0

-- Reorder rate should be [0, 1]
SELECT COUNT(*) FROM base_events 
WHERE order_reorder_rate < 0 OR order_reorder_rate > 1;  -- Expected: 0
```

### After kpi_user_aggregates.sql

```sql
-- Row count should match distinct users
SELECT COUNT(*) FROM user_kpis;  -- Expected: ~206K

-- All orders should be positive
SELECT COUNT(*) FROM user_kpis WHERE orders <= 0;  -- Expected: 0

-- Items >= orders (monotonic relationship)
SELECT COUNT(*) FROM user_kpis WHERE items < orders;  -- Expected: 0

-- Reorder rate should be [0, 1]
SELECT COUNT(*) FROM user_kpis 
WHERE reorder_rate < 0 OR reorder_rate > 1;  -- Expected: 0

-- Small basket share should be [0, 1]
SELECT COUNT(*) FROM user_kpis 
WHERE small_basket_share < 0 OR small_basket_share > 1;  -- Expected: 0
```

### After kpi_overall_summary.sql

```sql
-- Should return exactly 1 row
SELECT COUNT(*) FROM overall_summary;  -- Expected: 1

-- Active customers should match user count
SELECT active_customers FROM overall_summary;  -- Expected: ~206K

-- VPAC should equal components multiplied
SELECT 
  vpac,
  orders_per_customer * items_per_order AS calculated_vpac,
  ABS(vpac - (orders_per_customer * items_per_order)) AS diff
FROM overall_summary;  -- diff should be < 0.01
```

---

## Expected Row Counts (Sanity Checks)

| Query | Output Table | Expected Rows | Validation |
|-------|-------------|---------------|------------|
| base_events.sql | base_events | ~3,421,083 | Should match orders with products |
| kpi_user_aggregates.sql | user_kpis | ~206,209 | Should match distinct users |
| kpi_overall_summary.sql | overall_summary | 1 | Single summary row |

---

## Column Name Contract (SQL → Python)

These column names are STABLE and used by Python `MetricEngine`:

### user_kpis columns:
- `user_id` - unique user identifier
- `orders` - total orders per user
- `items` - total items ordered
- `avg_basket_size` - average items per order
- `reorder_rate` - % of items that are reorders
- `small_basket_share` - % of orders with ≤3 items
- `median_days_since_prior` - avg days between orders
- `orders_per_customer` - same as orders (for VPAC)

### overall_summary columns:
- `active_customers` - distinct user count
- `total_orders` - sum of all orders
- `total_items` - sum of all items
- `vpac` - North Star metric (orders_per_customer × items_per_order)
- `orders_per_customer` - avg orders per user
- `items_per_order` - avg items per order
- `avg_reorder_rate` - mean reorder rate
- `small_basket_share` - mean small basket %
- `median_days_since_prior` - median days between orders

**DO NOT RENAME THESE COLUMNS** - Python code depends on exact names.

---

## Known Edge Cases

### NULL values in days_since_prior_order
- **Cause:** First orders have no prior order
- **Frequency:** ~6-7% of orders
- **Handling:** Excluded from AVG/MEDIAN calculations (SQL handles this automatically)

### Single-order customers
- **Impact:** median_days_since_prior = NULL
- **Frequency:** ~20% of users
- **Handling:** Excluded from overall median calculation

### Small basket threshold
- **Definition:** ≤3 items per order
- **Configurable:** Yes, in `src/config.py` (SMALL_BASKET_THRESHOLD)
- **Used for:** Quality monitoring, not filtering

---

## Debugging Tips

### Query runs but returns no rows
```sql
-- Check if input tables exist
SELECT * FROM orders LIMIT 5;
SELECT * FROM order_products LIMIT 5;

-- Check join effectiveness
SELECT COUNT(*) FROM orders;
SELECT COUNT(DISTINCT order_id) FROM order_products;
```

### Unexpected metric values
```sql
-- Inspect sample user
SELECT * FROM user_kpis WHERE user_id = 1 LIMIT 1;

-- Check distribution
SELECT 
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY orders) AS p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY orders) AS p50,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY orders) AS p75
FROM user_kpis;
```

### Performance issues
- DuckDB loads CSVs lazily - first execution is always slower
- Use `LIMIT` clause when testing
- Pre-aggregate in CTEs when possible

---

## Maintenance

When updating these queries:

1. **Preserve column names** used by Python
2. **Update header comments** with assumptions/edge cases
3. **Run validation queries** to verify correctness
4. **Update this README** if execution order changes
5. **Increment version comment** at top of changed file

---

*Last updated: 2026-01-20*
