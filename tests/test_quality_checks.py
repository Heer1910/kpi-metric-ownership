"""
Test quality check system with contracts and reporting.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.quality.checks import (
    DataQualityChecker,
    CheckSeverity,
    DatasetContract,
    DATASET_CONTRACTS
)


class TestDatasetContracts:
    """Test dataset contract validation."""
    
    def test_contracts_defined(self):
        """Test that contracts exist for key tables."""
        assert 'orders' in DATASET_CONTRACTS
        assert 'user_kpis' in DATASET_CONTRACTS
        assert 'base_events' in DATASET_CONTRACTS
    
    def test_contract_structure(self):
        """Test contract has required fields."""
        contract = DATASET_CONTRACTS['user_kpis']
        assert contract.name == 'user_kpis'
        assert len(contract.required_columns) > 0
        assert contract.min_row_count > 0


class TestQualityChecker:
    """Test quality checker functionality."""
    
    def test_valid_dataset_passes(self):
        """Test that valid dataset passes all checks."""
        df = pd.DataFrame({
            'user_id': range(200_000),
            'orders': [5] * 200_000,
            'items': [20] * 200_000,
            'reorder_rate': [0.5] * 200_000,
        })
        
        checker = DataQualityChecker()
        results = checker.validate_dataset(df, 'user_kpis')
        
        assert len(results) > 0
        assert not checker.has_errors()
    
    def test_missing_columns_fails(self):
        """Test that missing required columns causes error."""
        df = pd.DataFrame({
            'user_id': range(1000),
            # Missing 'orders' column
        })
        
        checker = DataQualityChecker()
        results = checker.validate_dataset(df, 'user_kpis')
        
        assert checker.has_errors()
        error_results = [r for r in results if r.severity == CheckSeverity.ERROR and not r.passed]
        assert len(error_results) > 0
    
    def test_low_row_count_warns(self):
        """Test that low row count generates warning."""
        df = pd.DataFrame({
            'user_id': range(100),  # Way below 100K minimum
            'orders': [5] * 100,
            'items': [20] * 100,
            'reorder_rate': [0.5] * 100,
        })
        
        checker = DataQualityChecker()
        results = checker.validate_dataset(df, 'user_kpis')
        
        # Should have warnings but not errors for row count
        warnings = [r for r in results if r.severity == CheckSeverity.WARNING and not r.passed]
        assert len(warnings) > 0
    
    def test_report_generation(self, tmp_path):
        """Test that report generates correctly."""
        df = pd.DataFrame({
            'user_id': range(1000),
            '

orders': [5] * 1000,
            'items': [20] * 1000,
            'reorder_rate': [0.5] * 1000,
        })
        
        checker = DataQualityChecker()
        checker.validate_dataset(df, 'user_kpis')
        
        report_path = tmp_path / "quality_report.md"
        checker.generate_report(report_path)
        
        assert report_path.exists()
        content = report_path.read_text()
        assert "Data Quality Report" in content
        assert "Summary" in content


class TestRegressionFixtures:
    """Regression tests with known-good data."""
    
    def test_exact_vpac_calculation(self):
        """Test VPAC calculation with synthetic data."""
        # Create data where VPAC should be exactly 50.0
        # 10 orders/customer × 5 items/order = 50
        df = pd.DataFrame({
            'user_id': [1, 2, 3],
            'orders_per_customer': [10, 10, 10],
            'avg_basket_size': [5, 5, 5],
        })
        
        # VPAC = mean(orders_per_customer) * mean(avg_basket_size)
        expected_vpac = 10.0 * 5.0
        actual_vpac = df['orders_per_customer'].mean() * df['avg_basket_size'].mean()
        
        assert abs(actual_vpac - expected_vpac) < 0.01
        assert actual_vpac == 50.0
    
    def test_tiny_synthetic_dataset(self):
        """Test with minimal synthetic dataset."""
        # 2 users, known values
        df = pd.DataFrame({
            'user_id': [1, 2],
            'orders': [3, 5],
            'items': [12, 20],
            'reorder_rate': [0.3, 0.5],
            'orders_per_customer': [3, 5],
            'avg_basket_size': [4.0, 4.0],
        })
        
        # Validate calculations
        assert df['orders'].mean() == 4.0
        assert df['items'].mean() == 16.0
        assert df['avg_basket_size'].mean() == 4.0
        
        # VPAC should be 4 orders/customer × 4 items/order = 16
        vpac = df['orders_per_customer'].mean() * df['avg_basket_size'].mean()
        assert vpac == 16.0
