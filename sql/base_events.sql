/*
====================================================================
BASE EVENT EXTRACTION
====================================================================

Purpose: Extract order-level events with product aggregations

Input Tables:
  - orders (user_id, order_id, order_number, order_dow, order_hour_of_day, days_since_prior_order)
  - order_products (order_id, product_id, reordered)

Output Table: base_events
  - Grain: ONE ROW PER ORDER
  - Columns: order details + aggregated product metrics + derived flags

Key Logic:
  1. Aggregate items per order from order_products
  2. Calculate reorder rate as (reordered items / total items)
  3. Flag small baskets (≤3 items) for quality monitoring
  4. Join back to orders table for temporal dimensions

Note: days_since_prior_order is NULL for first orders (expected)
*/

WITH order_items_agg AS (
    -- Aggregate order-level metrics from line items
    SELECT
        order_id,
        COUNT(*) AS items_in_order,
        SUM(CAST(reordered AS INTEGER)) AS reordered_items_in_order,
        COUNT(DISTINCT product_id) AS unique_products_in_order
    FROM order_products
    GROUP BY order_id
),

order_with_products AS (
    -- Join orders with product details
    SELECT
        o.order_id,
        o.user_id,
        o.order_number,
        o.order_dow,
        o.order_hour_of_day,
        o.days_since_prior_order,
        oi.items_in_order,
        oi.reordered_items_in_order,
        oi.unique_products_in_order,
        -- Compute reorder rate at order level
        CASE 
            WHEN oi.items_in_order > 0 
            THEN CAST(oi.reordered_items_in_order AS DOUBLE) / oi.items_in_order
            ELSE 0.0
        END AS order_reorder_rate,
        -- Flag small baskets
        CASE WHEN oi.items_in_order <= 3 THEN 1 ELSE 0 END AS is_small_basket
    FROM orders o
    INNER JOIN order_items_agg oi ON o.order_id = oi.order_id
)

SELECT
    order_id,
    user_id,
    order_number,
    order_dow,
    order_hour_of_day,
    days_since_prior_order,
    items_in_order,
    reordered_items_in_order,
    unique_products_in_order,
    order_reorder_rate,
    is_small_basket
FROM order_with_products
ORDER BY user_id, order_number
