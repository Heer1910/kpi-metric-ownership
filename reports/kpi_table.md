# KPI Metrics

| metric_name             | display_name                     | metric_type   |            value | unit            | owner                   | formula                               |
|:------------------------|:---------------------------------|:--------------|-----------------:|:----------------|:------------------------|:--------------------------------------|
| vpac                    | Value per Active Customer (VPAC) | north_star    |    162.016       | items/customer  | Product Growth          | Orders per Customer × Items per Order |
| active_customers        | Active Customers                 | driver        | 206209           | customers       | Marketing / Acquisition | COUNT(DISTINCT user_id)               |
| orders_per_customer     | Orders per Customer              | driver        |     16.2267      | orders/customer | Product / Retention     | AVG(orders per user)                  |
| items_per_order         | Items per Order                  | driver        |      9.98453     | items/order     | Product / Merchandising | AVG(items per order)                  |
| total_orders            | Total Orders                     | diagnostic    |      3.34608e+06 | orders          | Product Growth          | SUM(orders)                           |
| total_items             | Total Items                      | diagnostic    |      3.38191e+07 | items           | Product Growth          | SUM(items)                            |
| reorder_rate            | Reorder Rate                     | diagnostic    |      0.444332    | rate            | Product / Retention     | Reordered Items / Total Items         |
| small_basket_share      | Small Basket Share               | guardrail     |      0.184944    | rate            | Product Quality         | % of orders with ≤3 items             |
| median_days_since_prior | Median Days Between Orders       | guardrail     |     14.8         | days            | Product / Retention     | MEDIAN(days_since_prior_order)        |