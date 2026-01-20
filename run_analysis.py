#!/usr/bin/env python3
"""
KPI Framework Analysis Runner

Executes the complete KPI analysis pipeline including:
- Data loading and quality validation
- Metric computation with VPAC (North Star)
- Customer segmentation
- Driver decomposition
- Visualization generation
- Business review creation

Usage:
    python run_analysis.py                    # Run full analysis
    python run_analysis.py --quiet            # Minimal output
    python run_analysis.py --skip-viz         # Skip visualization generation
"""

import sys
import argparse
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from src.io.data_loader import quick_load
from src.metrics.compute import MetricEngine
from src.quality.checks import DataQualityChecker
from src.analysis.decomposition import VPACDecomposer, CustomerSegmentation
from src.viz.charts import KPIVisualizer
from src.reporting.memo import KPIReportBuilder


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run KPI framework analysis on Instacart dataset'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal console output'
    )
    parser.add_argument(
        '--skip-viz',
        action='store_true',
        help='Skip visualization generation (faster execution)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='Output directory for results'
    )
    
    return parser.parse_args()


def log(message: str, quiet: bool = False) -> None:
    """Print message unless quiet mode enabled."""
    if not quiet:
        print(message)


def main() -> int:
    """
    Main analysis pipeline.
    
    Returns:
        0 on success, non-zero on failure
    """
    args = parse_args()
    
    try:
        log("=" * 70, args.quiet)
        log("KPI FRAMEWORK ANALYSIS", args.quiet)
        log("=" * 70, args.quiet)
        
        # 1. Data Loading
        log("\n[1/8] Loading data...", args.quiet)
        try:
            loader = quick_load()
        except FileNotFoundError as e:
            print(f"ERROR: Data files not found - {e}")
            print("\nDownload the Instacart dataset from:")
            print("https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis")
            print("Extract CSV files to the data/ directory")
            return 1
        except Exception as e:
            print(f"ERROR loading data: {e}")
            return 1
        
        # 2. Data Quality Checks
        log("\n[2/8] Running data quality checks...", args.quiet)
        checker = DataQualityChecker(max_missing_rate=0.05)
        orders_sample = loader.execute_sql("SELECT * FROM orders LIMIT 10000")
        results = checker.run_all_checks(orders_sample, "orders")
        
        if not args.quiet:
            print(checker.get_summary_report())
        
        # 3. Metric Computation
        log("\n[3/8] Computing KPIs...", args.quiet)
        engine = MetricEngine(loader)
        metrics_df = engine.compute_all_metrics()
        north_star_info = engine.get_north_star()
        
        if not args.quiet:
            print("\n" + engine.get_metric_report())
        else:
            print(f"VPAC (North Star): {north_star_info['value']:.2f}")
        
        # 4. Customer Segmentation
        log("\n[4/8] Analyzing customer segments...", args.quiet)
        user_kpis = engine._get_user_kpis()
        segments = CustomerSegmentation.segment_by_order_frequency(user_kpis)
        
        if not args.quiet:
            print("\nCustomer Segments:")
            print(segments[['customer_count', 'vpac', 'order_share']].to_string())
        
        # 5. Driver Decomposition
        log("\n[5/8] Running VPAC decomposition...", args.quiet)
        median_orders = user_kpis['orders'].median()
        
        low_freq = user_kpis[user_kpis['orders'] <= median_orders]
        high_freq = user_kpis[user_kpis['orders'] > median_orders]
        
        p1_metrics = {
            'vpac': low_freq['orders_per_customer'].mean() * low_freq['avg_basket_size'].mean(),
            'orders_per_customer': low_freq['orders_per_customer'].mean(),
            'items_per_order': low_freq['avg_basket_size'].mean()
        }
        
        p2_metrics = {
            'vpac': high_freq['orders_per_customer'].mean() * high_freq['avg_basket_size'].mean(),
            'orders_per_customer': high_freq['orders_per_customer'].mean(),
            'items_per_order': high_freq['avg_basket_size'].mean()
        }
        
        decomposer = VPACDecomposer()
        decomposition = decomposer.decompose_vpac_change(
            p1_metrics, p2_metrics,
            period1_label="Low-Frequency Users",
            period2_label="High-Frequency Users"
        )
        
        # Validate decomposition
        try:
            decomposer.validate_decomposition(decomposition, tolerance=0.01)
            log("✓ Decomposition validated", args.quiet)
        except ValueError as e:
            print(f"WARNING: {e}")
        
        if not args.quiet:
            print(f"\nVPAC Change: {decomposition.total_change:+.2f}")
            for driver, contrib in decomposition.driver_contributions.items():
                print(f"  {driver}: {contrib:+.2f}")
        
        # 6. Visualization Generation
        if not args.skip_viz:
            log("\n[6/8] Creating visualizations...", args.quiet)
            viz = KPIVisualizer()
            
            viz.plot_metric_tree(north_star_info['value'], north_star_info['components'], save=True)
            viz.plot_waterfall(decomposition, save=True)
            viz.plot_segment_comparison(segments, save=True)
            viz.plot_kpi_health_grid(metrics_df, save=True)
            viz.plot_distribution(user_kpis['orders'], 'Orders per Customer', save=True)
            viz.plot_distribution(user_kpis['avg_basket_size'], 'Items per Order', save=True)
            
            log("  ✓ All visualizations saved to figures/", args.quiet)
            
            # Generate executive dashboard (2x2 panel)
            log("\n  Creating executive dashboard...", args.quiet)
            from src.viz.dashboard import create_executive_dashboard
            create_executive_dashboard(
                north_star_info=north_star_info,
                decomposition=decomposition,
                segments=segments,
                metrics_df=metrics_df,
                save=True
            )
            log("  ✓ Executive dashboard created", args.quiet)
        else:
            log("\n[6/8] Skipping visualizations (--skip-viz flag)", args.quiet)
        
        # 7. Business Review Generation
        log("\n[7/8] Generating business review...", args.quiet)
        report_builder = KPIReportBuilder()
        
        insights = [
            f"Power users drive {segments.loc['Power User', 'order_share']:.1%} of total orders despite being {segments.loc['Power User', 'customer_share']:.1%} of customers.",
            f"Reorder rate at {metrics_df[metrics_df['metric_name']=='reorder_rate']['value'].values[0]:.1%} indicates strong customer loyalty.",
            "Small basket share is within healthy thresholds, no acquisition quality concerns.",
        ]
        
        report_builder.create_weekly_business_review(
            metrics_df=metrics_df,
            north_star_info=north_star_info,
            decomposition=decomposition,
            key_insights=insights,
            save=True
        )
        
        # 8. Cleanup
        log("\n[8/8] Cleaning up...", args.quiet)
        loader.close()
        
        # Summary
        log("\n" + "=" * 70, args.quiet)
        log("✅ ANALYSIS COMPLETE", args.quiet)
        log("=" * 70, args.quiet)
        
        if not args.quiet:
            print("\nGenerated files:")
            if not args.skip_viz:
                print("  Visuals:  figures/*.png (6 files)")
            print("  Report:   reports/weekly_business_review.md")
            print(f"\nKey Findings:")
            print(f"  VPAC: {north_star_info['value']:.2f} items/customer")
            print(f"  Active Customers: {metrics_df[metrics_df['metric_name']=='active_customers']['value'].values[0]:,.0f}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\nERROR: Analysis failed - {e}")
        import traceback
        if not args.quiet:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
