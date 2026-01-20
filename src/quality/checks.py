"""
Data quality validation module.

Implements checks to ensure data integrity and metric validity.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class CheckSeverity(Enum):
    """Severity levels for quality check failures."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class QualityCheckResult:
    """Result of a quality check."""
    check_name: str
    passed: bool
    severity: CheckSeverity
    message: str
    details: Optional[Dict] = None


class DataQualityChecker:
    """
    Validates data quality and metric integrity.
    
    Performs checks for:
    - Null/missing values
    - Monotonic relationships
    - Value range validation
    - Outlier detection
    """
    
    def __init__(self, max_missing_rate: float = 0.05):
        """
        Initialize quality checker.
        
        Args:
            max_missing_rate: Maximum allowed missing rate (default 5%)
        """
        self.max_missing_rate = max_missing_rate
        self.results: List[QualityCheckResult] = []
        
    def run_all_checks(self, df: pd.DataFrame, metric_name: str = "dataset") -> List[QualityCheckResult]:
        """
        Run all quality checks on a dataset.
        
        Args:
            df: DataFrame to validate
            metric_name: Name for reporting
            
        Returns:
            List of check results
        """
        self.results = []
        
        # Basic checks
        self.check_null_values(df, metric_name)
        self.check_row_count(df, metric_name)
        self.check_numeric_ranges(df, metric_name)
        
        return self.results
    
    def check_null_values(self, df: pd.DataFrame, dataset_name: str) -> None:
        """Check for excessive null values in each column."""
        total_rows = len(df)
        
        for col in df.columns:
            null_count = df[col].isnull().sum()
            null_rate = null_count / total_rows if total_rows > 0 else 0
            
            if null_rate > self.max_missing_rate:
                self.results.append(QualityCheckResult(
                    check_name=f"null_check_{col}",
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message=f"Column '{col}' has {null_rate:.1%} missing values (threshold: {self.max_missing_rate:.1%})",
                    details={"column": col, "null_count": null_count, "null_rate": null_rate}
                ))
            else:
                self.results.append(QualityCheckResult(
                    check_name=f"null_check_{col}",
                    passed=True,
                    severity=CheckSeverity.INFO,
                    message=f"Column '{col}' null rate OK: {null_rate:.1%}",
                    details={"column": col, "null_count": null_count, "null_rate": null_rate}
                ))
    
    def check_row_count(self, df: pd.DataFrame, dataset_name: str, min_rows: int = 100) -> None:
        """Check if dataset has sufficient rows."""
        row_count = len(df)
        
        if row_count < min_rows:
            self.results.append(QualityCheckResult(
                check_name="row_count_check",
                passed=False,
                severity=CheckSeverity.ERROR,
                message=f"Dataset '{dataset_name}' has only {row_count} rows (minimum: {min_rows})",
                details={"row_count": row_count, "min_rows": min_rows}
            ))
        else:
            self.results.append(QualityCheckResult(
                check_name="row_count_check",
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"Dataset '{dataset_name}' has sufficient rows: {row_count:,}",
                details={"row_count": row_count}
            ))
    
    def check_numeric_ranges(self, df: pd.DataFrame, dataset_name: str) -> None:
        """Check numeric columns for invalid values (negative where should be positive, etc.)."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            # Check for negative values in count/amount columns
            if any(keyword in col.lower() for keyword in ['count', 'total', 'orders', 'items', 'customers']):
                negative_count = (df[col] < 0).sum()
                
                if negative_count > 0:
                    self.results.append(QualityCheckResult(
                        check_name=f"range_check_{col}",
                        passed=False,
                        severity=CheckSeverity.ERROR,
                        message=f"Column '{col}' has {negative_count} negative values (should be >= 0)",
                        details={"column": col, "negative_count": negative_count}
                    ))
                else:
                    self.results.append(QualityCheckResult(
                        check_name=f"range_check_{col}",
                        passed=True,
                        severity=CheckSeverity.INFO,
                        message=f"Column '{col}' range OK (all values >= 0)",
                        details={"column": col}
                    ))
            
            # Check for rates (should be between 0 and 1)
            if 'rate' in col.lower() or 'share' in col.lower():
                out_of_range = ((df[col] < 0) | (df[col] > 1)).sum()
                
                if out_of_range > 0:
                    self.results.append(QualityCheckResult(
                        check_name=f"range_check_{col}",
                        passed=False,
                        severity=CheckSeverity.WARNING,
                        message=f"Column '{col}' has {out_of_range} values outside [0, 1]",
                        details={"column": col, "out_of_range_count": out_of_range}
                    ))
    
    def check_monotonic_relationship(
        self, 
        df: pd.DataFrame, 
        col1: str, 
        col2: str, 
        relationship: str
    ) -> QualityCheckResult:
        """
        Check if two columns maintain a monotonic relationship.
        
        Args:
            df: DataFrame containing both columns
            col1: First column name
            col2: Second column name
            relationship: Expected relationship (">=" or "<=")
            
        Returns:
            Check result
        """
        if relationship == ">=":
            violations = (df[col1] < df[col2]).sum()
            expected = f"{col1} >= {col2}"
        elif relationship == "<=":
            violations = (df[col1] > df[col2]).sum()
            expected = f"{col1} <= {col2}"
        else:
            raise ValueError(f"Unknown relationship: {relationship}")
        
        total_rows = len(df)
        violation_rate = violations / total_rows if total_rows > 0 else 0
        
        passed = violations == 0
        
        return QualityCheckResult(
            check_name=f"monotonic_{col1}_{col2}",
            passed=passed,
            severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
            message=f"Monotonic check: {expected} - {violations:,} violations ({violation_rate:.1%})",
            details={
                "col1": col1,
                "col2": col2,
                "relationship": relationship,
                "violations": violations,
                "violation_rate": violation_rate
            }
        )
    
    def detect_outliers(
        self, 
        series: pd.Series, 
        method: str = "zscore", 
        threshold: float = 3.0
    ) -> Tuple[pd.Series, pd.DataFrame]:
        """
        Detect outliers in a numeric series.
        
        Args:
            series: Data to check
            method: Detection method ("zscore" or "iqr")
            threshold: Threshold for outlier detection
            
        Returns:
            Tuple of (boolean mask of outliers, outlier summary DataFrame)
        """
        if method == "zscore":
            z_scores = np.abs((series - series.mean()) / series.std())
            outliers = z_scores > threshold
            
        elif method == "iqr":
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            outliers = (series < Q1 - threshold * IQR) | (series > Q3 + threshold * IQR)
            
        else:
            raise ValueError(f"Unknown outlier detection method: {method}")
        
        # Create summary
        outlier_summary = pd.DataFrame({
            'value': series[outliers],
            'index': series[outliers].index
        })
        
        return outliers, outlier_summary
    
    def get_summary_report(self) -> str:
        """
        Get formatted summary of all check results.
        
        Returns:
            String report
        """
        if not self.results:
            return "No quality checks run yet."
        
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("DATA QUALITY CHECK SUMMARY")
        lines.append("=" * 70)
        
        # Count by severity
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        errors = sum(1 for r in self.results if r.severity == CheckSeverity.ERROR and not r.passed)
        warnings = sum(1 for r in self.results if r.severity == CheckSeverity.WARNING and not r.passed)
        
        lines.append(f"\nTotal Checks: {total}")
        lines.append(f"  ✓ Passed: {passed}")
        lines.append(f"  ✗ Failed: {failed}")
        lines.append(f"    - Errors: {errors}")
        lines.append(f"    - Warnings: {warnings}")
        
        # List failures
        if failed > 0:
            lines.append("\n⚠️  FAILED CHECKS:")
            lines.append("-" * 70)
            for result in self.results:
                if not result.passed:
                    icon = "❌" if result.severity == CheckSeverity.ERROR else "⚠️"
                    lines.append(f"  {icon} {result.message}")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
