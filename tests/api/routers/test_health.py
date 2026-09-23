"""Integration tests for health endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_health_check_ok(client: TestClient) -> None:
    """Health check returns 200 and status ok when all systems are healthy."""
    with patch("doubtless.storage.redis_store.ping_redis", return_value=True):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["db"] is True
        assert data["redis"] is True
        assert data["data_dir"] is True


def test_health_check_degraded(client: TestClient) -> None:
    """Health check returns degraded when Redis is unreachable."""
    with patch("doubtless.storage.redis_store.ping_redis", return_value=False):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["redis"] is False
