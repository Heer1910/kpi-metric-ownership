"""
Configuration module for KPI Framework.

Structured configuration with environment support and optional YAML loading.
Ensures reproducibility and maintainability.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import yaml


# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================

ENV = os.getenv("KPI_ENV", "DEV")  # DEV, CI, PROD
IS_CI = ENV == "CI"
IS_PROD = ENV == "PROD"


# ============================================================================
# PROJECT CONFIGURATION
# ============================================================================

@dataclass
class ProjectConfig:
    """Project-level paths and directories."""
    
    # Core paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    
    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"
    
    @property
    def sql_dir(self) -> Path:
        return self.project_root / "sql"
    
    @property
    def figures_dir(self) -> Path:
        return self.project_root / "figures"
    
    @property
    def reports_dir(self) -> Path:
        return self.project_root / "reports"
    
    @property
    def docs_dir(self) -> Path:
        return self.project_root / "docs"
    
    # Data sources (CSV files)
    @property
    def orders_file(self) -> Path:
        return self.data_dir / "orders.csv"
    
    @property
    def order_products_prior_file(self) -> Path:
        return self.data_dir / "order_products__prior.csv"
    
    @property
    def order_products_train_file(self) -> Path:
        return self.data_dir / "order_products__train.csv"
    
    @property
    def products_file(self) -> Path:
        return self.data_dir / "products.csv"
    
    @property
    def aisles_file(self) -> Path:
        return self.data_dir / "aisles.csv"
    
    @property
    def departments_file(self) -> Path:
        return self.data_dir / "departments.csv"
    
    # Time parameters
    week_start_day: int = 0  # Monday
    review_lookback_weeks: int = 8
    
    def ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# METRIC CONFIGURATION
# ============================================================================

@dataclass
class MetricConfig:
    """Metric definitions and thresholds."""
    
    # North Star
    north_star_metric: str = "VPAC"
    north_star_formula: str = "orders_per_customer * items_per_order"
    
    # Small basket definition
    small_basket_threshold: int = 3  # items
    
    # Anomaly detection
    anomaly_z_threshold: float = 2.5  # standard deviations
    
    # WoW movement thresholds
    wow_good_threshold: float = 0.02  # +2%
    wow_bad_threshold: float = -0.02  # -2%
    
    # Minimum sample size
    min_sample_size: int = 100
    
    # Decomposition tolerance
    decomposition_tolerance: float = 0.01  # 1%
    
    # Data quality
    max_missing_rate: float = 0.05  # 5%
    
    # Metric lists
    kpi_list: List[str] = field(default_factory=lambda: [
        "active_customers",
        "orders",
        "items",
        "orders_per_customer",
        "items_per_order",
        "reorder_rate",
    ])
    
    guardrail_metrics: List[str] = field(default_factory=lambda: [
        "median_days_since_prior",
        "small_basket_share",
    ])
    
    # Expected monotonic relationships (for validation)
    monotonic_relationships: List[Tuple[str, str, str]] = field(default_factory=lambda: [
        ("orders", "active_customers", ">="),
        ("items", "orders", ">="),
    ])


# ============================================================================
# VISUALIZATION CONFIGURATION
# ============================================================================

@dataclass
class VizConfig:
    """Visualization styling and parameters."""
    
    # Color palette (colorblind-friendly)
    color_positive: str = "#2ecc71"  # green
    color_negative: str = "#e74c3c"  # red
    color_neutral: str = "#95a5a6"   # grey
    color_primary: str = "#3498db"   # blue
    color_secondary: str = "#9b59b6" # purple
    
    # Figure sizes
    figsize_standard: Tuple[int, int] = (12, 6)
    figsize_wide: Tuple[int, int] = (14, 6)
    figsize_tall: Tuple[int, int] = (10, 8)
    figsize_square: Tuple[int, int] = (10, 10)
    
    # Font sizes
    title_fontsize: int = 14
    label_fontsize: int = 11
    tick_fontsize: int = 10
    
    # DPI for saved figures
    dpi: int = 300
    
    # Style
    style: str = "seaborn-v0_8-darkgrid"  # matplotlib style


# ============================================================================
# CONFIGURATION LOADER
# ============================================================================

class ConfigLoader:
    """Loads configuration from YAML files (optional) or uses defaults."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_file: Optional path to config.yaml file
        """
        self.config_file = config_file
        self.project = ProjectConfig()
        self.metrics = MetricConfig()
        self.viz = VizConfig()
        
        # Load from YAML if file exists
        if config_file and config_file.exists():
            self._load_from_yaml(config_file)
        
        # Environment-specific overrides
        self._apply_env_overrides()
        
        # Ensure directories
        self.project.ensure_directories()
    
    def _load_from_yaml(self, config_file: Path) -> None:
        """Load configuration from YAML file."""
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Update project config
        if 'project' in config_data:
            for key, value in config_data['project'].items():
                if hasattr(self.project, key):
                    setattr(self.project, key, value)
        
        # Update metrics config
        if 'metrics' in config_data:
            for key, value in config_data['metrics'].items():
                if hasattr(self.metrics, key):
                    setattr(self.metrics, key, value)
        
        # Update viz config
        if 'viz' in config_data:
            for key, value in config_data['viz'].items():
                if hasattr(self.viz, key):
                    setattr(self.viz, key, value)
    
    def _apply_env_overrides(self) -> None:
        """Apply environment-specific overrides."""
        if IS_CI:
            # CI environment: smaller figures, faster execution
            self.viz.dpi = 150
            self.viz.figsize_standard = (10, 5)
            self.metrics.min_sample_size = 50
        
        if IS_PROD:
            # Production: stricter validation
            self.metrics.max_missing_rate = 0.02  # 2%
            self.metrics.decomposition_tolerance = 0.005  # 0.5%


# ============================================================================
# GLOBAL CONFIG INSTANCE
# ============================================================================

# Check for config.yaml in project root
_config_file = Path(__file__).parent.parent / "config.yaml"
config = ConfigLoader(config_file=_config_file if _config_file.exists() else None)

# Expose for backwards compatibility and convenience
PROJECT_ROOT = config.project.project_root
DATA_DIR = config.project.data_dir
SQL_DIR = config.project.sql_dir
FIGURES_DIR = config.project.figures_dir
REPORTS_DIR = config.project.reports_dir
DOCS_DIR = config.project.docs_dir

ORDERS_FILE = config.project.orders_file
ORDER_PRODUCTS_PRIOR_FILE = config.project.order_products_prior_file
ORDER_PRODUCTS_TRAIN_FILE = config.project.order_products_train_file
PRODUCTS_FILE = config.project.products_file
AISLES_FILE = config.project.aisles_file
DEPARTMENTS_FILE = config.project.departments_file

SMALL_BASKET_THRESHOLD = config.metrics.small_basket_threshold
ANOMALY_Z_THRESHOLD = config.metrics.anomaly_z_threshold
WOW_GOOD_THRESHOLD = config.metrics.wow_good_threshold
WOW_BAD_THRESHOLD = config.metrics.wow_bad_threshold
MIN_SAMPLE_SIZE = config.metrics.min_sample_size
MAX_MISSING_RATE = config.metrics.max_missing_rate
DECOMPOSITION_TOLERANCE = config.metrics.decomposition_tolerance
MONOTONIC_RELATIONSHIPS = config.metrics.monotonic_relationships

COLOR_POSITIVE = config.viz.color_positive
COLOR_NEGATIVE = config.viz.color_negative
COLOR_NEUTRAL = config.viz.color_neutral
COLOR_PRIMARY = config.viz.color_primary
COLOR_SECONDARY = config.viz.color_secondary
FIGSIZE_STANDARD = config.viz.figsize_standard
FIGSIZE_WIDE = config.viz.figsize_wide
FIGSIZE_TALL = config.viz.figsize_tall
FIGSIZE_SQUARE = config.viz.figsize_square
TITLE_FONTSIZE = config.viz.title_fontsize
LABEL_FONTSIZE = config.viz.label_fontsize
TICK_FONTSIZE = config.viz.tick_fontsize

WEEK_START_DAY = config.project.week_start_day
REVIEW_LOOKBACK_WEEKS = config.project.review_lookback_weeks
