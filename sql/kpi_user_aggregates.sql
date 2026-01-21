/*
====================================================================
USER-LEVEL KPI AGGREGATION
====================================================================

Purpose: Aggregate order- and item-level metrics per user

Input Tables:
  - base_events (from base_events.sql)
    Grain: ONE ROW PER ORDER
    Columns: user_id, orders, items, reorder_rate, small_baskets, etc.

Output Table: user_kpis
  - Grain: ONE ROW PER USER
  - Columns: user_id, orders, items, avg_basket_size, reorder_rate, 
             small_basket_share, median_days_since_prior, orders_per_customer

Key Metrics Computed:
  - orders: Total orders per user
  - items: Total items ordered
  - avg_basket_size: Average items per order (items / orders)
  - reorder_rate: % of items that are reorders (across all items)
  - small_basket_share: % of orders with ≤3 items
  - median_days_since_prior: Average days between consecutive orders

Business Logic:
  - Reorder rate calculated across ALL items, not just orders
  - Small basket threshold set to 3 items (matches config.py)
  - First orders have NULL days_since_prior_order (handled in AVG)
  - orders_per_customer duplicated for VPAC calculation

Key Assumptions:
  - Each user has at least one order (from inner join in base_events)
  - total_orders > 0 for all rows (division by zero protected anyway)
  - days_since_prior_order NULL for first orders (expected, ~6% of dataset)
  - Reordered flag is accurate (0/1, NULL treated as 0)

Known Edge Cases:
  - Single-order customers: median_days_since_prior = NULL (expected)
  - All-reorder customers: reorder_rate = 1.0 (valid)
  - All small baskets: small_basket_share = 1.0 (quality flag)
  - Users with 1 order: avg and median are same

Expected Row Count: ~206K users (matches distinct user_id from orders)

Validation Query:
  -- Row count should match distinct users
  SELECT COUNT(*) FROM user_kpis;  -- Should be ~206K
  
  -- All orders should be positive
  SELECT COUNT(*) FROM user_kpis WHERE orders <= 0;  -- Should be 0
  
  -- Items >= orders (monotonic relationship)
  SELECT COUNT(*) FROM user_kpis WHERE items < orders;  -- Should be 0
  
  -- Reorder rate should be [0, 1]
  SELECT COUNT(*) FROM user_kpis 
  WHERE reorder_rate < 0 OR reorder_rate > 1;  -- Should be 0
  
  -- Small basket share should be [0, 1]
  SELECT COUNT(*) FROM user_kpis 
  WHERE small_basket_share < 0 OR small_basket_share > 1;  -- Should be 0

Execution Order: 2 (run after base_events.sql)
Dependencies: base_events table must exist
Used By: kpi_overall_summary.sql, Python MetricEngine
*/

WITH base_orders AS (
    SELECT * FROM base_events
),

user_aggregates AS (
    SELECT
        user_id,
        COUNT(*) AS total_orders,
        SUM(items_in_order) AS total_items,
        AVG(items_in_order) AS avg_items_per_order,
        SUM(reordered_items_in_order) AS total_reordered_items,
        AVG(order_reorder_rate) AS avg_reorder_rate,
        SUM(is_small_basket) AS small_basket_count,
        AVG(days_since_prior_order) AS avg_days_between_orders,
        MAX(order_number) AS max_order_number
    FROM base_orders
    GROUP BY user_id
)

-- Create persistent table
CREATE TABLE IF NOT EXISTS user_kpis AS
SELECT
    user_id,
    total_orders AS orders,
    total_items AS items,
    avg_items_per_order AS avg_basket_size,
    
    -- Reorder rate (overall)
    CASE 
        WHEN total_items > 0 
        THEN CAST(total_reordered_items AS DOUBLE) / total_items
        ELSE 0.0
    END AS reorder_rate,
    
    -- Small basket share
    CASE 
        WHEN total_orders > 0 
        THEN CAST(small_basket_count AS DOUBLE) / total_orders
        ELSE 0.0
    END AS small_basket_share,
    
    -- Frequency health
    avg_days_between_orders AS median_days_since_prior,
    
    -- North Star components (stable column names for Python)
    total_orders AS orders_per_customer,
    avg_items_per_order  -- Used for items_per_order in Python
    
FROM user_aggregates
ORDER BY user_id;
