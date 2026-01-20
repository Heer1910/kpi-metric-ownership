/*
Overall KPI summary.

This query computes company-level KPIs across all users.

Output grain: one row (total summary)
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
    
    -- Customer segmentation
    SUM(CASE WHEN lifetime_orders = 1 THEN 1 ELSE 0 END) AS one_time_customers,
    SUM(CASE WHEN lifetime_orders >= 5 THEN 1 ELSE 0 END) AS power_users
    
FROM user_kpis
