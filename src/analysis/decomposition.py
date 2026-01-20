"""
VPAC decomposition and driver attribution analysis.

This module provides tools to decompose the North Star metric (VPAC)
into its driver components and attribute changes over time.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DecompositionResult:
    """
    Results of a metric decomposition analysis.
    
    Attributes:
        metric_name: Name of the metric being decomposed
        total_change: Total change in the metric
        absolute_change: Absolute (additive) change
        percent_change: Percent change
        driver_contributions: Dict mapping driver names to their contribution
        period_start: Start period label
        period_end: End period label
    """
    metric_name: str
    total_change: float
    absolute_change: float
    percent_change: float
    driver_contributions: Dict[str, float]
    period_start: str
    period_end: str
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert decomposition to DataFrame for easy viewing."""
        rows = []
        
        for driver, contribution in self.driver_contributions.items():
            rows.append({
                'driver': driver,
                'contribution': contribution,
                'pct_of_total_change': contribution / self.total_change if self.total_change != 0 else 0
            })
        
        return pd.DataFrame(rows)


class VPACDecomposer:
    """
    Decomposes VPAC (Value per Active Customer) into driver components.
    
    VPAC = Orders per Customer × Items per Order
    
    This class can:
    1. Decompose changes between two periods
    2. Attribute changes to specific drivers
    3. Create waterfall visualizations
    """
    
    def __init__(self):
        """Initialize decomposer."""
        self.decomposition_history: List[DecompositionResult] = []
    
    def decompose_vpac_change(
        self,
        period1_metrics: Dict[str, float],
        period2_metrics: Dict[str, float],
        period1_label: str = "Period 1",
        period2_label: str = "Period 2"
    ) -> DecompositionResult:
        """
        Decompose VPAC change between two periods.
        
        VPAC = orders_per_customer × items_per_order
        
        Change decomposition:
        Δ VPAC = Δ(orders_per_customer × items_per_order)
               = orders_per_customer₂ × items_per_order₂ - orders_per_customer₁ × items_per_order₁
        
        Attribution (using midpoint method for symmetry):
        - Orders per customer effect: Δorders_per_customer × avg(items_per_order)
        - Items per order effect: avg(orders_per_customer) × Δitems_per_order
        
        Args:
            period1_metrics: Dict with keys 'vpac', 'orders_per_customer', 'items_per_order'
            period2_metrics: Same structure for period 2
            period1_label: Label for period 1
            period2_label: Label for period 2
            
        Returns:
            DecompositionResult with driver attributions
        """
        # Extract values
        vpac1 = period1_metrics['vpac']
        vpac2 = period2_metrics['vpac']
        
        orders_per_cust1 = period1_metrics['orders_per_customer']
        orders_per_cust2 = period2_metrics['orders_per_customer']
        
        items_per_order1 = period1_metrics['items_per_order']
        items_per_order2 = period2_metrics['items_per_order']
        
        # Total change
        total_change = vpac2 - vpac1
        percent_change = (vpac2 / vpac1 - 1) if vpac1 != 0 else 0
        
        # Driver changes (deltas)
        delta_orders_per_cust = orders_per_cust2 - orders_per_cust1
        delta_items_per_order = items_per_order2 - items_per_order1
        
        # Midpoint values (for symmetric attribution)
        avg_orders_per_cust = (orders_per_cust1 + orders_per_cust2) / 2
        avg_items_per_order = (items_per_order1 + items_per_order2) / 2
        
        # Attribution
        orders_per_cust_contribution = delta_orders_per_cust * avg_items_per_order
        items_per_order_contribution = avg_orders_per_cust * delta_items_per_order
        
        # Interaction effect (residual to ensure perfect decomposition)
        # VPAC change = base effects + interaction
        interaction = total_change - (orders_per_cust_contribution + items_per_order_contribution)
        
        driver_contributions = {
            'orders_per_customer': orders_per_cust_contribution,
            'items_per_order': items_per_order_contribution,
            'interaction': interaction
        }
        
        result = DecompositionResult(
            metric_name='vpac',
            total_change=total_change,
            absolute_change=total_change,
            percent_change=percent_change,
            driver_contributions=driver_contributions,
            period_start=period1_label,
            period_end=period2_label
        )
        
        self.decomposition_history.append(result)
        
        return result
    
    def validate_decomposition(self, result: DecompositionResult, tolerance: float = 0.01) -> bool:
        """
        Validate that decomposition components sum to total change.
        
        Args:
            result: Decomposition result to validate
            tolerance: Allowable error (fraction of total change)
            
        Returns:
            True if valid
            
        Raises:
            ValueError if decomposition doesn't sum correctly
        """
        component_sum = sum(result.driver_contributions.values())
        error = abs(component_sum - result.total_change)
        error_fraction = error / abs(result.total_change) if result.total_change != 0 else error
        
        if error_fraction > tolerance:
            raise ValueError(
                f"Decomposition validation failed: components sum to {component_sum:.4f}, "
                f"but total change is {result.total_change:.4f} (error: {error_fraction:.2%})"
            )
        
        return True
    
    def create_waterfall_data(self, result: DecompositionResult) -> pd.DataFrame:
        """
        Create data formatted for waterfall chart.
        
        Args:
            result: Decomposition result
            
        Returns:
            DataFrame with columns: step, value, cumulative
        """
        # Build waterfall steps
        steps = []
        cumulative = 0
        
        # Starting value (implied from total change and end value)
        # We'll show the contribution of each driver
        
        for driver, contribution in result.driver_contributions.items():
            steps.append({
                'step': driver,
                'value': contribution,
                'cumulative': cumulative + contribution,
                'type': 'driver'
            })
            cumulative += contribution
        
        # Add total
        steps.append({
            'step': 'Total Change',
            'value': result.total_change,
            'cumulative': result.total_change,
            'type': 'total'
        })
        
        return pd.DataFrame(steps)


