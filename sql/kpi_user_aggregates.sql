/*
====================================================================
USER-LEVEL KPI AGGREGATION
====================================================================

Purpose: Aggregate order- and item-level metrics per user

Input Tables:
  - base_events (from base_events.sql)

Output Table: user_kpis
  - Grain: ONE ROW PER USER
  - Columns: user_id + lifetime metrics + derived KPIs

Key Metrics Computed:
  - orders: Total orders per user
  - items: Total items ordered
  - avg_basket_size: Average items per order (items / orders)
  - reorder_rate: % of items that are reorders
  - small_basket_share: % of orders with ≤3 items
  - median_days_since_prior: Avg days between consecutive orders

Business Logic:
  - Reorder rate calculated across ALL items, not just orders
  - Small basket threshold set to 3 items (configurable in config.py)
  - First orders have NULL days_since_prior_order (handled in avg)
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
    
    -- Engagement proxy
    max_order_number AS lifetime_orders,
    
    -- North Star components
    total_orders AS orders_per_customer,
    avg_items_per_order AS avg_basket_size
    
FROM user_aggregates
ORDER BY user_id
