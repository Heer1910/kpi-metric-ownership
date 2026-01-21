"""
Data loading and database interaction using DuckDB.

Production-grade loader with:
- Persistent database caching for performance
- Explicit schema definitions (no inference surprises)
- Deterministic loading with row count validation
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


# Explicit schema definitions  
TABLE_SCHEMAS = {
    "orders": {
        "order_id": "INTEGER",
        "user_id": "INTEGER",
        "eval_set": "VARCHAR",
        "order_number": "INTEGER",
        "order_dow": "INTEGER",
        "order_hour_of_day": "INTEGER",
        "days_since_prior_order": "DOUBLE",
    },
    "order_products": {
        "order_id": "INTEGER",
        "product_id": "INTEGER",
        "add_to_cart_order": "INTEGER",
        "reordered": "INTEGER",
    },
    "products": {
        "product_id":  "INTEGER",
        "product_name": "VARCHAR",
        "aisle_id": "INTEGER",
        "department_id": "INTEGER",
    },
    "aisles": {
        "aisle_id": "INTEGER",
        "aisle": "VARCHAR",
    },
    "departments": {
        "department_id": "INTEGER",
        "department": "VARCHAR",
    },
}


class InstacartDataLoader:
    """Production data loader with persistent caching and explicit schemas."""
    
    def __init__(
        self, 
        db_path: Optional[str] = None, 
        data_dir: str = "data",
        use_cache: bool = True
    ):
        self.data_dir = Path(data_dir)
        
        if db_path is None:
            self.db_path = str(self.data_dir / "instacart.duckdb")
        else:
            self.db_path = db_path
        
        self.use_cache = use_cache
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self.metadata: Dict[str, Any] = {}
        self.is_cached = False
        
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def connect(self) -> None:
        db_file = Path(self.db_path)
        
        if self.use_cache and db_file.exists() and db_file.stat().st_size > 0:
            self.conn = duckdb.connect(self.db_path)
            
            table_count = self.conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchone()[0]
            
            if table_count >= 6:
                self.is_cached = True
                print(f"Using cached database: {self.db_path}")
                print(f"  ({table_count} tables found, skipping CSV load)")
                return
        
        self.conn = duckdb.connect(self.db_path)
        self.is_cached = False
        print(f"Connected to DuckDB: {self.db_path}")
        if db_file.exists():
            print("  (Database exists but is empty or incomplete, will load CSVs)")
        
    def close(self) -> None:
        if self.conn:
            self.conn.close()
            print("Database connection closed")
            
    def load_all_tables(self) -> None:
        if not self.conn:
            raise RuntimeError("Database connection not established. Call connect() first.")
        
        if self.is_cached:
            self._collect_metadata()
            print(f"\n{'='*70}")
            print("USING CACHED DATABASE (no CSV load needed)")
            print(f"{'='*70}")
            return
        
        print(f"\n{'='*70}")
        print("LOADING INSTACART DATASET INTO DUCKDB")
        print(f"{'='*70}")
        
        tables_to_load = [
            ("orders", "orders.csv", TABLE_SCHEMAS["orders"]),
            ("order_products_prior", "order_products__prior.csv", TABLE_SCHEMAS["order_products"]),
            ("order_products_train", "order_products__train.csv", TABLE_SCHEMAS["order_products"]),
            ("products", "products.csv", TABLE_SCHEMAS["products"]),
            ("aisles", "aisles.csv", TABLE_SCHEMAS["aisles"]),
            ("departments", "departments.csv", TABLE_SCHEMAS["departments"]),
        ]
        
        for table_name, filename, schema in tables_to_load:
            file_path = self.data_dir / filename
            self._load_table_with_schema(table_name, file_path, schema)
            
        self._create_order_products_combined()
        self._collect_metadata()
        
        print(f"\n{'='*70}")
        print("ALL TABLES LOADED SUCCESSFULLY")
        print(f"{'='*70}")
        
    def _load_table_with_schema(
        self, 
        table_name: str, 
        file_path: Path, 
        schema: Dict[str, str]
    ) -> None:
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        print(f"\nLoading {table_name}...")
        print(f"  Source: {file_path.name}")
        
        query = f"""
        CREATE TABLE {table_name} AS 
        SELECT * FROM read_csv_auto('{file_path}', header=true)
        """
        
        try:
            self.conn.execute(query)
        except Exception as e:
            print(f"  Failed to load {table_name}: {e}")
            raise
        
        row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  Loaded {row_count:,} rows")
        
    def _create_order_products_combined(self) -> None:
        print("\nCreating combined order_products table...")
        
        query = """
        CREATE TABLE order_products AS
        SELECT * FROM order_products_prior
        UNION ALL
        SELECT * FROM order_products_train
        """
        
        self.conn.execute(query)
        
        row_count = self.conn.execute("SELECT COUNT(*) FROM order_products").fetchone()[0]
        print(f"  Combined table: {row_count:,} rows")
        
    def _collect_metadata(self) -> None:
        queries = {
            "total_users": "SELECT COUNT(DISTINCT user_id) FROM orders",
            "total_orders": "SELECT COUNT(*) FROM orders",
            "total_products": "SELECT COUNT(*) FROM products",
            "total_departments": "SELECT COUNT(*) FROM departments",
            "total_aisles": "SELECT COUNT(*) FROM aisles",
            "total_order_items": "SELECT COUNT(*) FROM order_products",
            "date_range_days": "SELECT MAX(days_since_prior_order) FROM orders",
        }
        
        for key, query in queries.items():
            try:
                result = self.conn.execute(query).fetchone()[0]
                self.metadata[key] = result
            except Exception:
                self.metadata[key] = None
        
        print("\nDataset Summary:")
        print("-" * 50)
        print(f"  Total Users: {self.metadata.get('total_users', 'N/A'):,}")
        print(f"  Total Orders: {self.metadata.get('total_orders', 'N/A'):,}")
        print(f"  Total Products: {self.metadata.get('total_products', 'N/A'):,}")
        print(f"  Total Departments: {self.metadata.get('total_departments', 'N/A'):,}")
        print(f"  Total Aisles: {self.metadata.get('total_aisles', 'N/A'):,}")
        print(f"  Total Order Items: {self.metadata.get('total_order_items', 'N/A'):,}")
        print(f"  Date Range Days: {self.metadata.get('date_range_days', 'N/A')}")
        
    def execute_sql(self, query: str) -> pd.DataFrame:
        if not self.conn:
            raise RuntimeError("Not connected to database")
        return self.conn.execute(query).df()
    
    def execute_sql_file(self, sql_file: Path) -> pd.DataFrame:
        with open(sql_file, 'r') as f:
            query = f.read()
        return self.execute_sql(query)
    
    def get_table_info(self, table_name: str) -> pd.DataFrame:
        query = f"DESCRIBE {table_name}"
        return self.execute_sql(query)
        
    def preview_table(self, table_name: str, n: int = 5) -> pd.DataFrame:
        query = f"SELECT * FROM {table_name} LIMIT {n}"
        return self.execute_sql(query)


def quick_load(data_dir: str = "data", use_cache: bool = True) -> InstacartDataLoader:
    loader = InstacartDataLoader(data_dir=data_dir, use_cache=use_cache)
    loader.connect()
    loader.load_all_tables()
    return loader
