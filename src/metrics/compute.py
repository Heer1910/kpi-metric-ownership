"""
Metric computation engine.

This module provides the MetricEngine class which computes all KPIs
from the base data using the metric definitions.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from pathlib import Path

from .definitions import MetricDefinition, create_metric_registry, MetricType
from ..io.data_loader import InstacartDataLoader


class MetricEngine:
    """
    Computes KPIs from base data using defined metric registry.
    
    The engine:
    1. Loads data via SQL queries
    2. Applies metric computation functions
    3. Returns structured metric results with metadata
    """
    
    def __init__(self, data_loader: InstacartDataLoader):
        """
        Initialize metric engine.
        
        Args:
            data_loader: Connected data loader instance
        """
        self.loader = data_loader
        self.registry = create_metric_registry()
        self.results: Dict[str, Any] = {}
        
    def compute_all_metrics(self) -> pd.DataFrame:
        """
        Compute all metrics in the registry.
        
        Returns:
            DataFrame with one row per metric containing:
            - metric_name
            - metric_type
            - value
            - unit
            - owner
        """
        # First, get user-level KPI data
        user_kpis = self._get_user_kpis()
        
        # Compute each metric
        results = []
        
        for metric_name, metric_def in self.registry.items():
            try:
                value = metric_def.compute(user_kpis)
                
                results.append({
                    "metric_name": metric_name,
                    "display_name": metric_def.display_name,
                    "metric_type": metric_def.metric_type.value,
                    "value": value,
                    "unit": metric_def.unit,
                    "owner": metric_def.owner,
                    "formula": metric_def.formula,
                })
                
                # Store in results dict for easy access
                self.results[metric_name] = value
                
            except Exception as e:
                print(f"⚠️  Error computing {metric_name}: {e}")
                results.append({
                    "metric_name": metric_name,
                    "display_name": metric_def.display_name,
                    "metric_type": metric_def.metric_type.value,
                    "value": np.nan,
                    "unit": metric_def.unit,
                    "owner": metric_def.owner,
                    "formula": metric_def.formula,
                })
        
        return pd.DataFrame(results)
    
    def compute_metric(self, metric_name: str) -> Any:
        """
        Compute a single metric.
        
        Args:
            metric_name: Name of metric to compute
            
        Returns:
            Metric value
        """
        if metric_name not in self.registry:
            raise ValueError(f"Unknown metric: {metric_name}")
        
        metric_def = self.registry[metric_name]
        user_kpis = self._get_user_kpis()
        
        return metric_def.compute(user_kpis)
    
    def compare_periods(
        self,
        period1_data: pd.DataFrame,
        period2_data: pd.DataFrame,
        metrics: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Compare KPI values between two periods.
        
        Args:
            period1_data: User-level KPI data for period 1 (baseline)
            period2_data: User-level KPI data for period 2 (comparison)
            metrics: List of metric names to compare (default: all)
            
        Returns:
            DataFrame with columns:
            - metric_name
            - period1_value
            - period2_value
            - absolute_change
            - percent_change
        """
        if metrics is None:
            metrics = list(self.registry.keys())
        
        comparisons = []
        
        for metric_name in metrics:
            if metric_name not in self.registry:
                continue
            
            metric_def = self.registry[metric_name]
            
            try:
                p1_value = metric_def.compute(period1_data)
                p2_value = metric_def.compute(period2_data)
                
                abs_change = p2_value - p1_value
                pct_change = (abs_change / p1_value) if p1_value != 0 else 0.0
                
                comparisons.append({
                    'metric_name': metric_name,
                    'display_name': metric_def.display_name,
                    'period1_value': p1_value,
                    'period2_value': p2_value,
                    'absolute_change': abs_change,
                    'percent_change': pct_change,
                    'unit': metric_def.unit,
                })
            except Exception as e:
                print(f"⚠️  Error comparing {metric_name}: {e}")
        
        return pd.DataFrame(comparisons)
    
    def get_north_star(self) -> Dict[str, Any]:
        """
        Get North Star metric with its components.
        
        Returns:
            Dict with North Star value and breakdown
        """
        # Find North Star metric
        north_star = None
        for metric_def in self.registry.values():
            if metric_def.metric_type == MetricType.NORTH_STAR:
                north_star = metric_def
                break
        
        if not north_star:
            raise ValueError("No North Star metric defined")
        
        # Compute North Star and its dependencies
        user_kpis = self._get_user_kpis()
        north_star_value = north_star.compute(user_kpis)
        
        components = {}
        for dep in north_star.dependencies:
            if dep in self.registry:
                components[dep] = self.registry[dep].compute(user_kpis)
        
        return {
            "metric": north_star.name,
            "value": north_star_value,
            "components": components,
            "formula": north_star.formula,
        }
    
    def _get_user_kpis(self) -> pd.DataFrame:
        """
        Execute SQL to get user-level KPIs.
        
        Returns:
            DataFrame with user-level metrics
        """
        # Create base_events table
        base_query = """
        WITH order_items_agg AS (
            SELECT
                order_id,
                COUNT(*) AS items_in_order,
                SUM(CAST(reordered AS INTEGER)) AS reordered_items_in_order,
                COUNT(DISTINCT product_id) AS unique_products_in_order
            FROM order_products
            GROUP BY order_id
        ),
        order_with_products AS (
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
                CASE 
                    WHEN oi.items_in_order > 0 
                    THEN CAST(oi.reordered_items_in_order AS DOUBLE) / oi.items_in_order
                    ELSE 0.0
                END AS order_reorder_rate,
                CASE WHEN oi.items_in_order <= 3 THEN 1 ELSE 0 END AS is_small_basket
            FROM orders o
            INNER JOIN order_items_agg oi ON o.order_id = oi.order_id
        )
        SELECT * FROM order_with_products
        """
        
        base_events = self.loader.execute_sql(base_query)
        
        # Now compute user-level aggregates
        user_kpi_query = """
        WITH base_orders AS (
            SELECT * FROM temp_base_events
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
            CASE 
                WHEN total_items > 0 
                THEN CAST(total_reordered_items AS DOUBLE) / total_items
                ELSE 0.0
            END AS reorder_rate,
            CASE 
                WHEN total_orders > 0 
                THEN CAST(small_basket_count AS DOUBLE) / total_orders
                ELSE 0.0
            END AS small_basket_share,
            avg_days_between_orders AS median_days_since_prior,
            max_order_number AS lifetime_orders,
            total_orders AS orders_per_customer
        FROM user_aggregates
        ORDER BY user_id
        """
        
        # Register pandas DataFrame with DuckDB so it can be queried
        self.loader.conn.register('temp_base_events', base_events)
        
        user_kpis = self.loader.execute_sql(user_kpi_query)
        
        return user_kpis
    
    def get_metric_report(self) -> str:
        """
        Generate a text report of all metrics.
        
        Returns:
            Formatted string report
        """
        if not self.results:
            self.compute_all_metrics()
        
        lines = []
        lines.append("=" * 70)
        lines.append("KPI METRIC REPORT")
        lines.append("=" * 70)
        
        # North Star
        lines.append("\n📊 NORTH STAR METRIC")
        lines.append("-" * 70)
        north_star_info = self.get_north_star()
        lines.append(f"  {north_star_info['metric'].upper()}: {north_star_info['value']:.2f}")
        lines.append(f"  Formula: {north_star_info['formula']}")
        lines.append("\n  Components:")
        for comp, val in north_star_info['components'].items():
            lines.append(f"    - {comp}: {val:.2f}")
        
        # Driver metrics
        lines.append("\n🎯 DRIVER METRICS")
        lines.append("-" * 70)
        for name, metric_def in self.registry.items():
            if metric_def.metric_type == MetricType.DRIVER and name in self.results:
                value = self.results[name]
                lines.append(f"  {metric_def.display_name}: {value:,.0f} {metric_def.unit}")
        
        # Guardrails
        lines.append("\n🛡️  GUARDRAIL METRICS")
        lines.append("-" * 70)
        for name, metric_def in self.registry.items():
            if metric_def.metric_type == MetricType.GUARDRAIL and name in self.results:
                value = self.results[name]
                if isinstance(value, float):
                    lines.append(f"  {metric_def.display_name}: {value:.2%}" if metric_def.unit == "rate" else f"  {metric_def.display_name}: {value:.1f} {metric_def.unit}")
                else:
                    lines.append(f"  {metric_def.display_name}: {value:,.0f} {metric_def.unit}")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
