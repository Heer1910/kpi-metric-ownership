/*
User-level KPI aggregation.

This query computes all KPIs at the user level, which can then be aggregated
to weekly or monthly grains.

Output grain: one row per user
*/

WITH base_orders AS (
    SELECT * FROM base_events
),

user_aggregates AS (
    SELECT
        user_id,
        -- Order metrics
        COUNT(*) AS total_orders,
        
        -- Item metrics
        SUM(items_in_order) AS total_items,
        AVG(items_in_order) AS avg_items_per_order,
        
        -- Reorder metrics
        SUM(reordered_items_in_order) AS total_reordered_items,
        AVG(order_reorder_rate) AS avg_reorder_rate,
        
        -- Basket size distribution
        SUM(is_small_basket) AS small_basket_count,
        
        -- Temporal metrics
        AVG(days_since_prior_order) AS avg_days_between_orders,
        
        -- User activity level
        MAX(order_number) AS max_order_number
        
    FROM base_orders
    GROUP BY user_id
)

SELECT
    user_id,
    total_orders AS orders,
    total_items AS items,
    avg_items_per_order AS items_per_order,
    
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
