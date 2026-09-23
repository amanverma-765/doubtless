"""Integration tests for video endpoints: CRUD, status, config, and deletion."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from doubtless.storage import db


def test_get_upload_config(client: TestClient) -> None:
    """Config endpoint returns max upload size and allowed extensions."""
    res = client.get("/api/v1/videos/config")
    assert res.status_code == 200
    data = res.json()
    assert "max_upload_bytes" in data
    assert "mp4" in data["allowed_extensions"]


def test_list_all_videos_empty(client: TestClient) -> None:
    """Listing videos when none exist returns empty list."""
    res = client.get("/api/v1/videos")
    assert res.status_code == 200
    assert res.json() == []


def test_list_all_videos_populated(client: TestClient) -> None:
    """Listing videos returns registered videos with correct progress."""
    db.create_video("vid_1", "Lecture 1", "vid_1.mp4", status="ready")
    res = client.get("/api/v1/videos")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == "vid_1"
    assert data[0]["progress"] == 1.0


def test_get_video_by_id(client: TestClient) -> None:
    """Get video by ID returns 200 for existing and 404 for missing."""
    db.create_video("vid_exist", "Physics Lecture", "vid_exist.mp4")
    res = client.get("/api/v1/videos/vid_exist")
    assert res.status_code == 200
    assert res.json()["title"] == "Physics Lecture"

    res_404 = client.get("/api/v1/videos/missing_vid")
    assert res_404.status_code == 404


def test_get_video_status(client: TestClient) -> None:
    """Video status reports idle for missing, ready for ready, and error for error."""
    assert client.get("/api/v1/videos/unknown/status").json()["state"] == "idle"

    db.create_video("vid_ready", "Ready Vid", "vid_ready.mp4", status="ready")
    res_ready = client.get("/api/v1/videos/vid_ready/status")
    assert res_ready.json()["state"] == "ready"
    assert res_ready.json()["progress"] == 1.0

    db.create_video("vid_err", "Error Vid", "vid_err.mp4", status="error")
    db.update_video("vid_err", error="Corrupt file")
    res_err = client.get("/api/v1/videos/vid_err/status")
    assert res_err.json()["state"] == "error"
    assert res_err.json()["error"] == "Corrupt file"


def test_delete_video_by_id(client: TestClient) -> None:
    """Delete video triggers cascade deletion and removes record."""
    db.create_video("vid_del", "Delete Me", "vid_del.mp4")
    with patch("doubtless.api.routers.video.cascade_delete_video") as mock_cascade:
        mock_cascade.return_value = {"deleted": True, "video_id": "vid_del"}
        res = client.delete("/api/v1/videos/vid_del")
        assert res.status_code == 200
        assert res.json()["id"] == "vid_del"
        mock_cascade.assert_called_once_with("vid_del")


def test_delete_video_by_id_404(client: TestClient) -> None:
    """Deleting non-existent video returns 404."""
    res = client.delete("/api/v1/videos/nonexistent_vid")
    assert res.status_code == 404


def test_upload_video_invalid_extension(client: TestClient) -> None:
    """Upload endpoint rejects invalid file extension with 422."""
    res = client.put("/api/v1/videos/upload?name=document.pdf", content=b"dummy")
    assert res.status_code == 422
