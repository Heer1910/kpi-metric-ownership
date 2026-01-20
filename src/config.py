"""
Configuration module for KPI Framework.
Centralizes all parameters for reproducibility.
"""

from pathlib import Path
from datetime import datetime, timedelta

# ============================================================================
# PROJECT PATHS
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"
FIGURES_DIR = PROJECT_ROOT / "figures"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"

# Ensure directories exist
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DATA SOURCES
# ============================================================================
# Instacart dataset CSV files
ORDERS_FILE = DATA_DIR / "orders.csv"
ORDER_PRODUCTS_PRIOR_FILE = DATA_DIR / "order_products__prior.csv"
ORDER_PRODUCTS_TRAIN_FILE = DATA_DIR / "order_products__train.csv"
PRODUCTS_FILE = DATA_DIR / "products.csv"
AISLES_FILE = DATA_DIR / "aisles.csv"
DEPARTMENTS_FILE = DATA_DIR / "departments.csv"

# ============================================================================
# TIME PARAMETERS
# ============================================================================
# Week definition
WEEK_START_DAY = 0  # Monday = 0, Sunday = 6

# Analysis window (will be computed from data)
# These are placeholders - actual values computed in data loading
START_DATE = None
END_DATE = None

# ============================================================================
# METRIC DEFINITIONS
# ============================================================================

# North Star Metric: Value per Active Customer (VPAC)
# VPAC = Orders per Active Customer × Items per Order
NORTH_STAR_METRIC = "VPAC"
NORTH_STAR_FORMULA = "orders_per_customer * items_per_order"

# Supporting KPIs
KPI_LIST = [
    "active_customers",
    "orders",
    "items",
    "orders_per_customer",
    "items_per_order",
    "reorder_rate",
    "basket_size_median",
]

# Guardrail metrics
GUARDRAIL_METRICS = [
    "median_days_since_prior",
    "small_basket_share",  # ≤3 items
]

# ============================================================================
# THRESHOLDS
# ============================================================================

# Anomaly detection
ANOMALY_Z_THRESHOLD = 2.5  # Standard deviations for flagging

# Small basket definition
SMALL_BASKET_THRESHOLD = 3  # items

# Minimum sample size for valid metric computation
MIN_SAMPLE_SIZE = 100

# ============================================================================
# VISUAL STYLING
# ============================================================================

# Color palette (professional, colorblind-friendly)
COLOR_POSITIVE = "#2ecc71"  # green
COLOR_NEGATIVE = "#e74c3c"  # red
COLOR_NEUTRAL = "#95a5a6"   # grey
COLOR_PRIMARY = "#3498db"   # blue
COLOR_SECONDARY = "#9b59b6" # purple

# Status thresholds for health grid
WOW_GOOD_THRESHOLD = 0.02    # +2% is good
WOW_BAD_THRESHOLD = -0.02    # -2% is bad

# Figure size defaults
FIGSIZE_STANDARD = (12, 6)
FIGSIZE_WIDE = (14, 6)
FIGSIZE_TALL = (10, 8)
FIGSIZE_SQUARE = (10, 10)

# Font sizes
TITLE_FONTSIZE = 14
LABEL_FONTSIZE = 11
TICK_FONTSIZE = 10

# ============================================================================
# REPORTING
# ============================================================================

# Number of weeks to include in weekly business review
REVIEW_LOOKBACK_WEEKS = 8

# Decomposition tolerance (for validation)
DECOMPOSITION_TOLERANCE = 0.01  # 1% tolerance for rounding

# ============================================================================
# DATA QUALITY
# ============================================================================

# Maximum allowed missing rate
MAX_MISSING_RATE = 0.05  # 5%

# Expected relationships (for validation)
MONOTONIC_RELATIONSHIPS = [
    ("orders", "active_customers", ">="),  # orders >= customers (some reorder)
    ("items", "orders", ">="),              # items >= orders (at least 1 item/order)
]
