"""
Metric definitions and computation engine.

This module provides:
- MetricDefinition: A dataclass defining a metric's properties
- MetricEngine: Computes metrics from base data
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, List
from enum import Enum
import pandas as pd
import numpy as np


class MetricGrain(Enum):
    """Defines the level of aggregation for a metric."""
    USER = "user"
    ORDER = "order"
    OVERALL = "overall"
    CATEGORY = "category"


class MetricType(Enum):
    """Classification of metric purpose."""
    NORTH_STAR = "north_star"
    DRIVER = "driver"
    GUARDRAIL = "guardrail"
    DIAGNOSTIC = "diagnostic"


@dataclass
class MetricDefinition:
    """
    Defines a business metric with complete metadata.
    
    Attributes:
        name: Internal metric name (snake_case)
        display_name: Human-readable name
        grain: Level of aggregation
        metric_type: Classification (north star, driver, etc.)
        formula: How the metric is calculated (as text)
        computation_fn: Function to compute the metric
        unit: Unit of measurement (e.g., "customers", "orders", "rate")
        owner: Team responsible for this metric
        description: What the metric measures
        thresholds: Optional dict of threshold values
        filters: Optional filter criteria
        dependencies: List of metrics this depends on
    """
    
    name: str
    display_name: str
    grain: MetricGrain
    metric_type: MetricType
    formula: str
    computation_fn: Callable
    unit: str
    owner: str
    description: str
    thresholds: Dict[str, float] = field(default_factory=dict)
    filters: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    def compute(self, data: pd.DataFrame) -> Any:
        """
        Compute the metric value from input data.
        
        Args:
            data: Input DataFrame with necessary columns
            
        Returns:
            Computed metric value
        """
        return self.computation_fn(data)
    
    def validate(self, value: Any) -> bool:
        """
        Validate metric value against thresholds and business rules.
        
        Args:
            value: Metric value to validate
            
        Returns:
            True if valid, raises ValueError otherwise
        """
        if pd.isna(value):
            raise ValueError(f"Metric {self.name} is null")
        
        if "min" in self.thresholds and value < self.thresholds["min"]:
            raise ValueError(
                f"Metric {self.name} = {value} below minimum {self.thresholds['min']}"
            )
        
        if "max" in self.thresholds and value > self.thresholds["max"]:
            raise ValueError(
                f"Metric {self.name} = {value} above maximum {self.thresholds['max']}"
            )
        
        return True
    
    def __repr__(self) -> str:
        return f"MetricDefinition(name='{self.name}', type={self.metric_type.value}, grain={self.grain.value})"


# ============================================================================
# METRIC COMPUTATION FUNCTIONS
# ============================================================================

def compute_active_customers(df: pd.DataFrame) -> int:
    """Count distinct users."""
    return df['user_id'].nunique()


def compute_total_orders(df: pd.DataFrame) -> int:
    """Count total orders."""
    return int(df['orders'].sum())


def compute_total_items(df: pd.DataFrame) -> int:
    """Count total items ordered."""
    return int(df['items'].sum())


def compute_orders_per_customer(df: pd.DataFrame) -> float:
    """Average orders per active customer."""
    return df['orders_per_customer'].mean()


def compute_items_per_order(df: pd.DataFrame) -> float:
    """Average items per order."""
    return df['avg_basket_size'].mean()


def compute_vpac(df: pd.DataFrame) -> float:
    """
    North Star: Value per Active Customer.
    VPAC = Orders per Customer × Items per Order
    """
    orders_per_cust = compute_orders_per_customer(df)
    items_per_ord = compute_items_per_order(df)
    return orders_per_cust * items_per_ord


def compute_reorder_rate(df: pd.DataFrame) -> float:
    """Average reorder rate (% of items that are reorders)."""
    return df['reorder_rate'].mean()


def compute_small_basket_share(df: pd.DataFrame) -> float:
    """Share of orders with ≤3 items."""
    return df['small_basket_share'].mean()


def compute_median_days_since_prior(df: pd.DataFrame) -> float:
    """Median days between orders (frequency health)."""
    return df['median_days_since_prior'].median()


# ============================================================================
# METRIC REGISTRY
# ============================================================================

def create_metric_registry() -> Dict[str, MetricDefinition]:
    """
    Create the canonical registry of all KPIs.
    
    This is the single source of truth for metric definitions.
    """
    
    metrics = [
        # North Star
        MetricDefinition(
            name="vpac",
            display_name="Value per Active Customer (VPAC)",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.NORTH_STAR,
            formula="Orders per Customer × Items per Order",
            computation_fn=compute_vpac,
            unit="items/customer",
            owner="Product Growth",
            description="Value generated per active customer, combining purchase frequency and basket depth",
            thresholds={"min": 0},
            dependencies=["orders_per_customer", "items_per_order"],
        ),
        
        # Drivers
        MetricDefinition(
            name="active_customers",
            display_name="Active Customers",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.DRIVER,
            formula="COUNT(DISTINCT user_id)",
            computation_fn=compute_active_customers,
            unit="customers",
            owner="Marketing / Acquisition",
            description="Number of unique customers who placed at least one order",
            thresholds={"min": 1},
        ),
        
        MetricDefinition(
            name="orders_per_customer",
            display_name="Orders per Customer",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.DRIVER,
            formula="AVG(orders per user)",
            computation_fn=compute_orders_per_customer,
            unit="orders/customer",
            owner="Product / Retention",
            description="Average number of orders per active customer (purchase frequency)",
            thresholds={"min": 1.0},
        ),
        
        MetricDefinition(
            name="items_per_order",
            display_name="Items per Order",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.DRIVER,
            formula="AVG(items per order)",
            computation_fn=compute_items_per_order,
            unit="items/order",
            owner="Product / Merchandising",
            description="Average basket size (items per order)",
            thresholds={"min": 1.0},
        ),
        
        # Supporting KPIs
        MetricDefinition(
            name="total_orders",
            display_name="Total Orders",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.DIAGNOSTIC,
            formula="SUM(orders)",
            computation_fn=compute_total_orders,
            unit="orders",
            owner="Product Growth",
            description="Total number of orders placed",
            thresholds={"min": 0},
        ),
        
        MetricDefinition(
            name="total_items",
            display_name="Total Items",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.DIAGNOSTIC,
            formula="SUM(items)",
            computation_fn=compute_total_items,
            unit="items",
            owner="Product Growth",
            description="Total number of items ordered",
            thresholds={"min": 0},
        ),
        
        MetricDefinition(
            name="reorder_rate",
            display_name="Reorder Rate",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.DIAGNOSTIC,
            formula="Reordered Items / Total Items",
            computation_fn=compute_reorder_rate,
            unit="rate",
            owner="Product / Retention",
            description="Percentage of items that are reorders (loyalty indicator)",
            thresholds={"min": 0.0, "max": 1.0},
        ),
        
        # Guardrails
        MetricDefinition(
            name="small_basket_share",
            display_name="Small Basket Share",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.GUARDRAIL,
            formula="% of orders with ≤3 items",
            computation_fn=compute_small_basket_share,
            unit="rate",
            owner="Product Quality",
            description="Share of orders with ≤3 items (detects low-quality growth)",
            thresholds={"max": 0.3},  # Alert if >30% are small baskets
        ),
        
        MetricDefinition(
            name="median_days_since_prior",
            display_name="Median Days Between Orders",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.GUARDRAIL,
            formula="MEDIAN(days_since_prior_order)",
            computation_fn=compute_median_days_since_prior,
            unit="days",
            owner="Product / Retention",
            description="Median days between orders (frequency health check)",
            thresholds={"min": 1},
        ),
    ]
    
    return {m.name: m for m in metrics}
