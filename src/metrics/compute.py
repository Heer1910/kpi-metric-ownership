"""
Metric computation engine with layered output and caching.

Production features:
- Executive vs diagnostic metric layers
- Single metric computation with caching
- Strict grain enforcement
- Result validation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from functools import lru_cache

from .definitions import (
    MetricDefinition, 
    create_metric_registry, 
    MetricType, 
    MetricGrain,
    MetricTier
)
from ..io.data_loader import InstacartDataLoader


class MetricEngine:
    """
    Production metric computation engine with layers and caching.
    
    Features:
    - Two-layer output (executive summary + diagnostic)
    - Single metric computation with caching
    - Grain enforcement (user-level vs overall)
    - Result validation and error handling
    """
    
    def __init__(self, data_loader: InstacartDataLoader):
        """
        Initialize metric engine.
        
        Args:
            data_loader: Connected data loader instance
        """
        self.loader = data_loader
        self.registry = create_metric_registry()
        
        # Caching
        self._cache: Dict[str, Any] = {}
        self._user_kpis_cache: Optional[pd.DataFrame] = None
        
    def compute_all_metrics(self) -> pd.DataFrame:
        """
        Compute all metrics (backward compatible).
        
        Returns:
            DataFrame with all metrics
        """
        exec_summary, diagnostic = self.compute_metrics_by_layer()
        
        # Combine for backward compatibility
        all_metrics = pd.concat([exec_summary, diagnostic], ignore_index=True)
        return all_metrics
    
    def compute_metrics_by_layer(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Compute metrics in two layers for different audiences.
        
        Returns:
            Tuple of (executive_summary, diagnostic_metrics)
            
        Executive Summary:
            - North Star + top drivers (P0/P1 metrics)
            - For leadership and executive dashboards
            
        Diagnostic Metrics:
            - Guardrails + operational metrics (P2/P3)
            - For deep dives and operational monitoring
        """
        # Get user-level data once
        user_kpis = self._get_user_kpis()
        
        executive_results = []
        diagnostic_results = []
        
        for metric_name, metric_def in self.registry.items():
            try:
                # Enforce grain
                self._enforce_grain(metric_def, user_kpis)
                
                # Check cache first
                if metric_name in self._cache:
                    value = self._cache[metric_name]
                else:
                    value = metric_def.compute(user_kpis)
                    self._cache[metric_name] = value
                
                # Validate
                metric_def.validate(value)
                
                # Build result record
                result = {
                    "metric_name": metric_name,
                    "display_name": metric_def.display_name,
                    "metric_type": metric_def.metric_type.value,
                    "tier": metric_def.tier.value,
                    "value": value,
                    "unit": metric_def.unit,
                    "owner": metric_def.owner,
                    "owner_role": metric_def.owner_role,
                    "formula": metric_def.formula,
                    "directionality": metric_def.directionality.value,
                    "status": metric_def.get_status(value),
                }
                
                # Route to appropriate layer
                if metric_def.tier in [MetricTier.P0_EXECUTIVE, MetricTier.P1_LEADERSHIP]:
                    executive_results.append(result)
                else:
                    diagnostic_results.append(result)
                    
            except Exception as e:
                print(f"⚠️  Error computing {metric_name}: {e}")
                
                # Add NULL result
                result = {
                    "metric_name": metric_name,
                    "display_name": metric_def.display_name,
                    "metric_type": metric_def.metric_type.value,
                    "tier": metric_def.tier.value,
                    "value": np.nan,
                    "unit": metric_def.unit,
                    "owner": metric_def.owner,
                    "owner_role": metric_def.owner_role,
                    "formula": metric_def.formula,
                    "directionality": metric_def.directionality.value,
                    "status": "ERROR",
                }
                
                # Route errors to diagnostic layer
                diagnostic_results.append(result)
        
        executive_df = pd.DataFrame(executive_results)
        diagnostic_df = pd.DataFrame(diagnostic_results)
        
        return executive_df, diagnostic_df
    
    def compute(self, metric_name: str, use_cache: bool = True) -> Any:
        """
        Compute a single metric with optional caching.
        
        Args:
            metric_name: Name of metric to compute
            use_cache: If True, return cached value if available
            
        Returns:
            Metric value
            
        Raises:
            ValueError: If metric doesn't exist or grain mismatch
        """
        if metric_name not in self.registry:
            raise ValueError(
                f"Unknown metric: {metric_name}. "
                f"Available: {list(self.registry.keys())}"
            )
        
        # Check cache
        if use_cache and metric_name in self._cache:
            return self._cache[metric_name]
        
        metric_def = self.registry[metric_name]
        user_kpis = self._get_user_kpis()
        
        # Enforce grain
        self._enforce_grain(metric_def, user_kpis)
        
        # Compute
        value = metric_def.compute(user_kpis)
        
        # Validate
        metric_def.validate(value)
        
        # Cache result
        self._cache[metric_name] = value
        
        return value
    
    def clear_cache(self) -> None:
        """Clear metric computation cache."""
        self._cache.clear()
        self._user_kpis_cache = None
        print("✓ Cache cleared")
    
    def get_cached_value(self, metric_name: str) -> Optional[Any]:
        """
        Get cached metric value without recomputation.
        
        Args:
            metric_name: Metric to retrieve
            
        Returns:
            Cached value or None if not cached
        """
        return self._cache.get(metric_name)
    
    def _enforce_grain(self, metric_def: MetricDefinition, data: pd.DataFrame) -> None:
        """
        Enforce that data grain matches metric grain.
        
        Args:
            metric_def: Metric definition
            data: Input data
            
        Raises:
            ValueError: If grain mismatch detected
        """
        expected_grain = metric_def.grain
        
        # Check if data has user_id column (indicates user-level grain)
        has_user_id = 'user_id' in data.columns
        
        if expected_grain == MetricGrain.USER and not has_user_id:
            raise ValueError(
                f"Metric {metric_def.name} expects USER grain but data lacks user_id. "
                f"Cannot compute user-level metrics on aggregated data."
            )
        
        if expected_grain == MetricGrain.ORDER:
            # Order-level metrics need order_id
            if 'order_id' not in data.columns:
                raise ValueError(
                    f"Metric {metric_def.name} expects ORDER grain but data lacks order_id"
                )
        
        # OVERALL grain can work with any data
        # Just validate we have at least one row
        if expected_grain == MetricGrain.OVERALL and len(data) == 0:
            raise ValueError(
                f"Metric {metric_def.name} expects OVERALL grain but data is empty"
            )
    
    def _get_user_kpis(self) -> pd.DataFrame:
        """
        Get user-level KPI data with caching.
        
        Runs prerequisite SQL queries if tables don't exist.
        
        Returns:
            DataFrame with user-level metrics
        """
        if self._user_kpis_cache is not None:
            return self._user_kpis_cache
        
        sql_dir = Path(__file__).parent.parent.parent / "sql"
        
        # Check if base_events table exists
        try:
            self.loader.conn.execute("SELECT COUNT(*) FROM base_events").fetchone()
        except:
            # Need to create base_events first
            base_events_sql = sql_dir / "base_events.sql"
            if base_events_sql.exists():
                with open(base_events_sql, 'r') as f:
                    query = f.read()
                self.loader.conn.execute(query)
        
        # Now load user KPIs
        sql_file = sql_dir / "kpi_user_aggregates.sql"
        
        if not sql_file.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file}")
        
        with open(sql_file, 'r') as f:
            query = f.read()
        
        # Execute query
        user_kpis = self.loader.execute_sql(query)
        
        # Cache result
        self._user_kpis_cache = user_kpis
        
        return user_kpis
    
    def get_north_star(self) -> Dict[str, Any]:
        """
        Get North Star metric with components.
        
        Returns:
            Dict with North Star value, formula, and components
        """
        # Get VPAC metric
        vpac_metric = self.registry["vpac"]
        vpac_value = self.compute("vpac")
        
        # Get components
        orders_per_customer = self.compute("orders_per_customer")
        items_per_order = self.compute("items_per_order")
        
        return {
            "metric": vpac_metric.display_name,
            "value": vpac_value,
            "formula": vpac_metric.formula,
            "components": {
                "orders_per_customer": orders_per_customer,
                "items_per_order": items_per_order,
            },
            "unit": vpac_metric.unit,
            "owner": vpac_metric.owner,
            "tier": vpac_metric.tier.value,
        }
    
    def get_executive_summary(self) -> pd.DataFrame:
        """
        Get only executive summary metrics (P0/P1).
        
        Returns:
            DataFrame with executive metrics only
        """
        exec_df, _ = self.compute_metrics_by_layer()
        return exec_df
    
    def get_diagnostic_metrics(self) -> pd.DataFrame:
        """
        Get only diagnostic metrics (P2/P3).
        
        Returns:
            DataFrame with diagnostic metrics only
        """
        _, diag_df = self.compute_metrics_by_layer()
        return diag_df
    
    def get_metrics_by_owner(self, owner_role: str) -> pd.DataFrame:
        """
        Get all metrics owned by a specific role.
        
        Args:
            owner_role: Role to filter by (Growth, Lifecycle, etc.)
            
        Returns:
            DataFrame with metrics for that role
        """
        all_metrics = self.compute_all_metrics()
        return all_metrics[all_metrics['owner_role'] == owner_role]
    
    def get_metric_report(self) -> str:
        """
        Generate formatted text report of all metrics.
        
        Returns:
            Formatted string report
        """
        exec_df, diag_df = self.compute_metrics_by_layer()
        
        lines = []
        lines.append("=" * 70)
        lines.append("METRIC COMPUTATION REPORT")
        lines.append("=" * 70)
        
        # Executive Summary
        lines.append("\n📊 EXECUTIVE SUMMARY (P0/P1 Metrics)")
        lines.append("-" * 70)
        for _, row in exec_df.iterrows():
            value_str = self._format_value(row['value'], row['unit'])
            status = row.get('status', 'OK')
            status_icon = "✓" if status == "OK" else ("⚠️" if status == "WARNING" else "❌")
            lines.append(
                f"{status_icon} {row['display_name']}: {value_str} "
                f"[{row['owner_role']}]"
            )
        
        # Diagnostic Metrics
        if len(diag_df) > 0:
            lines.append("\n🔍 DIAGNOSTIC METRICS (P2/P3)")
            lines.append("-" * 70)
            for _, row in diag_df.iterrows():
                value_str = self._format_value(row['value'], row['unit'])
                lines.append(
                    f"  {row['display_name']}: {value_str} [{row['owner_role']}]"
                )
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    def _format_value(self, value: Any, unit: str) -> str:
        """Format metric value for display."""
        if pd.isna(value):
            return "NULL"
        
        if unit == "rate":
            return f"{value:.1%}"
        elif unit in ["customers", "orders", "items"]:
            return f"{value:,.0f}"
        else:
            return f"{value:.2f}"
    
    def compare_periods(
        self, 
        period1_data: pd.DataFrame, 
        period2_data: pd.DataFrame,
        metric_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Compare metrics between two periods.
        
        Args:
            period1_data: User KPIs for period 1
            period2_data: User KPIs for period 2
            metric_name: Optional specific metric to compare
            
        Returns:
            DataFrame with period comparison
        """
        metrics_to_compare = [metric_name] if metric_name else list(self.registry.keys())
        
        results = []
        for name in metrics_to_compare:
            metric_def = self.registry[name]
            
            try:
                # Compute for both periods
                p1_value = metric_def.compute(period1_data)
                p2_value = metric_def.compute(period2_data)
                
                # Calculate change
                abs_change = p2_value - p1_value
                pct_change = (abs_change / p1_value) if p1_value != 0 else 0
                
                results.append({
                    "metric": metric_def.display_name,
                    "period_1": p1_value,
                    "period_2": p2_value,
                    "absolute_change": abs_change,
                    "percent_change": pct_change,
                    "unit": metric_def.unit,
                })
            except Exception as e:
                print(f"⚠️  Error comparing {name}: {e}")
        
        return pd.DataFrame(results)
