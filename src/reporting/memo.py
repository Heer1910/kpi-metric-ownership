"""
Weekly Business Review memo generation.

Creates executive-ready WBR with:
- What changed (metrics with exact numbers)
- Why it changed (driver attribution)
- What we should do next (actions)
- Risks and guardrails
"""

import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from ..config import REPORTS_DIR
from ..analysis.decomposition import DecompositionResult


class KPIReportBuilder:
    """
    Builds structured KPI reports for weekly business reviews.
    
    Format follows real FAANG WBR structure:
    - Executive summary
    - What changed
    - Why it changed
    - What we should do next
    - Risks/guardrails
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize report builder.
        
        Args:
            output_dir: Directory to save reports (defaults to REPORTS_DIR)
        """
        self.output_dir = output_dir or REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_weekly_business_review(
        self,
        metrics_df: pd.DataFrame,
        north_star_info: Dict,
        decomposition: Optional[DecompositionResult] = None,
        key_insights: Optional[List[str]] = None,
        save: bool = True
    ) -> str:
        """
        Create a weekly business review memo.
        
        Args:
            metrics_df: DataFrame with all metrics
            north_star_info: Dict with North Star value and components
            decomposition: Optional decomposition result
            key_insights: Optional list of key insights
            save: Whether to save to file
            
        Returns:
            Markdown-formatted report string
        """
        lines = []
        
        # Header
        lines.append("# Weekly Business Review")
        lines.append(f"\n**Date:** {datetime.now().strftime('%B %d, %Y')}")
        lines.append(f"**Period:** Current Week")
        lines.append("\n---\n")
        
        # Section 1: What Changed
        lines.append("## 📊 What Changed")
        lines.append("\n### North Star Metric")
        lines.append(f"**VPAC (Value per Active Customer):** {north_star_info['value']:.2f} items/customer")
        
        # Add components with numbers
        lines.append("\n**Formula:** Orders/Customer × Items/Order")
        for comp_key, comp_val in north_star_info['components'].items():
            comp_name = comp_key.replace('_', ' ').title()
            lines.append(f"- {comp_name}: {comp_val:.2f}")
        
        # Key metrics table
        lines.append("\n### Key Metrics")
        lines.append("\n| Metric | Value | Owner | Status |")
        lines.append("|--------|-------|-------|--------|")
        
        for _, row in metrics_df.head(10).iterrows():
            value_str = self._format_metric_value(row['value'], row.get('unit', ''))
            status = row.get('status', 'OK')
            status_icon = "✅" if status == "OK" else ("⚠️" if status == "WARNING" else "❌")
            lines.append(
                f"| {row['display_name']} | **{value_str}** | "
                f"{row.get('owner_role', 'N/A')} | {status_icon} {status} |"
            )
        
        lines.append("\n")
        
        # Section 2: Why It Changed
        lines.append("## 🔍 Why It Changed")
        
        if decomposition:
            lines.append(f"\n**Total Change:** {decomposition.total_change:+.2f} ({decomposition.percent_change:+.1%})")
            lines.append("\n### Driver Attribution")
            
            # Sort drivers by absolute contribution
            sorted_drivers = sorted(
                decomposition.driver_contributions.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            
            for driver, contrib in sorted_drivers:
                if driver == 'interaction' and abs(contrib) < 0.01:
                    continue
                
                driver_name = driver.replace('_', ' ').title()
                pct_of_total = (contrib / decomposition.total_change * 100) if decomposition.total_change != 0 else 0
                
                # Add arrow and explanation
                arrow = "↑" if contrib > 0 else "↓"
                lines.append(f"- **{driver_name}** {arrow} contributed **{contrib:+.2f}** ({pct_of_total:+.0f}% of change)")
        else:
            lines.append("\n*Decomposition analysis not available - configure period comparison to enable.*")
        
        lines.append("\n")
        
        # Section 3: What We Should Do Next
        lines.append("## 🎯 What We Should Do Next")
        lines.append("\n### Recommended Actions")
        
        # Generate actions based on metrics
        actions = self._generate_actions(metrics_df, decomposition)
        for i, action in enumerate(actions, 1):
            lines.append(f"{i}. {action}")
        
        lines.append("\n")
        
        # Section 4: Risks / Guardrails
        lines.append("## ⚠️ Risks & Guardrails")
        
        # Check guardrail metrics
        guardrails = metrics_df[metrics_df['metric_type'] == 'guardrail'] if 'metric_type' in metrics_df.columns else pd.DataFrame()
        
        if len(guardrails) > 0:
            lines.append("\n### Guardrail Status")
            for _, row in guardrails.iterrows():
                status = row.get('status', 'OK')
                value_str = self._format_metric_value(row['value'], row.get('unit', ''))
                
                if status != "OK":
                    icon = "🔴" if status == "CRITICAL" else "🟡"
                    lines.append(f"- {icon} **{row['display_name']}**: {value_str} - {status}")
                else:
                    lines.append(f"- ✅ **{row['display_name']}**: {value_str} - Within bounds")
        
        # Additional risks
        lines.append("\n### Key Risks to Monitor")
        lines.append("- **Data Quality:** Ensure base tables refresh on schedule")
        lines.append("- **Seasonal Effects:** Consider day-of-week and time-of-day patterns")
        lines.append("- **Segment Shifts:** Monitor power user vs regular customer balance")
        
        lines.append("\n")
        
        # Insights section (if provided)
        if key_insights:
            lines.append("## 💡 Key Insights")
            for insight in key_insights:
                lines.append(f"- {insight}")
            lines.append("\n")
        
        # Footer
        lines.append("---")
        lines.append(f"\n*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("\n*All metrics link to definitions in `docs/metric_dictionary.md`*")
        
        report = "\n".join(lines)
        
        # Save to file
        if save:
            output_path = self.output_dir / "wbr.md"
            with open(output_path, 'w') as f:
                f.write(report)
            print(f"✓ Saved: {output_path}")
        
        return report
    
    def _format_metric_value(self, value: float, unit: str) -> str:
        """Format metric value based on unit."""
        if pd.isna(value):
            return "N/A"
        
        if unit == "rate":
            return f"{value:.1%}"
        elif unit in ["customers", "orders", "items"]:
            return f"{value:,.0f}"
        elif unit == "days":
            return f"{value:.1f} days"
        else:
            return f"{value:.2f}"
    
    def _generate_actions(
        self, 
        metrics_df: pd.DataFrame, 
        decomposition: Optional[DecompositionResult]
    ) -> List[str]:
        """
        Generate recommended actions based on metrics.
        
        Returns:
            List of action items with metric references
        """
        actions = []
        
        # Check for metric issues
        if 'status' in metrics_df.columns:
            warnings = metrics_df[metrics_df['status'] == 'WARNING']
            errors = metrics_df[metrics_df['status'] == 'CRITICAL']
            
            if len(errors) > 0:
                for _, row in errors.head(2).iterrows():
                    actions.append(
                        f"**URGENT:** Address {row['display_name']} "
                        f"({self._format_metric_value(row['value'], row.get('unit', ''))}) - "
                        f"assigned to {row.get('owner_role', 'team')}"
                    )
            
            if len(warnings) > 0:
                for _, row in warnings.head(2).iterrows():
                    actions.append(
                        f"Investigate {row['display_name']} trend - "
                        f"currently at {self._format_metric_value(row['value'], row.get('unit', ''))}"
                    )
        
        # Decomposition-based actions
        if decomposition:
            sorted_drivers = sorted(
                decomposition.driver_contributions.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            
            top_driver = sorted_drivers[0][0] if sorted_drivers else None
            
            if top_driver == 'orders_per_customer':
                actions.append(
                    "Focus retention efforts: Orders/Customer is the primary driver "
                    "(Contact Lifecycle team)"
                )
            elif top_driver == 'items_per_order':
                actions.append(
                    "Optimize basket depth: Items/Order is the primary driver "
                    "(Contact Merchandising team)"
                )
        
        # Default actions if none generated
        if not actions:
            actions = [
                "Continue monitoring all metrics for week-over-week trends",
                "Review segment-specific performance (power users vs occasional)",
                "Validate data quality checks pass (see `reports/data_quality_report.md`)",
            ]
        
        return actions
    
    def create_kpi_table(self, metrics_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create formatted KPI table for export.
        
        Args:
            metrics_df: Metrics DataFrame
            
        Returns:
            Formatted table
        """
        # Select and rename columns
        table = metrics_df[['display_name', 'value', 'unit', 'owner', 'metric_type']].copy()
        table.columns = ['Metric', 'Value', 'Unit', 'Owner', 'Type']
        
        return table
