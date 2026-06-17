import duckdb
import pandas as pd
from pandas import DataFrame

DB_FILE = "predictive_hpa.db"

def init_db() -> None:
    connection = duckdb.connect(DB_FILE)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics_history (
            timestamp TIMESTAMP UNIQUE,
            cpu_usage DOUBLE,
            mem_usage DOUBLE,
            rps DOUBLE,
            replicas DOUBLE
        );
    """)

    connection.close()

def append_metric(df: DataFrame) -> None:
    connection = duckdb.connect(DB_FILE)
    connection.execute("""
        INSERT INTO metrics_history 
        SELECT timestamp, cpu_usage, mem_usage, rps, replicas 
        FROM df 
        ON CONFLICT (timestamp) DO NOTHING
    """)
    connection.close()

def get_days_count() -> int:
    connection = duckdb.connect(DB_FILE)
    result = connection.execute("SELECT COUNT(DISTINCT CAST(timestamp AS DATE)) FROM metrics_history").fetchone()
    connection.close()
    return result[0] if result else 0

def get_all_historical_data() -> DataFrame:
    connection = duckdb.connect(DB_FILE)
    df = connection.execute("SELECT * FROM metrics_history ORDER BY timestamp AS").df()
    connection.close()
    return df