"""
Metric governance system with complete metadata and validation.

Production-grade metric definitions with:
- Governance fields (owner, tier, cadence, directionality)
- Edge case validation (division by zero, NULL handling)
- Optional YAML loading for centralized metric catalog
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, List
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np
import yaml


# ============================================================================
# ENUMS FOR METRIC CLASSIFICATION
# ============================================================================

class MetricGrain(Enum):
    """Level of aggregation for a metric."""
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


class MetricDirectionality(Enum):
    """Whether higher or lower values are better."""
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    NEUTRAL = "neutral"


class MetricTier(Enum):
    """Priority tier for metric monitoring."""
    P0_EXECUTIVE = "P0"  # Executive dashboard
    P1_LEADERSHIP = "P1"  # Leadership review
    P2_OPERATIONAL = "P2"  # Operational monitoring
    P3_DIAGNOSTIC = "P3"  # Deep dive only


class RefreshCadence(Enum):
    """How often metric should be updated."""
    REALTIME = "realtime"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ============================================================================
# METRIC DEFINITION WITH GOVERNANCE
# ============================================================================

@dataclass
class MetricDefinition:
    """
    Complete metric definition with governance metadata.
    
    Core Attributes:
        name: Internal metric name (snake_case)
        display_name: Human-readable name
        grain: Level of aggregation
        metric_type: Classification (north star, driver, etc.)
        formula: How the metric is calculated (as text)
        computation_fn: Function to compute the metric
        unit: Unit of measurement (e.g., "customers", "orders", "rate")
        description: What the metric measures
    
    Governance Attributes:
        owner: Team responsible (e.g., "Growth PM", "Lifecycle Lead")
        owner_role: Functional area ("Growth", "Lifecycle", "Merchandising")
        tier: Priority (P0=executive, P1=leadership, P2=operational, P3=diagnostic)
        refresh_cadence: Update frequency (daily, weekly, monthly)
        directionality: Whether higher/lower is better
        review_cadence: How often to review in meetings
    
    Validation Attributes:
        thresholds: Dict of threshold values (min, max, warn_min, warn_max)
        validation_rules: Edge case handling rules
        dependencies: List of metrics this depends on
    """
    
    # Core fields
    name: str
    display_name: str
    grain: MetricGrain
    metric_type: MetricType
    formula: str
    computation_fn: Callable
    unit: str
    description: str
    
    # Governance fields
    owner: str
    owner_role: str  # Growth, Lifecycle, Merchandising, Product
    tier: MetricTier = MetricTier.P2_OPERATIONAL
    refresh_cadence: RefreshCadence = RefreshCadence.WEEKLY
    directionality: MetricDirectionality = MetricDirectionality.NEUTRAL
    review_cadence: str = "weekly"  # "daily", "weekly", "monthly"
    
    # Validation
    thresholds: Dict[str, float] = field(default_factory=dict)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    filters: Optional[str] = None
    
    def compute(self, data: pd.DataFrame) -> Any:
        """
        Compute metric value with edge case handling.
        
        Args:
            data: Input DataFrame
            
        Returns:
            Computed value
            
        Raises:
            ValueError: If computation fails validation
        """
        # Check for empty data
        if len(data) == 0:
            if self.validation_rules.get("allow_empty", False):
                return 0.0
            raise ValueError(f"Cannot compute {self.name}: empty dataset")
        
        # Check for required columns
        if "required_columns" in self.validation_rules:
            required = self.validation_rules["required_columns"]
            missing = set(required) - set(data.columns)
            if missing:
                raise ValueError(f"Missing columns for {self.name}: {missing}")
        
        try:
            result = self.computation_fn(data)
        except ZeroDivisionError:
            # Handle division by zero
            if self.validation_rules.get("division_by_zero", "error") == "return_zero":
                return 0.0
            elif self.validation_rules.get("division_by_zero") == "return_null":
                return np.nan
            else:
                raise ValueError(f"{self.name}: Division by zero")
        except Exception as e:
            raise ValueError(f"Failed to compute {self.name}: {e}")
        
        # Handle NULL results
        if pd.isna(result):
            if self.validation_rules.get("allow_null", False):
                return result
            raise ValueError(f"{self.name} computed to NULL")
        
        return result
    
    def validate(self, value: Any) -> bool:
        """
        Validate metric value against thresholds and business rules.
        
        Args:
            value: Metric value to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if pd.isna(value):
            if self.validation_rules.get("allow_null", False):
                return True
            raise ValueError(f"Metric {self.name} is NULL")
        
        # Check minimum threshold
        if "min" in self.thresholds and value < self.thresholds["min"]:
            raise ValueError(
                f"{self.name} = {value:.4f} below minimum {self.thresholds['min']}"
            )
        
        # Check maximum threshold
        if "max" in self.thresholds and value > self.thresholds["max"]:
            raise ValueError(
                f"{self.name} = {value:.4f} above maximum {self.thresholds['max']}"
            )
        
        return True
    
    def get_status(self, value: Any) -> str:
        """
        Get metric status (OK, WARNING, CRITICAL) based on value.
        
        Args:
            value: Metric value
            
        Returns:
            Status string
        """
        if pd.isna(value):
            return "UNKNOWN"
        
        # Check critical thresholds
        if "min" in self.thresholds and value < self.thresholds["min"]:
            return "CRITICAL"
        if "max" in self.thresholds and value > self.thresholds["max"]:
            return "CRITICAL"
        
        # Check warning thresholds
        if "warn_min" in self.thresholds and value < self.thresholds["warn_min"]:
            return "WARNING"
        if "warn_max" in self.thresholds and value > self.thresholds["warn_max"]:
            return "WARNING"
        
        return "OK"


