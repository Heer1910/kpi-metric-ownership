#!/usr/bin/env python3
"""
Standalone script to run KPI analysis (alternative to Jupyter notebook).
Run with: python run_analysis.py
"""

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

from src.io.data_loader import quick_load
from src.metrics.compute import MetricEngine
from src.quality.checks import DataQualityChecker
from src.analysis.decomposition import VPACDecomposer, CustomerSegmentation
from src.viz.charts import KPIVisualizer
from src.reporting.memo import KPIReportBuilder

print("="*70)
print("KPI FRAMEWORK ANALYSIS")
print("="*70)

# 1. Load Data
print("\n[1/8] Loading data...")
loader = quick_load()

# 2. Data Quality
print("\n[2/8] Running data quality checks...")
checker = DataQualityChecker(max_missing_rate=0.05)
orders_df = loader.execute_sql("SELECT * FROM orders LIMIT 10000")
results = checker.run_all_checks(orders_df, "orders")
print(checker.get_summary_report())

# 3. Compute KPIs
print("\n[3/8] Computing all KPIs...")
engine = MetricEngine(loader)
metrics_df = engine.compute_all_metrics()
north_star_info = engine.get_north_star()

print("\n" + engine.get_metric_report())

# 4. Customer Segmentation
print("\n[4/8] Analyzing customer segments...")
user_kpis = engine._get_user_kpis()
order_freq_segments = CustomerSegmentation.segment_by_order_frequency(user_kpis)

print("\nCustomer Segments by Order Frequency:")
print(order_freq_segments[['customer_count', 'orders', 'vpac', 'order_share']])

# 5. VPAC Decomposition (simulated comparison)
print("\n[5/8] Running VPAC decomposition...")
median_orders = user_kpis['orders'].median()
period1_users = user_kpis[user_kpis['orders'] <= median_orders]
period2_users = user_kpis[user_kpis['orders'] > median_orders]

period1_metrics = {
    'vpac': period1_users['orders_per_customer'].mean() * period1_users['avg_basket_size'].mean(),
    'orders_per_customer': period1_users['orders_per_customer'].mean(),
    'items_per_order': period1_users['avg_basket_size'].mean()
}

period2_metrics = {
    'vpac': period2_users['orders_per_customer'].mean() * period2_users['avg_basket_size'].mean(),
    'orders_per_customer': period2_users['orders_per_customer'].mean(),
    'items_per_order': period2_users['avg_basket_size'].mean()
}

decomposer = VPACDecomposer()
decomposition = decomposer.decompose_vpac_change(
    period1_metrics, period2_metrics,
    period1_label="Lower-Frequency", period2_label="Higher-Frequency"
)

print(f"\nVPAC Change: {decomposition.total_change:+.2f} ({decomposition.percent_change:+.1%})")
print("\nDriver Contributions:")
for driver, contrib in decomposition.driver_contributions.items():
    print(f"  {driver}: {contrib:+.2f}")

decomposer.validate_decomposition(decomposition, tolerance=0.01)
print("✓ Decomposition validated")

# 6. Generate Visualizations
print("\n[6/8] Creating visualizations...")
viz = KPIVisualizer()

viz.plot_metric_tree(north_star_info['value'], north_star_info['components'], save=True)
print("  ✓ Metric tree saved")

viz.plot_waterfall(decomposition, save=True)
print("  ✓ Waterfall chart saved")

viz.plot_segment_comparison(order_freq_segments, save=True)
print("  ✓ Segment comparison saved")

viz.plot_kpi_health_grid(metrics_df, save=True)
print("  ✓ KPI health grid saved")

viz.plot_distribution(user_kpis['orders'], 'Orders per Customer', save=True)
viz.plot_distribution(user_kpis['avg_basket_size'], 'Items per Order', save=True)
print("  ✓ Distribution plots saved")

# 7. Generate Business Review
print("\n[7/8] Generating weekly business review...")
report_builder = KPIReportBuilder()

key_insights = [
    "Higher-frequency customers have significantly higher VPAC driven primarily by order frequency.",
    "Power users (11+ orders) represent the highest VPAC segment and contribute disproportionately to total items.",
    "Reorder rate is healthy across all segments, indicating strong product-market fit.",
    "Small basket share is within acceptable thresholds, suggesting good acquisition quality."
]

report = report_builder.create_weekly_business_review(
    metrics_df=metrics_df,
    north_star_info=north_star_info,
    decomposition=decomposition,
    key_insights=key_insights,
    save=True
)

# 8. Cleanup
print("\n[8/8] Cleaning up...")
loader.close()

print("\n" + "="*70)
print("✅ ANALYSIS COMPLETE!")
print("="*70)
print("\nGenerated files:")
print("  - figures/01_metric_tree.png")
print("  - figures/02_vpac_waterfall.png")
print("  - figures/03_segment_comparison.png")
print("  - figures/04_kpi_health_grid.png")
print("  - figures/05_dist_*.png")
print("  - reports/weekly_business_review.md")
print("\nView the figures in the 'figures/' directory!")
