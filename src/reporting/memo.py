"""
KPI reporting and memo generation.

This module creates structured business review reports and KPI summaries.
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
        lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        lines.append("---\n")
        
        # Executive Summary: North Star
        lines.append("## 📊 Executive Summary\n")
        lines.append(f"**North Star Metric: VPAC** = {north_star_info['value']:.2f}\n")
        lines.append(f"*{north_star_info['formula']}*\n")
        
        lines.append("### Components\n")
        for comp, val in north_star_info['components'].items():
            comp_display = comp.replace('_', ' ').title()
            lines.append(f"- **{comp_display}**: {val:.2f}")
        
        lines.append("\n")
        
        # Decomposition (if provided)
        if decomposition:
            lines.append("## 🔍 What Moved and Why\n")
            lines.append(f"**Total Change:** {decomposition.total_change:+.2f} ")
            lines.append(f"({decomposition.percent_change:+.1%})\n")
            
            lines.append("### Driver Attribution\n")
            for driver, contrib in decomposition.driver_contributions.items():
                if driver != 'interaction' or abs(contrib) > 0.01:
                    driver_display = driver.replace('_', ' ').title()
                    lines.append(f"- **{driver_display}**: {contrib:+.2f}")
            
            lines.append("\n")
        
        # All KPIs Table
        lines.append("## 📈 All KPIs\n")
        lines.append("| Metric | Value | Unit | Owner |")
        lines.append("|--------|-------|------|-------|")
        
        for _, row in metrics_df.iterrows():
            display_name = row['display_name']
            value = row['value']
            unit = row['unit']
            owner = row.get('owner', '-')
            
            # Format value
            if unit == 'rate':
                value_str = f"{value:.1%}"
            elif unit in ['customers', 'orders', 'items']:
                value_str = f"{value:,.0f}"
            else:
                value_str = f"{value:.2f}"
            
            lines.append(f"| {display_name} | {value_str} | {unit} | {owner} |")
        
        lines.append("\n")
        
        # Key Insights
        if key_insights:
            lines.append("## 💡 Key Insights\n")
            for i, insight in enumerate(key_insights, 1):
                lines.append(f"{i}. {insight}")
            lines.append("\n")
        
        # Recommendations section (placeholder)
        lines.append("## 🎯 Recommended Actions\n")
        lines.append("_To be filled based on metric movements and business context._\n")
        lines.append("---\n")
        
        # Footer
        lines.append("*This report was generated automatically by the KPI Framework system.*")
        
        report = "\n".join(lines)
        
        if save:
            save_path = self.output_dir / "weekly_business_review.md"
            with open(save_path, 'w') as f:
                f.write(report)
            print(f"✓ Saved: {save_path}")
        
        return report
    
    def create_kpi_summary_table(self, metrics_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create a formatted summary table for easy scanning.
        
        Args:
            metrics_df: DataFrame with metrics
            
        Returns:
            Formatted DataFrame
        """
        summary = metrics_df[['display_name', 'metric_type', 'value', 'unit', 'owner']].copy()
        summary = summary.rename(columns={
            'display_name': 'Metric',
            'metric_type': 'Type',
            'value': 'Value',
            'unit': 'Unit',
            'owner': 'Owner'
        })
        
        # Format value column
        def format_value(row):
            if row['Unit'] == 'rate':
                return f"{row['Value']:.1%}"
            elif row['Unit'] in ['customers', 'orders', 'items']:
                return f"{row['Value']:,.0f}"
            else:
                return f"{row['Value']:.2f}"
        
        summary['Value'] = summary.apply(format_value, axis=1)
        
        return summary