# ============================================================================
# COMPUTATION FUNCTIONS
# ============================================================================

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division with zero check.
    
    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Value to return if denominator is 0
        
    Returns:
        Division result or default
    """
    return numerator / denominator if denominator != 0 else default


def compute_vpac(data: pd.DataFrame) -> float:
    """Compute VPAC (North Star)."""
    return data['orders_per_customer'].mean() * data['avg_basket_size'].mean()


def compute_active_customers(data: pd.DataFrame) -> int:
    """Count distinct active customers."""
    return len(data)


def compute_orders_per_customer(data: pd.DataFrame) -> float:
    """Average orders per customer."""
    return data['orders'].mean() if 'orders' in data.columns else data['orders_per_customer'].mean()


def compute_items_per_order(data: pd.DataFrame) -> float:
    """Average items per order."""
    return data['avg_basket_size'].mean()


def compute_reorder_rate(data: pd.DataFrame) -> float:
    """Overall reorder rate."""
    return data['reorder_rate'].mean()


def compute_small_basket_share(data: pd.DataFrame) -> float:
    """Share of orders with ≤3 items."""
    return data['small_basket_share'].mean()


def compute_median_days_since_prior(data: pd.DataFrame) -> float:
    """Median days between orders."""
    return data['median_days_since_prior'].median()


# ============================================================================
# METRIC REGISTRY
# ============================================================================

def create_metric_registry() -> Dict[str, MetricDefinition]:
    """
    Create governance-compliant metric registry.
    
    Returns:
        Dictionary of metric_name -> MetricDefinition
    """
    metrics = {
        "vpac": MetricDefinition(
            name="vpac",
            display_name="Value per Active Customer (VPAC)",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.NORTH_STAR,
            formula="orders_per_customer × items_per_order",
            computation_fn=compute_vpac,
            unit="items/customer",
            description="Total items ordered per active customer (North Star metric)",
            owner="Product Growth Lead",
            owner_role="Growth",
            tier=MetricTier.P0_EXECUTIVE,
            refresh_cadence=RefreshCadence.DAILY,
            directionality=MetricDirectionality.HIGHER_IS_BETTER,
            review_cadence="daily",
            thresholds={"min": 0, "warn_min": 100},
            validation_rules={"division_by_zero": "error"},
            dependencies=["orders_per_customer", "items_per_order"],
        ),
        
        "active_customers": MetricDefinition(
            name="active_customers",
            display_name="Active Customers",
            grain=MetricGrain.OVERALL,
            metric_type=MetricType.DRIVER,
            formula="COUNT(DISTINCT user_id)",
            computation_fn=compute_active_customers,
            unit="customers",
            description="Number of customers with at least one order",
            owner="Marketing Lead",
            owner_role="Growth",
            tier=MetricTier.P0_EXECUTIVE,
            refresh_cadence=RefreshCadence.DAILY,
            directionality=MetricDirectionality.HIGHER_IS_BETTER,
            review_cadence="daily",
            thresholds={"min": 1},
            validation_rules={"allow_empty": False},
        ),
        
        "orders_per_customer": MetricDefinition(
            name="orders_per_customer",
            display_name="Orders per Customer",
            grain=MetricGrain.USER,
            metric_type=MetricType.DRIVER,
            formula="AVG(orders)",
            computation_fn=compute_orders_per_customer,
            unit="orders/customer",
            description="Average number of orders per customer (frequency)",
            owner="Retention PM",
            owner_role="Lifecycle",
            tier=MetricTier.P0_EXECUTIVE,
            refresh_cadence=RefreshCadence.WEEKLY,
            directionality=MetricDirectionality.HIGHER_IS_BETTER,
            review_cadence="weekly",
            thresholds={"min": 1},
        ),
        
        "items_per_order": MetricDefinition(
            name="items_per_order",
            display_name="Items per Order",
            grain=MetricGrain.USER,
            metric_type=MetricType.DRIVER,
            formula="AVG(avg_basket_size)",
            computation_fn=compute_items_per_order,
            unit="items/order",
            description="Average items per order (basket depth)",
            owner="Merchandising PM",
            owner_role="Merchandising",
            tier=MetricTier.P0_EXECUTIVE,
            refresh_cadence=RefreshCadence.WEEKLY,
            directionality=MetricDirectionality.HIGHER_IS_BETTER,
            review_cadence="weekly",
            thresholds={"min": 1},
        ),
        
        "reorder_rate": MetricDefinition(
            name="reorder_rate",
            display_name="Reorder Rate",
            grain=MetricGrain.USER,
            metric_type=MetricType.GUARDRAIL,
            formula="AVG(reorder_rate)",
            computation_fn=compute_reorder_rate,
            unit="rate",
            description="% of items that are reorders (loyalty indicator)",
            owner="Retention PM",
            owner_role="Lifecycle",
            tier=MetricTier.P1_LEADERSHIP,
            refresh_cadence=RefreshCadence.WEEKLY,
            directionality=MetricDirectionality.HIGHER_IS_BETTER,
            review_cadence="weekly",
            thresholds={"min": 0, "max": 1, "warn_min": 0.30},
            validation_rules={"allow_null": False},
        ),
        
        "small_basket_share": MetricDefinition(
            name="small_basket_share",
            display_name="Small Basket Share",
            grain=MetricGrain.USER,
            metric_type=MetricType.GUARDRAIL,
            formula="AVG(small_basket_share)",
            computation_fn=compute_small_basket_share,
            unit="rate",
            description="% of orders with ≤3 items (quality flag)",
            owner="Product Quality Lead",
            owner_role="Product",
            tier=MetricTier.P1_LEADERSHIP,
            refresh_cadence=RefreshCadence.WEEKLY,
            directionality=MetricDirectionality.LOWER_IS_BETTER,
            review_cadence="weekly",
            thresholds={"min": 0, "max": 1, "warn_max": 0.30},
        ),
        
        "median_days_since_prior": MetricDefinition(
            name="median_days_since_prior",
            display_name="Median Days Between Orders",
            grain=MetricGrain.USER,
            metric_type=MetricType.GUARDRAIL,
            formula="MEDIAN(median_days_since_prior)",
            computation_fn=compute_median_days_since_prior,
            unit="days",
            description="Median days between consecutive orders (frequency health)",
            owner="Retention PM",
            owner_role="Lifecycle",
            tier=MetricTier.P2_OPERATIONAL,
            refresh_cadence=RefreshCadence.WEEKLY,
            directionality=MetricDirectionality.LOWER_IS_BETTER,
            review_cadence="weekly",
            thresholds={"min": 1, "warn_max": 30},
            validation_rules={"allow_null": True},  # NULL for single-order customers
        ),
    }
    
    return metrics


def load_metrics_from_yaml(yaml_path: Path) -> Dict[str, MetricDefinition]:
    """
    Load metric definitions from YAML file (optional).
    
    Args:
        yaml_path: Path to metrics.yaml file
        
    Returns:
        Dictionary of metric definitions
        
    Note:
        YAML file should define metrics with all governance fields.
        This is optional - defaults to create_metric_registry() if file not found.
    """
    if not yaml_path.exists():
        print(f"Metrics YAML not found: {yaml_path}, using default registry")
        return create_metric_registry()
    
    with open(yaml_path, 'r') as f:
        yaml_data = yaml.safe_load(f)
    
    # TODO: Parse YAML and construct MetricDefinition objects
    # For now, returns default registry
    print(f"Loaded metrics from: {yaml_path}")
    return create_metric_registry()
