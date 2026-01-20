"""
Visualization module for KPI framework.

Creates professional, clean visualizations optimized for leadership review.
Uses matplotlib and seaborn for consistency and clarity.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from ..config import (
    COLOR_POSITIVE,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    FIGSIZE_STANDARD,
    FIGSIZE_WIDE,
    FIGSIZE_TALL,
    FIGSIZE_SQUARE,
    TITLE_FONTSIZE,
    LABEL_FONTSIZE,
    TICK_FONTSIZE,
    WOW_GOOD_THRESHOLD,
    WOW_BAD_THRESHOLD,
    FIGURES_DIR,
)
from ..analysis.decomposition import DecompositionResult


# Set global style
sns.set_style("whitegrid")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']


class KPIVisualizer:
    """
    Creates all KPI visualizations for the framework.
    
    Visualizations:
    1. Metric Tree (driver map)
    2. VPAC Driver Waterfall
    3. Funnel-to-Value Bridge (placeholder - requires event data)
    4. KPI Health Grid
    5. Anomaly Calendar (placeholder - requires time series)
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize visualizer.
        
        Args:
            output_dir: Directory to save figures (defaults to FIGURES_DIR from config)
        """
        self.output_dir = output_dir or FIGURES_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def plot_metric_tree(
        self,
        north_star_value: float,
        components: Dict[str, float],
        deltas: Optional[Dict[str, float]] = None,
        save: bool = True
    ) -> plt.Figure:
        """
        Visual 1: Metric Tree showing North Star and its driver components.
        
        Args:
            north_star_value: VPAC value
            components: Dict of component values (orders_per_customer, items_per_order)
            deltas: Optional WoW changes for each metric
            save: Whether to save figure
            
        Returns:
            Figure object
        """
        fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
        ax.axis('off')
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        
        # Colors
        north_star_color = COLOR_PRIMARY
        driver_color = COLOR_SECONDARY
        
        # North Star box (top center)
        ns_x, ns_y = 5, 7
        ns_width, ns_height = 2.5, 1.5
        
        ns_box = FancyBboxPatch(
            (ns_x - ns_width/2, ns_y - ns_height/2),
            ns_width, ns_height,
            boxstyle="round,pad=0.1",
            edgecolor=north_star_color,
            facecolor=north_star_color,
            alpha=0.3,
            linewidth=3
        )
        ax.add_patch(ns_box)
        
        # North Star text
        delta_text = ""
        if deltas and 'vpac' in deltas:
            delta = deltas['vpac']
            delta_sign = "+" if delta >= 0 else ""
            delta_color = COLOR_POSITIVE if delta >= 0 else COLOR_NEGATIVE
            delta_text = f"\n({delta_sign}{delta:.2f})"
        
        ax.text(ns_x, ns_y + 0.3, "NORTH STAR", ha='center', va='center',
                fontsize=10, fontweight='bold', color=north_star_color)
        ax.text(ns_x, ns_y - 0.1, "VPAC", ha='center', va='center',
                fontsize=TITLE_FONTSIZE, fontweight='bold')
        ax.text(ns_x, ns_y - 0.5, f"{north_star_value:.2f}" + delta_text,
                ha='center', va='center', fontsize=LABEL_FONTSIZE)
        
        # Driver boxes (bottom)
        driver_positions = [
            (2.5, 3.5, 'orders_per_customer', 'Orders per\nCustomer'),
            (7.5, 3.5, 'items_per_order', 'Items per\nOrder')
        ]
        
        for dx, dy, key, label in driver_positions:
            # Driver box
            driver_box = FancyBboxPatch(
                (dx - 1, dy - 0.75),
                2, 1.5,
                boxstyle="round,pad=0.08",
                edgecolor=driver_color,
                facecolor=driver_color,
                alpha=0.2,
                linewidth=2
            )
            ax.add_patch(driver_box)
            
            # Value and delta
            value = components.get(key, 0)
            delta_text_driver = ""
            if deltas and key in deltas:
                delta = deltas[key]
                delta_sign = "+" if delta >= 0 else ""
                delta_text_driver = f"\n({delta_sign}{delta:.2f})"
            
            ax.text(dx, dy + 0.3, label, ha='center', va='center',
                    fontsize=LABEL_FONTSIZE, fontweight='bold')
            ax.text(dx, dy - 0.2, f"{value:.2f}" + delta_text_driver,
                    ha='center', va='center', fontsize=LABEL_FONTSIZE)
            
            # Arrow from driver to North Star
            arrow = FancyArrowPatch(
                (dx, dy + 0.75), (ns_x, ns_y - ns_height/2 - 0.1),
                arrowstyle='->,head_width=0.4,head_length=0.4',
                color=driver_color,
                linewidth=2,
                alpha=0.6
            )
            ax.add_patch(arrow)
        
        # Formula
        ax.text(5, 5.2, "VPAC = Orders per Customer × Items per Order",
                ha='center', va='center', fontsize=LABEL_FONTSIZE,
                style='italic', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Title
        fig.suptitle("KPI Metric Tree: North Star & Drivers", 
                     fontsize=TITLE_FONTSIZE + 2, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        
        if save:
            save_path = self.output_dir / "01_metric_tree.png"
            fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"✓ Saved: {save_path}")
        
        return fig
    
    def plot_waterfall(
        self,
        decomposition: DecompositionResult,
        save: bool = True
    ) -> plt.Figure:
        """
        Visual 2: Waterfall chart showing VPAC driver contributions to change.
        
        Args:
            decomposition: DecompositionResult from VPACDecomposer
            save: Whether to save figure
            
        Returns:
            Figure object
        """
        fig, ax = plt.subplots(figsize=FIGSIZE_STANDARD)
        
        # Prepare data
        drivers = []
        contributions = []
        
        for driver, contrib in decomposition.driver_contributions.items():
            if driver != 'interaction':  # Skip interaction for clarity unless large
                drivers.append(driver.replace('_', ' ').title())
                contributions.append(contrib)
        
        # Add interaction if significant
        if 'interaction' in decomposition.driver_contributions:
            interaction_val = decomposition.driver_contributions['interaction']
            if abs(interaction_val) > 0.01:  # Only show if > 1% of a unit
                drivers.append('Interaction')
                contributions.append(interaction_val)
        
        # Add total
        drivers.append('Total Change')
        contributions.append(decomposition.total_change)
        
        # Compute positions for waterfall
        n = len(drivers)
        x_pos = np.arange(n)
        
        # Calculate cumulative for bar positioning
        # For waterfall: start bottom of bar at cumulative of previous
        bottoms = [0]
        cumulative = 0
        for i, val in enumerate(contributions[:-1]):  # Exclude total
            cumulative += val
            bottoms.append(cumulative - contributions[i+1] if i < len(contributions)-2 else 0)
        
        # Colors: positive = green, negative = red, total = blue
        colors = []
        for i, val in enumerate(contributions):
            if i == len(contributions) - 1:  # Total
                colors.append(COLOR_PRIMARY)
            elif val >= 0:
                colors.append(COLOR_POSITIVE)
            else:
                colors.append(COLOR_NEGATIVE)
        
        # Plot bars
        bars = ax.bar(x_pos[:-1], contributions[:-1], bottom=bottoms[:-1],
                      color=colors[:-1], edgecolor='black', linewidth=1, alpha=0.7)
        
        # Total bar
        ax.bar(x_pos[-1], contributions[-1], bottom=0,
               color=colors[-1], edgecolor='black', linewidth=2, alpha=0.8)
        
        # Add value labels
        for i, (driver, contrib) in enumerate(zip(drivers, contributions)):
            if i < len(contributions) - 1:
                y_pos = bottoms[i] + contrib/2
            else:
                y_pos = contrib/2
            
            ax.text(i, y_pos, f"{contrib:+.2f}",
                    ha='center', va='center', fontsize=TICK_FONTSIZE,
                    fontweight='bold', color='white' if abs(contrib) > 0.5 else 'black')
        
        # Connecting lines (optional, for clarity)
        for i in range(len(x_pos) - 2):
            ax.plot([x_pos[i] + 0.4, x_pos[i+1] - 0.4],
                    [bottoms[i] + contributions[i], bottoms[i+1]],
                    'k--', linewidth=0.8, alpha=0.5)
        
        # Formatting
        ax.set_xticks(x_pos)
        ax.set_xticklabels(drivers, fontsize=TICK_FONTSIZE, rotation=0)
        ax.set_ylabel('Contribution to VPAC Change', fontsize=LABEL_FONTSIZE)
        ax.set_title(f'VPAC Driver Waterfall: {decomposition.period_start} → {decomposition.period_end}',
                     fontsize=TITLE_FONTSIZE, fontweight='bold', pad=20)
        
        # Grid
        ax.grid(axis='y', alpha=0.3)
        ax.set_axisbelow(True)
        
        # Zero line
        ax.axhline(y=0, color='black', linewidth=1.5, linestyle='-', alpha=0.8)
        
        plt.tight_layout()
        
        if save:
            save_path = self.output_dir / "02_vpac_waterfall.png"
            fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"✓ Saved: {save_path}")
        
        return fig
    
    def plot_kpi_health_grid(
        self,
        metrics_df: pd.DataFrame,
        save: bool = True
    ) -> plt.Figure:
        """
        Visual 4: KPI Health Grid - leadership-friendly table with status indicators.
        
        Args:
            metrics_df: DataFrame with columns: metric_name, display_name, value, unit
            save: Whether to save figure
            
        Returns:
            Figure object
        """
        fig, ax = plt.subplots(figsize=(12, len(metrics_df) * 0.5 + 1))
        ax.axis('tight')
        ax.axis('off')
        
        # Prepare table data
        table_data = []
        for _, row in metrics_df.iterrows():
            display_name = row['display_name']
            value = row['value']
            unit = row['unit']
            
            # Format value
            if unit == 'rate':
                value_str = f"{value:.1%}"
            elif unit in ['customers', 'orders', 'items']:
                value_str = f"{value:,.0f}"
            else:
                value_str = f"{value:.2f}"
            
            # Status (placeholder - would need historical data for real WoW)
            status = "●"  # Neutral by default
            
            table_data.append([display_name, value_str, unit, status])
        
        # Create table
        table = ax.table(
            cellText=table_data,
            colLabels=['Metric', 'Value', 'Unit', 'Status'],
            cellLoc='left',
            loc='center',
            colWidths=[0.4, 0.25, 0.2, 0.15]
        )
        
        # Style table
        table.auto_set_font_size(False)
        table.set_fontsize(TICK_FONTSIZE)
        table.scale(1, 2)
        
        # Header styling
        for i in range(4):
            cell = table[(0, i)]
            cell.set_facecolor(COLOR_PRIMARY)
            cell.set_text_props(weight='bold', color='white', fontsize=LABEL_FONTSIZE)
        
        # Alternating row colors
        for i in range(1, len(table_data) + 1):
            for j in range(4):
                cell = table[(i, j)]
                if i % 2 == 0:
                    cell.set_facecolor('#f0f0f0')
                else:
                    cell.set_facecolor('white')
        
        fig.suptitle('KPI Health Grid', fontsize=TITLE_FONTSIZE + 2, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        
        if save:
            save_path = self.output_dir / "04_kpi_health_grid.png"
            fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"✓ Saved: {save_path}")
        
        return fig
    
    def plot_segment_comparison(
        self,
        segment_df: pd.DataFrame,
        metric_col: str = 'vpac',
        segment_col: str = 'segment',
        save: bool = True
    ) -> plt.Figure:
        """
        Visual 3 (alternative): Customer segment comparison.
        
        Args:
            segment_df: DataFrame with segment data
            metric_col: Column name for metric to plot
            segment_col: Column name for segment labels
            save: Whether to save figure
            
        Returns:
            Figure object
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)
        
        # Sort by metric value
        segment_df_sorted = segment_df.sort_values(metric_col, ascending=False)
        
        # Plot 1: Metric by segment
        bars = ax1.barh(segment_df_sorted.index, segment_df_sorted[metric_col],
                        color=COLOR_PRIMARY, edgecolor='black', alpha=0.7)
        
        ax1.set_xlabel(metric_col.upper(), fontsize=LABEL_FONTSIZE)
        ax1.set_title(f'{metric_col.upper()} by Customer Segment',
                      fontsize=TITLE_FONTSIZE, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, (idx, row) in enumerate(segment_df_sorted.iterrows()):
            ax1.text(row[metric_col], i, f" {row[metric_col]:.2f}",
                     va='center', fontsize=TICK_FONTSIZE, fontweight='bold')
        
        # Plot 2: Customer and order share
        if 'customer_share' in segment_df.columns and 'order_share' in segment_df.columns:
            x = np.arange(len(segment_df_sorted))
            width = 0.35
            
            ax2.bar(x - width/2, segment_df_sorted['customer_share'] * 100,
                    width, label='Customer Share', color=COLOR_SECONDARY, alpha=0.7)
            ax2.bar(x + width/2, segment_df_sorted['order_share'] * 100,
                    width, label='Order Share', color=COLOR_PRIMARY, alpha=0.7)
            
            ax2.set_ylabel('Share (%)', fontsize=LABEL_FONTSIZE)
            ax2.set_title('Customer vs Order Share by Segment',
                          fontsize=TITLE_FONTSIZE, fontweight='bold')
            ax2.set_xticks(x)
            ax2.set_xticklabels(segment_df_sorted.index, fontsize=TICK_FONTSIZE)
            ax2.legend(fontsize=TICK_FONTSIZE)
            ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            save_path = self.output_dir / "03_segment_comparison.png"
            fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"✓ Saved: {save_path}")
        
        return fig
    
    def plot_distribution(
        self,
        data: pd.Series,
        metric_name: str,
        bins: int = 50,
        save: bool = True
    ) -> plt.Figure:
        """
        Plot distribution of a user-level metric.
        
        Args:
            data: Series with metric values
            metric_name: Name of metric for labeling
            bins: Number of histogram bins
            save: Whether to save
            
        Returns:
            Figure object
        """
        fig, ax = plt.subplots(figsize=FIGSIZE_STANDARD)
        
        # Plot histogram
        ax.hist(data.dropna(), bins=bins, color=COLOR_PRIMARY,
                edgecolor='black', alpha=0.7)
        
        # Add statistics
        mean_val = data.mean()
        median_val = data.median()
        
        ax.axvline(mean_val, color=COLOR_NEGATIVE, linestyle='--',
                   linewidth=2, label=f'Mean: {mean_val:.2f}')
        ax.axvline(median_val, color=COLOR_POSITIVE, linestyle='--',
                   linewidth=2, label=f'Median: {median_val:.2f}')
        
        ax.set_xlabel(metric_name, fontsize=LABEL_FONTSIZE)
        ax.set_ylabel('Customer Count', fontsize=LABEL_FONTSIZE)
        ax.set_title(f'Distribution of {metric_name}',
                     fontsize=TITLE_FONTSIZE, fontweight='bold')
        ax.legend(fontsize=TICK_FONTSIZE)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            filename = f"05_dist_{metric_name.lower().replace(' ', '_')}.png"
            save_path = self.output_dir / filename
            fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"✓ Saved: {save_path}")
        
        return fig
