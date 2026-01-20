"""
Unit tests for decomposition analysis.
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.decomposition import VPACDecomposer, DecompositionResult


class TestVPACDecomposer:
    """Test VPAC decomposition logic."""
    
    @pytest.fixture
    def decomposer(self):
        """Create decomposer instance."""
        return VPACDecomposer()
    
    def test_decompose_vpac_change_basic(self, decomposer):
        """Test basic VPAC decomposition."""
        period1 = {
            'vpac': 50.0,
            'orders_per_customer': 5.0,
            'items_per_order': 10.0
        }
        
        period2 = {
            'vpac': 60.0,
            'orders_per_customer': 6.0,
            'items_per_order': 10.0
        }
        
        result = decomposer.decompose_vpac_change(period1, period2)
        
        # Check total change
        assert result.total_change == 10.0
        assert result.percent_change == pytest.approx(0.2, abs=0.01)  # 20% increase
        
        # Check that decomposition is valid
        assert decomposer.validate_decomposition(result, tolerance=0.01)
    
    def test_decomposition_components_sum_to_total(self, decomposer):
        """Test that driver contributions sum to total change."""
        period1 = {
            'vpac': 100.0,
            'orders_per_customer': 10.0,
            'items_per_order': 10.0
        }
        
        period2 = {
            'vpac': 120.0,
            'orders_per_customer': 11.0,
            'items_per_order': 11.0  # Both increased
        }
        
        result = decomposer.decompose_vpac_change(period1, period2)
        
        # Sum of all contributions
        total_contrib = sum(result.driver_contributions.values())
        
        # Should equal total change within small tolerance
        assert abs(total_contrib - result.total_change) < 0.01
    
    def test_orders_only_change(self, decomposer):
        """Test decomposition when only orders per customer changes."""
        period1 = {
            'vpac': 50.0,
            'orders_per_customer': 5.0,
            'items_per_order': 10.0
        }
        
        period2 = {
            'vpac': 60.0,
            'orders_per_customer': 6.0,
            'items_per_order': 10.0  # No change
        }
        
        result = decomposer.decompose_vpac_change(period1, period2)
        
        # Orders per customer should have the dominant contribution
        orders_contrib = result.driver_contributions['orders_per_customer']
        items_contrib = result.driver_contributions['items_per_order']
        
        assert abs(orders_contrib) > abs(items_contrib)
    
    def test_items_only_change(self, decomposer):
        """Test decomposition when only items per order changes."""
        period1 = {
            'vpac': 50.0,
            'orders_per_customer': 5.0,
            'items_per_order': 10.0
        }
        
        period2 = {
            'vpac': 55.0,
            'orders_per_customer': 5.0,  # No change
            'items_per_order': 11.0
        }
        
        result = decomposer.decompose_vpac_change(period1, period2)
        
        # Items per order should have the dominant contribution
        orders_contrib = result.driver_contributions['orders_per_customer']
        items_contrib = result.driver_contributions['items_per_order']
        
        assert abs(items_contrib) > abs(orders_contrib)
    
    def test_validation_fails_on_bad_decomposition(self, decomposer):
        """Test that validation catches incorrect decompositions."""
        # Manually create a bad decomposition
        bad_result = DecompositionResult(
            metric_name='vpac',
            total_change=10.0,
            absolute_change=10.0,
            percent_change=0.1,
            driver_contributions={
                'orders_per_customer': 5.0,
                'items_per_order': 3.0,  # Only sums to 8.0, not 10.0
            },
            period_start='P1',
            period_end='P2'
        )
        
        with pytest.raises(ValueError):
            decomposer.validate_decomposition(bad_result, tolerance=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
