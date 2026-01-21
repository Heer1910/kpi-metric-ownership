/*
====================================================================
OVERALL KPI SUMMARY
====================================================================

Purpose: Compute company-wide KPIs by aggregating across all users

Input Tables:
  - user_kpis (from kpi_user_aggregates.sql)
    Grain: ONE ROW PER USER
    Columns: user_id, orders, items, reorder_rate, etc.

Output Table: overall_summary
  - Grain: ONE ROW (company-wide summary)
  - Columns: active_customers, total_orders, total_items, vpac,
             orders_per_customer, items_per_order, avg_reorder_rate,
             small_basket_share, median_days_since_prior

Key Metrics Computed:
  - active_customers: COUNT(DISTINCT user_id)
  - total_orders: SUM(orders) across all users
  - total_items: SUM(items) across all users
  - vpac (North Star): AVG(orders_per_customer) × AVG(items_per_order)
  - orders_per_customer: Average orders per user
  - items_per_order: Average items per order
  - avg_reorder_rate: Mean reorder rate across users
  - small_basket_share: Mean % of small baskets
  - median_days_since_prior: Median days between orders

Business Logic:
  - VPAC = Orders per Customer × Items per Order (North Star metric)
  - Averages computed at user level, then averaged
  - Percentile for median_days uses PERCENTILE_CONT(0.5)

Key Assumptions:
  - user_kpis table has been populated
  - All users have orders > 0
  - NULL median_days_since_prior for single-order users (excluded from median)

Known Edge Cases:
  - Single-order customers don't contribute to median_days_since_prior
  - VPAC uses averages of averages (correct for ratio metrics)
  - Empty dataset would return NULL (protected upstream)

Expected Row Count: 1 (single summary row)

Validation Query:
  -- Should return exactly 1 row
  SELECT COUNT(*) FROM overall_summary;  -- Should be 1
  
  -- Active customers should match user count
  SELECT active_customers FROM overall_summary;  -- Should be ~206K
  
  -- Total orders should be large
  SELECT total_orders FROM overall_summary;  -- Should be ~3.4M
  
  -- VPAC should equal components multiplied
  SELECT 
    vpac,
    orders_per_customer * items_per_order AS calculated_vpac,
    ABS(vpac - (orders_per_customer * items_per_order)) AS diff
  FROM overall_summary;  -- diff should be < 0.01

Execution Order: 3 (run after kpi_user_aggregates.sql)
Dependencies: user_kpis table must exist
Used By: Python MetricEngine for North Star reporting
*/

WITH user_kpis AS (
    SELECT * FROM user_kpis_table
)

SELECT
    -- Volume metrics
    COUNT(DISTINCT user_id) AS active_customers,
    SUM(orders) AS total_orders,
    SUM(items) AS total_items,
    
    -- North Star: VPAC = Orders per Customer × Items per Order
    AVG(orders_per_customer) AS orders_per_customer,
    AVG(avg_basket_size) AS items_per_order,
    AVG(orders_per_customer) * AVG(avg_basket_size) AS vpac,
    
    -- Supporting KPIs
    AVG(reorder_rate) AS avg_reorder_rate,
    AVG(small_basket_share) AS small_basket_share,
    
    -- Guardrails
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY median_days_since_prior) AS median_days_since_prior,
    
    -- Customer segmentation (for context)
    SUM(CASE WHEN orders = 1 THEN 1 ELSE 0 END) AS one_time_customers,
    SUM(CASE WHEN orders >= 11 THEN 1 ELSE 0 END) AS power_users
    
FROM user_kpis
