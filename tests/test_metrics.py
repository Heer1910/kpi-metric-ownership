"""
Unit tests for metric definitions and computation.
"""

import pytest
import pandas as pd
import numpy as np
from src.metrics.definitions import (
    MetricDefinition,
    MetricGrain,
    MetricType,
    create_metric_registry,
    compute_vpac,
    compute_orders_per_customer,
    compute_items_per_order,
)


class TestMetricDefinitions:
    """Test metric definition dataclass and registry."""
    
    def test_metric_registry_creation(self):
        """Test that metric registry is created with all expected metrics."""
        registry = create_metric_registry()
        
        # Check that key metrics exist
        assert 'vpac' in registry
        assert 'orders_per_customer' in registry
        assert 'items_per_order' in registry
        assert 'reorder_rate' in registry
        
        # Check types
        assert registry['vpac'].metric_type == MetricType.NORTH_STAR
        assert registry['orders_per_customer'].metric_type == MetricType.DRIVER
    
    def test_metric_validation(self):
        """Test metric value validation."""
        registry = create_metric_registry()
        vpac_metric = registry['vpac']
        
        # Should pass for positive value
        assert vpac_metric.validate(10.5) == True
        
        # Should fail for negative value (below threshold)
        with pytest.raises(ValueError):
            vpac_metric.validate(-1.0)
        
        # Should fail for null
        with pytest.raises(ValueError):
            vpac_metric.validate(np.nan)


class TestMetricComputation:
    """Test metric computation functions."""
    
    @pytest.fixture
    def sample_user_kpis(self):
        """Create sample user-level KPI data for testing."""
        return pd.DataFrame({
            'user_id': [1, 2, 3, 4, 5],
            'orders': [10, 5, 2, 1, 15],
            'items': [100, 50, 20, 5, 200],
            'orders_per_customer': [10, 5, 2, 1, 15],
            'avg_basket_size': [10.0, 10.0, 10.0, 5.0, 13.33],
            'reorder_rate': [0.5, 0.4, 0.3, 0.2, 0.6],
            'small_basket_share': [0.1, 0.2, 0.5, 1.0, 0.0],
            'median_days_since_prior': [7.0, 14.0, 30.0, np.nan, 5.0],
        })
    
    def test_compute_orders_per_customer(self, sample_user_kpis):
        """Test orders per customer computation."""
        result = compute_orders_per_customer(sample_user_kpis)
        
        expected = sample_user_kpis['orders_per_customer'].mean()
        assert result == expected
        assert result > 0
    
    def test_compute_items_per_order(self, sample_user_kpis):
        """Test items per order computation."""
        result = compute_items_per_order(sample_user_kpis)
        
        expected = sample_user_kpis['avg_basket_size'].mean()
        assert abs(result - expected) < 0.01  # Allow small floating point error
        assert result > 0
    
    def test_compute_vpac(self, sample_user_kpis):
        """Test VPAC computation."""
        result = compute_vpac(sample_user_kpis)
        
        orders_per_cust = sample_user_kpis['orders_per_customer'].mean()
        items_per_order = sample_user_kpis['avg_basket_size'].mean()
        expected = orders_per_cust * items_per_order
        
        assert abs(result - expected) < 0.01
        assert result > 0
    
    def test_vpac_components_multiply_correctly(self, sample_user_kpis):
        """Test that VPAC = orders_per_customer × items_per_order."""
        vpac = compute_vpac(sample_user_kpis)
        orders_per_cust = compute_orders_per_customer(sample_user_kpis)
        items_per_order = compute_items_per_order(sample_user_kpis)
        
        expected_vpac = orders_per_cust * items_per_order
        
        assert abs(vpac - expected_vpac) < 0.01  # Should match within rounding


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
