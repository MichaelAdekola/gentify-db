# utils/db.py
from pathlib import Path
import duckdb, pandas as pd
from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase

_DB_PATH = "gentify.duckdb"                 # sits in project root


class DuckDBClient:
    """
    One-shot loader + a single SQLAlchemy engine that the whole app shares.
    • load_many(...)  - bulk-ingest CSVs into real tables (overwrites each run)
    • run_sql(...)    - return a Pandas DataFrame
    • get_sql_database() - LangChain-friendly wrapper around the same engine
    """

    def __init__(self):
        # Create the engine up-front (only one connection pool in the process)
        self.engine = create_engine(f"duckdb:///{_DB_PATH}")

    # ------------------------------------------------------------------ #
    #  CSV → DuckDB (uses a throw-away, write-mode connection)            #
    # ------------------------------------------------------------------ #
    def load_many(self, mapping: dict[str, str]) -> dict[str, tuple[int, int]]:
        """
        mapping = {"sales": "sample_data/sales.csv", ...}
        Returns {"sales": (rows, cols), ...}
        """
        stats: dict[str, tuple[int, int]] = {}
        from pathlib import Path

        # 🔑 Close any idle reader connections first – otherwise DuckDB
        #   thinks two writers are live and throws the conflict error.
        self.engine.dispose(close=True)

        # now open *one* writer connection
        with self.engine.begin() as conn:
            for table, csv_path in mapping.items():
                abs_path = Path(csv_path).resolve().as_posix()

                conn.exec_driver_sql(f"""
                    CREATE OR REPLACE TABLE {table} AS
                    SELECT * FROM read_csv_auto('{abs_path}', HEADER = TRUE)
                """)

                rows = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {table}").scalar_one()
                cols = conn.exec_driver_sql(f"PRAGMA table_info('{table}')").rowcount
                stats[table] = (rows, cols)

        return stats

    # ------------------------------------------------------------------ #
    #  Query helpers (read-only via SQLAlchemy engine)                    #
    # ------------------------------------------------------------------ #
    def run_sql(self, sql: str) -> pd.DataFrame:
        """Execute SQL via SQLAlchemy, return a pandas DataFrame."""
        from sqlalchemy import text

        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())

        return df

    def get_sql_database(self) -> SQLDatabase:
        """Supply to LangChain’s create_sql_query_chain()."""
        return SQLDatabase(self.engine)
