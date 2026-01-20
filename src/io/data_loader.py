"""
Data loading and database interaction using DuckDB.

This module handles:
- Loading Instacart CSV files into DuckDB
- SQL query execution
- Data validation and quality checks
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from ..config import (
    ORDERS_FILE,
    ORDER_PRODUCTS_PRIOR_FILE,
    ORDER_PRODUCTS_TRAIN_FILE,
    PRODUCTS_FILE,
    AISLES_FILE,
    DEPARTMENTS_FILE,
    SQL_DIR,
)


class InstacartDataLoader:
    """
    Loads Instacart dataset into DuckDB and provides query interface.
    
    The dataset consists of:
    - orders: user orders with timing information
    - order_products: which products were in each order
    - products: product catalog with category hierarchy
    - aisles, departments: product categorization
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize data loader.
        
        Args:
            db_path: Path to DuckDB database file. If None, uses in-memory database.
        """
        self.db_path = db_path or ":memory:"
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self.metadata: Dict[str, Any] = {}
        
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def connect(self) -> None:
        """Establish connection to DuckDB."""
        self.conn = duckdb.connect(self.db_path)
        print(f"✓ Connected to DuckDB: {self.db_path}")
        
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")
            
    def load_all_tables(self) -> None:
        """
        Load all Instacart CSV files into DuckDB tables.
        Performs basic validation and collects metadata.
        """
        if not self.conn:
            raise RuntimeError("Database connection not established. Call connect() first.")
        
        print("\n" + "="*70)
        print("LOADING INSTACART DATASET INTO DUCKDB")
        print("="*70)
        
        # Define table loading specs
        tables_to_load = [
            ("orders", ORDERS_FILE),
            ("order_products_prior", ORDER_PRODUCTS_PRIOR_FILE),
            ("order_products_train", ORDER_PRODUCTS_TRAIN_FILE),
            ("products", PRODUCTS_FILE),
            ("aisles", AISLES_FILE),
            ("departments", DEPARTMENTS_FILE),
        ]
        
        # Load each table
        for table_name, file_path in tables_to_load:
            self._load_table(table_name, file_path)
            
        # Combine order_products tables for easier analysis
        self._create_order_products_combined()
        
        # Collect dataset metadata
        self._collect_metadata()
        
        print("\n" + "="*70)
        print("✓ ALL TABLES LOADED SUCCESSFULLY")
        print("="*70)
        
    def _load_table(self, table_name: str, file_path: Path) -> None:
        """Load a single CSV file into a DuckDB table."""
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        print(f"\nLoading {table_name}...")
        print(f"  Source: {file_path.name}")
        
        # Use DuckDB's native CSV reader (very fast)
        query = f"""
        CREATE TABLE {table_name} AS 
        SELECT * FROM read_csv_auto('{file_path}', header=true)
        """
        
        self.conn.execute(query)
        
        # Get row count
        row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  ✓ Loaded {row_count:,} rows")
        
    def _create_order_products_combined(self) -> None:
        """
        Combine prior and train order_products tables into a single view.
        This makes analysis easier since we want to analyze all orders together.
        """
        print("\nCreating combined order_products table...")
        
        query = """
        CREATE TABLE order_products AS
        SELECT * FROM order_products_prior
        UNION ALL
        SELECT * FROM order_products_train
        """
        
        self.conn.execute(query)
        
        row_count = self.conn.execute("SELECT COUNT(*) FROM order_products").fetchone()[0]
        print(f"  ✓ Combined table: {row_count:,} rows")
        
    def _collect_metadata(self) -> None:
        """Collect high-level dataset metadata for reference."""
        queries = {
            "total_users": "SELECT COUNT(DISTINCT user_id) FROM orders",
            "total_orders": "SELECT COUNT(*) FROM orders",
            "total_products": "SELECT COUNT(*) FROM products",
            "total_departments": "SELECT COUNT(*) FROM departments",
            "total_aisles": "SELECT COUNT(*) FROM aisles",
            "total_order_items": "SELECT COUNT(*) FROM order_products",
            "date_range_days": """
                SELECT MAX(days_since_prior_order) 
                FROM orders 
                WHERE days_since_prior_order IS NOT NULL
            """,
        }
        
        print("\nDataset Summary:")
        print("-" * 50)
        
        for key, query in queries.items():
            value = self.conn.execute(query).fetchone()[0]
            self.metadata[key] = value
            
            # Format output nicely
            label = key.replace("_", " ").title()
            print(f"  {label}: {value:,}")
            
    def execute_sql(self, query: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as pandas DataFrame.
        
        Args:
            query: SQL query string
            
        Returns:
            Query results as DataFrame
        """
        if not self.conn:
            raise RuntimeError("Database connection not established.")
        
        return self.conn.execute(query).df()
        
    def execute_sql_file(self, sql_file: Path) -> pd.DataFrame:
        """
        Execute SQL from a file.
        
        Args:
            sql_file: Path to .sql file
            
        Returns:
            Query results as DataFrame
        """
        with open(sql_file, 'r') as f:
            query = f.read()
        
        return self.execute_sql(query)
        
    def get_table_info(self, table_name: str) -> pd.DataFrame:
        """Get schema information for a table."""
        query = f"DESCRIBE {table_name}"
        return self.execute_sql(query)
        
    def preview_table(self, table_name: str, n: int = 5) -> pd.DataFrame:
        """Preview first n rows of a table."""
        query = f"SELECT * FROM {table_name} LIMIT {n}"
        return self.execute_sql(query)


def quick_load() -> InstacartDataLoader:
    """
    Convenience function to quickly load data and return connected loader.
    
    Usage:
        >>> loader = quick_load()
        >>> df = loader.execute_sql("SELECT * FROM orders LIMIT 10")
    """
    loader = InstacartDataLoader()
    loader.connect()
    loader.load_all_tables()
    return loader