class CustomerSegmentation:
    """
    Analyzes customer segments and their contribution to KPIs.
    """
    
    @staticmethod
    def segment_by_order_frequency(user_kpis: pd.DataFrame) -> pd.DataFrame:
        """
        Segment customers by order frequency.
        
        Segments:
        - One-time: 1 order
        - Occasional: 2-4 orders
        - Regular: 5-10 orders
        - Power users: 11+ orders
        
        Args:
            user_kpis: User-level KPI DataFrame with 'orders' column
            
        Returns:
            Segment summary DataFrame
        """
        # Define segments
        def assign_segment(orders):
            if orders == 1:
                return 'One-time'
            elif orders <= 4:
                return 'Occasional'
            elif orders <= 10:
                return 'Regular'
            else:
                return 'Power User'
        
        user_kpis['segment'] = user_kpis['orders'].apply(assign_segment)
        
        # Aggregate by segment
        segment_summary = user_kpis.groupby('segment').agg({
            'user_id': 'count',
            'orders': 'sum',
            'items': 'sum',
            'orders_per_customer': 'mean',
            'avg_basket_size': 'mean'
        }).rename(columns={'user_id': 'customer_count'})
        
        # Compute VPAC per segment
        segment_summary['vpac'] = (
            segment_summary['orders_per_customer'] * segment_summary['avg_basket_size']
        )
        
        # Compute share of total
        segment_summary['customer_share'] = (
            segment_summary['customer_count'] / segment_summary['customer_count'].sum()
        )
        segment_summary['order_share'] = (
            segment_summary['orders'] / segment_summary['orders'].sum()
        )
        segment_summary['item_share'] = (
            segment_summary['items'] / segment_summary['items'].sum()
        )
        
        # Sort by order frequency
        segment_order = ['One-time', 'Occasional', 'Regular', 'Power User']
        segment_summary = segment_summary.reindex(segment_order)
        
        return segment_summary
    
    @staticmethod
    def segment_by_basket_size(user_kpis: pd.DataFrame) -> pd.DataFrame:
        """
        Segment customers by average basket size.
        
        Args:
            user_kpis: User-level KPI DataFrame
            
        Returns:
            Segment summary DataFrame
        """
        # Define percentile-based segments
        basket_size_quartiles = user_kpis['avg_basket_size'].quantile([0.25, 0.5, 0.75])
        
        def assign_basket_segment(basket_size):
            if basket_size <= basket_size_quartiles[0.25]:
                return 'Small Basket'
            elif basket_size <= basket_size_quartiles[0.5]:
                return 'Medium Basket'
            elif basket_size <= basket_size_quartiles[0.75]:
                return 'Large Basket'
            else:
                return 'XL Basket'
        
        user_kpis['basket_segment'] = user_kpis['avg_basket_size'].apply(assign_basket_segment)
        
        segment_summary = user_kpis.groupby('basket_segment').agg({
            'user_id': 'count',
            'orders': 'sum',
            'items': 'sum',
            'avg_basket_size': 'mean',
            'orders_per_customer': 'mean'
        }).rename(columns={'user_id': 'customer_count'})
        
        segment_summary['vpac'] = (
            segment_summary['orders_per_customer'] * segment_summary['avg_basket_size']
        )
        
        return segment_summary
