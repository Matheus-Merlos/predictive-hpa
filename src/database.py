import logging as logger
import duckdb
import pandas as pd
from pandas import DataFrame

DB_FILE = "/var/lib/predictive-hpa/duckdb.db"

class DuckDBConnection:
    def __init__(self, database_path: str) -> None:
        self.__database_path = database_path
        self.__connection = None


    def __enter__(self):
        self.__connection = duckdb.connect(self.__database_path)
        self.__connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics_history (
                timestamp TIMESTAMP UNIQUE,
                cpu_usage DOUBLE,
                mem_usage DOUBLE,
                rps DOUBLE,
                replicas DOUBLE
            );
        """)

        return self


    def __exit__(self, exc_type, exc, tb):
        if self.__connection:
            self.__connection.close()

        if exc_type is not None:
            logger.exception(f'Error in duckdb connection.')


    def append_metric(self, df: DataFrame) -> None:
        self.__connection.execute("""
            INSERT INTO metrics_history 
            SELECT timestamp, cpu_usage, mem_usage, rps, replicas 
            FROM df 
            ON CONFLICT (timestamp) DO NOTHING
        """)


    def get_days_count(self) -> int:
        result = self.__connection.execute("SELECT COUNT(DISTINCT CAST(timestamp AS DATE)) FROM metrics_history").fetchone()
        return result[0] if result else 0


    def get_all_historical_data(self) -> DataFrame:
        df = self.__connection.execute("SELECT * FROM metrics_history ORDER BY timestamp AS").df()
        return df