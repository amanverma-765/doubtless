"""SQLite connection lifecycle, transaction management, and health checking."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from doubtless.config import DATA_DIR
from doubtless.storage.schema import create_all_tables

_DB_PATH: Path = DATA_DIR / "doubtless.db"
_tables_initialized: bool = False


def reset_db_state(path: Path | None = None) -> None:
    """Reset initialization flag and optionally update database path (for tests)."""
    global _tables_initialized, _DB_PATH
    _tables_initialized = False
    if path is not None:
        _DB_PATH = path


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Ensure database schema tables are created once per lifecycle."""
    global _tables_initialized
    if not _tables_initialized:
        create_all_tables(conn)
        _tables_initialized = True


@contextmanager
def get_db() -> Generator[sqlite3.Connection]:
    """Context manager providing a transactional SQLite connection."""
    conn = sqlite3.connect(_DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    _ensure_tables(conn)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize database directory and create tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_db():
        pass


def check_db_health() -> bool:
    """Verify database read and write capability."""
    try:
        with get_db() as conn:
            row = conn.execute("SELECT 1;").fetchone()
            return bool(row and row[0] == 1)
    except Exception:
        return False
