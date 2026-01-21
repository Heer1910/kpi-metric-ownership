"""
Data quality validation with dataset contracts and reporting.

Production features:
- Dataset contracts (required columns, min row counts)
- Fail vs warn severity levels
- Markdown quality report generation
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime


class CheckSeverity(Enum):
    """Severity levels for quality check failures."""
    INFO = "info"
    WARNING = "warning"  # Warn but continue
    ERROR = "error"  # Fail execution


@dataclass
class QualityCheckResult:
    """Result of a quality check."""
    check_name: str
    passed: bool
    severity: CheckSeverity
    message: str
    details: Optional[Dict] = None


@dataclass
class DatasetContract:
    """Contract defining expected dataset structure and quality."""
    name: str
    required_columns: Set[str]
    min_row_count: int
    max_missing_rate: float = 0.05
    expected_ranges: Optional[Dict[str, Tuple[float, float]]] = None


# Dataset contracts for each table
DATASET_CONTRACTS = {
    "orders": DatasetContract(
        name="orders",
        required_columns={"order_id", "user_id", "order_number"},
        min_row_count=1_000_000,  # Expect at least 1M orders
        max_missing_rate=0.05,
        expected_ranges={
            "order_number": (1, 200),  # Users have 1-200 orders
            "order_dow": (0, 6),  # Day of week 0-6
           "order_hour_of_day": (0, 23),  # Hour 0-23
        }
    ),
    "order_products": DatasetContract(
        name="order_products",
        required_columns={"order_id", "product_id"},
        min_row_count=10_000_000,  # Expect at least 10M items
        max_missing_rate=0.0,  # No NULLs allowed
    ),
    "user_kpis": DatasetContract(
        name="user_kpis",
        required_columns={"user_id", "orders", "items", "reorder_rate"},
        min_row_count=100_000,  # Expect at least 100K users
        max_missing_rate=0.01,
        expected_ranges={
            "orders": (1, 200),
            "items": (1, 5000),
            "reorder_rate": (0, 1),
        }
    ),
    "base_events": DatasetContract(
        name="base_events",
        required_columns={"order_id", "user_id", "items_in_order"},
        min_row_count=1_000_000,
        max_missing_rate=0.05,
        expected_ranges={
            "items_in_order": (1, 200),
            "order_reorder_rate": (0, 1),
        }
    ),
}


class DataQualityChecker:
    """
    Validates data quality with contracts and generates reports.
    """
    
    def __init__(self):
        """Initialize quality checker."""
        self.results: List[QualityCheckResult] = []
        
    def validate_dataset(
        self, 
        df: pd.DataFrame, 
        dataset_name: str,
        contract: Optional[DatasetContract] = None
    ) -> List[QualityCheckResult]:
        """
        Validate dataset against contract.
        
        Args:
            df: DataFrame to validate
            dataset_name: Name of dataset
            contract: Optional contract (uses default if available)
            
        Returns:
            List of check results
        """
        self.results = []
        
        # Get contract
        if contract is None and dataset_name in DATASET_CONTRACTS:
            contract = DATASET_CONTRACTS[dataset_name]
        
        # Run contract checks
        if contract:
            self._check_required_columns(df, contract)
            self._check_min_row_count(df, contract)
            self._check_null_rates(df, contract)
            self._check_value_ranges(df, contract)
        
        # General checks
        self._check_duplicates(df, dataset_name)
        
        return self.results
    
    def _check_required_columns(self, df: pd.DataFrame, contract: DatasetContract) -> None:
        """Check required columns exist."""
        missing_cols = contract.required_columns - set(df.columns)
        
        if missing_cols:
            self.results.append(QualityCheckResult(
                check_name="required_columns",
                passed=False,
                severity=CheckSeverity.ERROR,
                message=f"Missing required columns in {contract.name}",
                details={"missing_columns": list(missing_cols)}
            ))
        else:
            self.results.append(QualityCheckResult(
                check_name="required_columns",
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"All required columns present in {contract.name}",
                details={"column_count": len(df.columns)}
            ))
    
    def _check_min_row_count(self, df: pd.DataFrame, contract: DatasetContract) -> None:
        """Check minimum row count."""
        row_count = len(df)
        
        if row_count < contract.min_row_count:
            # Warn if under threshold
            self.results.append(QualityCheckResult(
                check_name="min_row_count",
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"{contract.name} has {row_count:,} rows, expected >={contract.min_row_count:,}",
                details={"actual": row_count, "expected": contract.min_row_count}
            ))
        else:
            self.results.append(QualityCheckResult(
                check_name="min_row_count",
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"{contract.name} has {row_count:,} rows (✓)",
                details={"row_count": row_count}
            ))
    
    def _check_null_rates(self, df: pd.DataFrame, contract: DatasetContract) -> None:
        """Check NULL rates per column."""
        total_rows = len(df)
        
        for col in contract.required_columns:
            if col not in df.columns:
                continue
            
            null_count = df[col].isnull().sum()
            null_rate = null_count / total_rows if total_rows > 0 else 0
            
            if null_rate > contract.max_missing_rate:
                self.results.append(QualityCheckResult(
                    check_name=f"null_rate_{col}",
                    passed=False,
                    severity=CheckSeverity.ERROR,
                    message=f"{col} has {null_rate:.1%} NULLs (max: {contract.max_missing_rate:.1%})",
                    details={"column": col, "null_rate": null_rate}
                ))
    
    def _check_value_ranges(self, df: pd.DataFrame, contract: DatasetContract) -> None:
        """Check value ranges."""
        if not contract.expected_ranges:
            return
        
        for col, (min_val, max_val) in contract.expected_ranges.items():
            if col not in df.columns:
                continue
            
            actual_min = df[col].min()
            actual_max = df[col].max()
            
            if actual_min < min_val or actual_max > max_val:
                self.results.append(QualityCheckResult(
                    check_name=f"range_{col}",
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message=f"{col} range [{actual_min:.2f}, {actual_max:.2f}] outside expected [{min_val}, {max_val}]",
                    details={"column": col, "actual_range": (actual_min, actual_max)}
                ))
    
    def _check_duplicates(self, df: pd.DataFrame, dataset_name: str) -> None:
        """Check for duplicate rows."""
        dup_count = df.duplicated().sum()
        
        if dup_count > 0:
            self.results.append(QualityCheckResult(
                check_name="duplicates",
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"Found {dup_count:,} duplicate rows in {dataset_name}",
                details={"duplicate_count": dup_count}
            ))
    
    def generate_report(self, output_path: Path) -> None:
        """
        Generate markdown quality report.
        
        Args:
            output_path: Path to save report (e.g., reports/data_quality_report.md)
        """
        lines = []
        lines.append("# Data Quality Report")
        lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"\n**Total Checks:** {len(self.results)}")
        
        # Summary stats
        passed = sum(1 for r in self.results if r.passed)
        errors = sum(1 for r in self.results if r.severity == CheckSeverity.ERROR and not r.passed)
        warnings = sum(1 for r in self.results if r.severity == CheckSeverity.WARNING and not r.passed)
        
        lines.append(f"\n## Summary\n")
        lines.append(f"- ✅ **Passed:** {passed}")
        lines.append(f"- ❌ **Errors:** {errors}")
        lines.append(f"- ⚠️  **Warnings:** {warnings}")
        
        # Group by severity
        errors_list = [r for r in self.results if r.severity == CheckSeverity.ERROR and not r.passed]
        warnings_list = [r for r in self.results if r.severity == CheckSeverity.WARNING and not r.passed]
        info_list = [r for r in self.results if r.passed and r.severity == CheckSeverity.INFO]
        
        # Errors section
        if errors_list:
            lines.append(f"\n## ❌ Errors (Fail)")
            lines.append("\n| Check | Message | Details |")
            lines.append("|-------|---------|---------|")
            for r in errors_list:
                details_str = str(r.details) if r.details else "-"
                lines.append(f"| `{r.check_name}` | {r.message} | {details_str} |")
        
        # Warnings section
        if warnings_list:
            lines.append(f"\n## ⚠️  Warnings (Non-blocking)")
            lines.append("\n| Check | Message | Details |")
            lines.append("|-------|---------|---------|")
            for r in warnings_list:
                details_str = str(r.details) if r.details else "-"
                lines.append(f"| `{r.check_name}` | {r.message} | {details_str} |")
        
        # Passed checks
        if info_list:
            lines.append(f"\n## ✅ Passed Checks")
            lines.append("\n| Check | Message |")
            lines.append("|-------|---------|")
            for r in info_list[:10]:  # Show first 10
                lines.append(f"| `{r.check_name}` | {r.message} |")
            
            if len(info_list) > 10:
                lines.append(f"\n_... and {len(info_list) - 10} more passed checks_")
        
        # Decision
        lines.append(f"\n## 🚦 Quality Gate Decision\n")
        if errors > 0:
            lines.append("**Status:** ❌ **FAIL** - Critical errors must be fixed")
            lines.append(f"\n{errors} error(s) detected. Execution should be blocked.")
        elif warnings > 0:
            lines.append("**Status:** ⚠️  **WARN** - Proceed with caution")
            lines.append(f"\n{warnings} warning(s) detected. Review recommended but not blocking.")
        else:
            lines.append("**Status:** ✅ **PASS** - All quality checks passed")
        
        # Write report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✓ Quality report saved: {output_path}")
    
    def has_errors(self) -> bool:
        """Check if any ERROR-level checks failed."""
        return any(
            r.severity == CheckSeverity.ERROR and not r.passed 
            for r in self.results
        )
