"""
Edge case and robustness tests for metric computation.

Tests boundary conditions that might break in production:
- Empty datasets
- Single customer scenarios  
- Customers with no reorders
- Extreme values
"""

import pytest
import pandas as pd
import numpy as np
from src.metrics.definitions import (
    create_metric_registry,
    compute_vpac,
    compute_orders_per_customer,
    compute_items_per_order,
    compute_reorder_rate,
)


class TestEdgeCases:
    """Test metric behavior with unusual but valid data."""
    
    def test_single_customer_single_order(self):
        """Minimal valid dataset: 1 customer, 1 order."""
        data = pd.DataFrame({
            'user_id': [1],
            'orders': [1],
            'items': [5],
            'orders_per_customer': [1],
            'avg_basket_size': [5.0],
            'reorder_rate': [0.0],
            'small_basket_share': [1.0],
            'median_days_since_prior': [np.nan],
        })
        
        vpac = compute_vpac(data)
        assert vpac == 5.0  # 1 order × 5 items
        
        orders = compute_orders_per_customer(data)
        assert orders == 1.0
        
        items = compute_items_per_order(data)
        assert items == 5.0
    
    def test_no_reorders(self):
        """All customers are first-time purchasers."""
        data = pd.DataFrame({
            'user_id': [1, 2, 3],
            'orders': [1, 1, 1],
            'items': [10, 8, 12],
            'orders_per_customer': [1, 1, 1],
            'avg_basket_size': [10.0, 8.0, 12.0],
            'reorder_rate': [0.0, 0.0, 0.0],
            'small_basket_share': [0.0, 0.0, 0.0],
            'median_days_since_prior': [np.nan, np.nan, np.nan],
        })
        
        reorder_rate = compute_reorder_rate(data)
        assert reorder_rate == 0.0
    
    def test_all_reorders(self):
        """Every item is a reorder (ceiling case)."""
        data = pd.DataFrame({
            'user_id': [1, 2],
            'orders': [10, 15],
            'items': [100, 150],
            'orders_per_customer': [10, 15],
            'avg_basket_size': [10.0, 10.0],
            'reorder_rate': [1.0, 1.0],
            'small_basket_share': [0.0, 0.0],
            'median_days_since_prior': [7.0, 5.0],
        })
        
        reorder_rate = compute_reorder_rate(data)
        assert reorder_rate == 1.0
    
    def test_extreme_power_user(self):
        """One customer with 1000 orders (stress test)."""
        data = pd.DataFrame({
            'user_id': [1, 2],
            'orders': [1000, 5],
            'items': [10000, 50],
            'orders_per_customer': [1000, 5],
            'avg_basket_size': [10.0, 10.0],
            'reorder_rate': [0.9, 0.5],
            'small_basket_share': [0.01, 0.2],
            'median_days_since_prior': [1.0, 14.0],
        })
        
        vpac = compute_vpac(data)
        assert vpac > 0  # Should not overflow
        assert not np.isnan(vpac)
    
    def test_all_small_baskets(self):
        """Everyone orders ≤3 items (quality alarm)."""
        data = pd.DataFrame({
            'user_id': [1, 2, 3],
            'orders': [5, 8, 3],
            'items': [15, 24, 9],
            'orders_per_customer': [5, 8, 3],
            'avg_basket_size': [3.0, 3.0, 3.0],
            'reorder_rate': [0.3, 0.4, 0.2],
            'small_basket_share': [1.0, 1.0, 1.0],
            'median_days_since_prior': [10.0, 12.0, 8.0],
        })
        
        from src.metrics.definitions import compute_small_basket_share
        share = compute_small_basket_share(data)
        assert share == 1.0  # Should trigger alert in production
    
    def test_mixed_null_days_since_prior(self):
        """Some users have NULL days_since_prior (first orders)."""
        data = pd.DataFrame({
            'user_id': [1, 2, 3, 4],
            'orders': [1, 5, 10, 2],
            'items': [10, 50, 100, 20],
            'orders_per_customer': [1, 5, 10, 2],
            'avg_basket_size': [10.0, 10.0, 10.0, 10.0],
            'reorder_rate': [0.0, 0.5, 0.7, 0.3],
            'small_basket_share': [0.0, 0.2, 0.1, 0.5],
            'median_days_since_prior': [np.nan, 14.0, 7.0, np.nan],
        })
        
        from src.metrics.definitions import compute_median_days_since_prior
        median_days = compute_median_days_since_prior(data)
        
        # Should compute median of non-null values
        assert not np.isnan(median_days)
        assert median_days > 0


class TestMetricValidation:
    """Test threshold validation logic."""
    
    def test_vpac_threshold_min(self):
        """VPAC should reject negative values."""
        registry = create_metric_registry()
        vpac_metric = registry['vpac']
        
        with pytest.raises(ValueError):
            vpac_metric.validate(-1.0)
    
    def test_reorder_rate_range(self):
        """Reorder rate must be in [0, 1]."""
        registry = create_metric_registry()
        reorder_metric = registry['reorder_rate']
        
        # Valid
        assert reorder_metric.validate(0.5)
        assert reorder_metric.validate(0.0)
        assert reorder_metric.validate(1.0)
        
        # Invalid
        with pytest.raises(ValueError):
            reorder_metric.validate(1.5)
        
        with pytest.raises(ValueError):
            reorder_metric.validate(-0.1)
    
    def test_null_rejection(self):
        """Metrics should not accept NULL values."""
        registry = create_metric_registry()
        
        for metric in registry.values():
            with pytest.raises(ValueError):
                metric.validate(np.nan)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
