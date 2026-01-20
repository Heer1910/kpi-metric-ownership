"""
Executive dashboard visualization combining multiple charts.
"""

import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

from .charts import KPIVisualizer
from ..config import FIGURES_DIR, TITLE_FONTSIZE


def create_executive_dashboard(
    north_star_info: Dict,
    decomposition,
    segments: pd.DataFrame,
    metrics_df: pd.DataFrame,
    save: bool = True,
    output_dir: Optional[Path] = None
) -> plt.Figure:
    """
    Create a 2x2 executive dashboard combining key views.
    
    Panels:
    - Top left: North Star metric tree
    - Top right: Driver waterfall
    - Bottom left: Segment comparison
    - Bottom right: KPI health grid summary
    
    Args:
        north_star_info: Dict with North Star value and components
        decomposition: DecompositionResult from VPACDecomposer
        segments: Customer segmentation DataFrame
        metrics_df: All metrics DataFrame
        save: Whether to save the figure
        output_dir: Output directory (defaults to FIGURES_DIR)
        
    Returns:
        Figure object with 2x2 subplots
    """
    output_dir = output_dir or FIGURES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    fig = plt.figure(figsize=(20, 14))
    
    # Create 2x2 grid
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.25)
    
    # Panel 1: Metric Tree (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.axis('off')
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    
    # Simplified metric tree
    vpac_val = north_star_info['value']
    orders_val = north_star_info['components'].get('orders_per_customer', 0)
    items_val = north_star_info['components'].get('items_per_order', 0)
    
    ax1.text(5, 8, 'NORTH STAR', ha='center', fontsize=14, weight='bold', color='#1f77b4')
    ax1.text(5, 7.3, f'VPAC: {vpac_val:.2f}', ha='center', fontsize=18, weight='bold')
    ax1.text(5, 6.5, 'items/customer', ha='center', fontsize=10, style='italic')
    
    # Drivers
    ax1.text(2.5, 3.5, 'Orders/Customer', ha='center', fontsize=12, weight='bold')
    ax1.text(2.5, 2.8, f'{orders_val:.2f}', ha='center', fontsize=14)
    
    ax1.text(7.5, 3.5, 'Items/Order', ha='center', fontsize=12, weight='bold')
    ax1.text(7.5, 2.8, f'{items_val:.2f}', ha='center', fontsize=14)
    
    # Arrows
    ax1.annotate('', xy=(5, 6.2), xytext=(2.5, 4),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray'))
    ax1.annotate('', xy=(5, 6.2), xytext=(7.5, 4),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray'))
    
    ax1.set_title('1. North Star Metric', fontsize=TITLE_FONTSIZE, weight='bold', pad=10)
    
    # Panel 2: Driver Waterfall (top right)
    ax2 = fig.add_subplot(gs[0, 1])
    
    drivers = []
    contributions = []
    for driver, contrib in decomposition.driver_contributions.items():
        if driver != 'interaction' or abs(contrib) > 0.01:
            drivers.append(driver.replace('_', ' ').title())
            contributions.append(contrib)
    
    x_pos = range(len(drivers))
    colors = ['#2ecc71' if c >= 0 else '#e74c3c' for c in contributions]
    
    ax2.bar(x_pos, contributions, color=colors, alpha=0.7, edgecolor='black')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(drivers, rotation=15, ha='right')
    ax2.set_ylabel('Contribution', fontsize=12)
    ax2.set_title('2. Driver Attribution', fontsize=TITLE_FONTSIZE, weight='bold', pad=10)
    ax2.grid(axis='y', alpha=0.3)
    
    # Panel 3: Segment Comparison (bottom left)
    ax3 = fig.add_subplot(gs[1, 0])
    
    segments_plot = segments.sort_values('vpac', ascending=False)
    y_pos = range(len(segments_plot))
    
    ax3.barh(y_pos, segments_plot['vpac'], color='#3498db', alpha=0.7, edgecolor='black')
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(segments_plot.index)
    ax3.set_xlabel('VPAC', fontsize=12)
    ax3.set_title('3. Customer Segments', fontsize=TITLE_FONTSIZE, weight='bold', pad=10)
    ax3.grid(axis='x', alpha=0.3)
    
    # Panel 4: KPI Summary Table (bottom right)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')
    
    # Select key metrics for summary
    key_metrics = ['vpac', 'active_customers', 'orders_per_customer', 
                   'items_per_order', 'reorder_rate', 'small_basket_share']
    
    summary_data = []
    for _, row in metrics_df.iterrows():
        if row['metric_name'] in key_metrics:
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
            
            summary_data.append([display_name, value_str])
    
    table = ax4.table(
        cellText=summary_data,
        colLabels=['Metric', 'Value'],
        cellLoc='left',
        loc='center',
        colWidths=[0.65, 0.35]
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.5)
    
    # Header styling
    for i in range(2):
        cell = table[(0, i)]
        cell.set_facecolor('#1f77b4')
        cell.set_text_props(weight='bold', color='white')
    
    # Alternating rows
    for i in range(1, len(summary_data) + 1):
        for j in range(2):
            cell = table[(i, j)]
            if i % 2 == 0:
                cell.set_facecolor('#f0f0f0')
    
    ax4.set_title('4. KPI Summary', fontsize=TITLE_FONTSIZE, weight='bold', pad=10)
    
    # Overall title
    fig.suptitle('Executive Dashboard: KPI Overview',
                fontsize=TITLE_FONTSIZE + 4, weight='bold', y=0.98)
    
    if save:
        save_path = output_dir / '00_executive_dashboard.png'
        fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✓ Saved: {save_path}")
    
    return fig
