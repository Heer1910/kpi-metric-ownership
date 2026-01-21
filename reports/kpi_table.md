# KPI Metrics

| metric_name             | display_name                     | metric_type   |         value | unit            | owner                | formula                               |
|:------------------------|:---------------------------------|:--------------|--------------:|:----------------|:---------------------|:--------------------------------------|
| vpac                    | Value per Active Customer (VPAC) | north_star    |    162.016    | items/customer  | Product Growth Lead  | orders_per_customer × items_per_order |
| active_customers        | Active Customers                 | driver        | 206209        | customers       | Marketing Lead       | COUNT(DISTINCT user_id)               |
| orders_per_customer     | Orders per Customer              | driver        |     16.2267   | orders/customer | Retention PM         | AVG(orders)                           |
| items_per_order         | Items per Order                  | driver        |      9.98453  | items/order     | Merchandising PM     | AVG(avg_basket_size)                  |
| reorder_rate            | Reorder Rate                     | guardrail     |      0.444332 | rate            | Retention PM         | AVG(reorder_rate)                     |
| small_basket_share      | Small Basket Share               | guardrail     |      0.184944 | rate            | Product Quality Lead | AVG(small_basket_share)               |
| median_days_since_prior | Median Days Between Orders       | guardrail     |     14.8      | days            | Retention PM         | MEDIAN(median_days_since_prior)       |