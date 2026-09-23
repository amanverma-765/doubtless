"""Integration tests for chat endpoints."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from doubtless.api.app import app
from doubtless.storage import db


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient]:
    """Test client using an isolated temporary database."""
    test_db = tmp_path / "test_doubtless_chat_api.db"
    with patch.object(db, "_DB_PATH", test_db):
        db._tables_initialized = False
        db.init_db()
        with TestClient(app) as test_client:
            yield test_client


def test_get_chat_history_404(client: TestClient) -> None:
    """Non-existent video returns 404 for chat history."""
    res = client.get("/api/v1/chat/nonexistent_vid")
    assert res.status_code == 404


def test_clear_chat_history_404(client: TestClient) -> None:
    """Non-existent video returns 404 when clearing chat."""
    res = client.delete("/api/v1/chat/nonexistent_vid")
    assert res.status_code == 404


def test_get_and_clear_chat_history_success(client: TestClient) -> None:
    """Clear chat history removes messages and returns deleted count."""
    db.create_video("vid_chat", "Test Video", "test.mp4")
    db.add_message("vid_chat", role="user", content="Hello")
    db.add_message("vid_chat", role="assistant", content="Hi there")

    # Verify history
    res = client.get("/api/v1/chat/vid_chat")
    assert res.status_code == 200
    assert len(res.json()["messages"]) == 2

    # Clear history
    del_res = client.delete("/api/v1/chat/vid_chat")
    assert del_res.status_code == 200
    data = del_res.json()
    assert data["status"] == "cleared"
    assert data["video_id"] == "vid_chat"
    assert data["deleted_count"] == 2

    # Verify empty history now
    res_after = client.get("/api/v1/chat/vid_chat")
    assert res_after.status_code == 200
    assert len(res_after.json()["messages"]) == 0
