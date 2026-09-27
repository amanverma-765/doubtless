"""Global pytest fixtures and shared testing utilities."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from doubtless.api.app import app
from doubtless.storage import connection


@pytest.fixture
def temp_db(tmp_path: Path) -> Generator[Path]:
    """Provide an isolated temporary SQLite database path for testing."""
    test_db = tmp_path / "test_doubtless.db"
    with patch.object(connection, "_DB_PATH", test_db):
        connection.reset_db_state(test_db)
        connection.init_db()
        try:
            yield test_db
        finally:
            connection.reset_db_state()


@pytest.fixture
def client(temp_db: Path) -> Generator[TestClient]:
    """Provide a FastAPI TestClient configured with an isolated test database."""
    with TestClient(app) as test_client:
        yield test_client
