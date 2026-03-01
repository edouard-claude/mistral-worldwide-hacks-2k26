"""DuckDB schema initialization.

This module provides a standalone schema init function that can be called
from scripts or during app startup. The actual table creation logic lives
in GameStore.init_schema() — this module re-exports it for convenience.
"""

from src.clients.duckdb_store import GameStore
from src.core.config import get_settings


def init_database() -> None:
    """Initialize the DuckDB database with all tables.

    Creates the database file and all required tables with spatial extension.
    Safe to call multiple times (uses CREATE TABLE IF NOT EXISTS).
    """
    settings = get_settings()
    store = GameStore(settings)
    store.init_schema()
    store.close()


if __name__ == "__main__":
    init_database()
    print("Database schema initialized successfully.")
