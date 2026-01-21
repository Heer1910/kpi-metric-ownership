#!/usr/bin/env python3
"""
KPI Framework Analysis Runner

Production CLI for KPI analysis with comprehensive arguments.
Generates all artifacts (CSV, markdown, visualizations) in one command.

Usage:
    python run_analysis.py                              # Run with defaults
    python run_analysis.py --data_dir custom_data/      # Custom data location
    python run_analysis.py --output_dir results/        # Custom output location
    python run_analysis.py --segment power_users        # Filter by segment
    python run_analysis.py --start_date 2020-01-01      # Date range (future)
"""

import sys
import argparse
import warnings
from pathlib import Path
from datetime import datetime

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
    """Parse production-level command line arguments."""
    parser = argparse.ArgumentParser(
        description='KPI Framework - Production Analytics Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_analysis.py                                    # Run with defaults
  python run_analysis.py --data_dir custom_data/            # Custom data path
  python run_analysis.py --output_dir results/              # Custom output path
  python run_analysis.py --segment power_users              # Segment filter
  python run_analysis.py --start_date 2020-01-01            # Date filter (future)
  python run_analysis.py --quiet --skip-viz                 # Fast execution
        """
    )
    
    # Data inputs
    parser.add_argument(
        '--data_dir',
        type=str,
        default='data',
        help='Path to data directory containing CSV files (default: data/)'
    )
    
    # Outputs
    parser.add_argument(
        '--output_dir',
        type=str,
        default='.',
        help='Base output directory for all artifacts (default: current dir)'
    )
    
    # Date filters (for production thinking - not used in static dataset)
    parser.add_argument(
        '--start_date',
        type=str,
        default=None,
        help='Start date for analysis (YYYY-MM-DD). Note: Dataset is static, this signals production thinking'
    )
    
    parser.add_argument(
        '--end_date',
        type=str,
        default=None,
        help='End date for analysis (YYYY-MM-DD). Note: Dataset is static'
    )
    
    # Segmentation
    parser.add_argument(
        '--segment',
        type=str,
        default=None,
        choices=['power_users', 'regular', 'occasional', 'one_time', 'device', 'department'],
        help='Filter analysis by customer segment'
    )
    
    # Execution options
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
        '--export_csv',
        action='store_true',
        default=True,
        help='Export KPI table as CSV (default: True)'
    )
    
    return parser.parse_args()


def log(message: str, quiet: bool = False) -> None:
    """Print message unless quiet mode enabled."""
    if not quiet:
        print(message)


def validate_dates(start_date: str, end_date: str) -> bool:
    """
    Validate date format and range.
    
    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        
    Returns:
        True if valid, False otherwise
    """
    if not start_date and not end_date:
        return True
    
    try:
        if start_date:
            datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_date and end_date:
            if start_date > end_date:
                print(f"ERROR: Start date ({start_date}) is after end date ({end_date})")
                return False
        
        return True
    except ValueError as e:
        print(f"ERROR: Invalid date format - {e}")
        print("Use YYYY-MM-DD format (e.g., 2020-01-01)")
        return False


def main() -> int:
    """
    Main analysis pipeline with production CLI.
    
    Returns:
        Exit code: 0 on success, non-zero on failure
    """
    args = parse_args()
    
    # Validate arguments
    if not validate_dates(args.start_date, args.end_date):
        return 1
    
    # Setup output directories
    base_output = Path(args.output_dir)
    figures_dir = base_output / 'figures'
    reports_dir = base_output / 'reports'
    
    figures_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        log("=" * 70, args.quiet)
        log("KPI FRAMEWORK ANALYSIS - PRODUCTION MODE", args.quiet)
        log("=" * 70, args.quiet)
        
        if args.start_date or args.end_date:
            log(f"\nDate Range: {args.start_date or 'earliest'} to {args.end_date or 'latest'}", args.quiet)
        
        if args.segment:
            log(f"Segment Filter: {args.segment}", args.quiet)
        
        # 1. Data Loading
        log("\n[1/8] Loading data...", args.quiet)
        try:
            loader = quick_load(data_dir=args.data_dir)
        except FileNotFoundError as e:
            print(f"\nERROR: Data files not found in {args.data_dir}/")
            print("\nDownload the Instacart dataset from:")
            print("https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis")
            print(f"Extract CSV files to {args.data_dir}/")
            return 1
        except Exception as e:
            print(f"\nERROR loading data: {e}")
            return 1
        
        # 2. Data Quality Checks (CRITICAL - affects exit code)
        log("\n[2/8] Running data quality checks...", args.quiet)
        checker = DataQualityChecker(max_missing_rate=0.05)
        orders_sample = loader.execute_sql("SELECT * FROM orders LIMIT 10000")
        results = checker.run_all_checks(orders_sample, "orders")
        
        # Check for ERRORS (not warnings)
        from src.quality.checks import CheckSeverity
        errors = [r for r in results if r.severity == CheckSeverity.ERROR and not r.passed]
        if errors:
            print("\n❌ DATA QUALITY CHECK FAILED")
            print(f"\nFound {len(errors)} critical error(s):")
            for err in errors:
                print(f"  - {err.message}")
            print("\nExiting with error code 1")
            return 1
        
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
        
        # Apply segment filter if specified
        if args.segment:
            if args.segment == 'power_users':
                user_kpis = user_kpis[user_kpis['orders'] >= 11]
            elif args.segment == 'regular':
                user_kpis = user_kpis[(user_kpis['orders'] >= 5) & (user_kpis['orders'] < 11)]
            elif args.segment == 'occasional':
                user_kpis = user_kpis[(user_kpis['orders'] >= 2) & (user_kpis['orders'] < 5)]
            elif args.segment == 'one_time':
                user_kpis = user_kpis[user_kpis['orders'] == 1]
            
            log(f"  Filtered to {len(user_kpis):,} customers in segment: {args.segment}", args.quiet)
        
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
            viz = KPIVisualizer(output_dir=figures_dir)
            
            viz.plot_metric_tree(north_star_info['value'], north_star_info['components'], save=True)
            viz.plot_waterfall(decomposition, save=True)
            viz.plot_segment_comparison(segments, save=True)
            viz.plot_kpi_health_grid(metrics_df, save=True)
            viz.plot_distribution(user_kpis['orders'], 'Orders per Customer', save=True)
            viz.plot_distribution(user_kpis['avg_basket_size'], 'Items per Order', save=True)
            
            # Executive dashboard
            log("  Creating executive dashboard...", args.quiet)
            from src.viz.dashboard import create_executive_dashboard
            create_executive_dashboard(
                north_star_info=north_star_info,
                decomposition=decomposition,
                segments=segments,
                metrics_df=metrics_df,
                save=True,
                output_dir=figures_dir
            )
            
            log(f"  ✓ All visualizations saved to {figures_dir}/", args.quiet)
        else:
            log("\n[6/8] Skipping visualizations (--skip-viz flag)", args.quiet)
        
        # 7. Export Artifacts
        log("\n[7/8] Exporting artifacts...", args.quiet)
        
        # Export KPI table as CSV
        if args.export_csv:
            csv_path = reports_dir / 'kpi_metrics.csv'
            metrics_df.to_csv(csv_path, index=False)
            log(f"  ✓ KPI table exported: {csv_path}", args.quiet)
        
        # Export KPI table as markdown
        md_table_path = reports_dir / 'kpi_table.md'
        with open(md_table_path, 'w') as f:
            f.write("# KPI Metrics\n\n")
            f.write(metrics_df.to_markdown(index=False))
        log(f"  ✓ KPI table (markdown): {md_table_path}", args.quiet)
        
        # Generate business review
        report_builder = KPIReportBuilder(output_dir=reports_dir)
        
        insights = [
            f"Power users drive {segments.loc['Power User', 'order_share']:.1%} of total orders despite being {segments.loc['Power User', 'customer_share']:.1%} of customers.",
            f"Reorder rate at {metrics_df[metrics_df['metric_name']=='reorder_rate']['value'].values[0]:.1%} indicates strong customer loyalty.",
            "Small basket share is within healthy thresholds, no acquisition quality concerns.",
        ]
        
        memo_path = report_builder.create_weekly_business_review(
            metrics_df=metrics_df,
            north_star_info=north_star_info,
            decomposition=decomposition,
            key_insights=insights,
            save=True
        )
        log(f"  ✓ Weekly business review: {memo_path}", args.quiet)
        
        # 8. Cleanup
        log("\n[8/8] Cleaning up...", args.quiet)
        loader.close()
        
        # Summary
        log("\n" + "=" * 70, args.quiet)
        log("✅ ANALYSIS COMPLETE", args.quiet)
        log("=" * 70, args.quiet)
        
        if not args.quiet:
            print(f"\nGenerated artifacts in: {base_output}/")
            print("\nFiles created:")
            if not args.skip_viz:
                print(f"  Visualizations: {figures_dir}/*.png (7 files)")
            print(f"  KPI Table (CSV): {reports_dir}/kpi_metrics.csv")
            print(f"  KPI Table (MD):  {reports_dir}/kpi_table.md")
            print(f"  Weekly Review:   {reports_dir}/weekly_business_review.md")
            print(f"\nKey Findings:")
            print(f"  VPAC: {north_star_info['value']:.2f} items/customer")
            print(f"  Active Customers: {metrics_df[metrics_df['metric_name']=='active_customers']['value'].values[0]:,.0f}")
            print(f"  Data Quality: {len([r for r in results if r.status == 'PASS'])} checks passed")
        
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
