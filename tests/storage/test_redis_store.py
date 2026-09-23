"""Unit tests for Redis storage utilities and progress tracking."""

import json
from unittest.mock import MagicMock, patch

from doubtless.storage import redis_store


def test_ping_redis_success_and_failure() -> None:
    """ping_redis returns True on responsive client and False on exception."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    with patch.object(redis_store, "_get_client", return_value=mock_client):
        assert redis_store.ping_redis() is True

    mock_client.ping.side_effect = ConnectionError("unreachable")
    with patch.object(redis_store, "_get_client", return_value=mock_client):
        assert redis_store.ping_redis() is False


def test_set_and_get_transcode_progress() -> None:
    """Setting progress writes JSON payload and getting progress reads it."""
    mock_client = MagicMock()
    with patch.object(redis_store, "_get_client", return_value=mock_client):
        redis_store.set_transcode_progress("vid_123", 0.75, stage="transcribing")
        mock_client.set.assert_called_once()
        args, kwargs = mock_client.set.call_args
        assert args[0] == "transcode:prog:vid_123"
        payload = json.loads(args[1])
        assert payload["progress"] == 0.75
        assert payload["stage"] == "transcribing"

        # Test get_transcode_progress
        mock_client.mget.return_value = [
            json.dumps(
                {"progress": 0.75, "stage": "transcribing", "message": "working"}
            )
        ]
        prog = redis_store.get_transcode_progress("vid_123")
        assert prog["progress"] == 0.75
        assert prog["stage"] == "transcribing"
        assert prog["message"] == "working"


def test_get_transcode_progress_batch() -> None:
    """Batch progress retrieves multiple keys and parses them gracefully."""
    mock_client = MagicMock()
    stored_json = json.dumps(
        {"progress": 0.5, "stage": "indexing", "message": "50% done"}
    )
    mock_client.mget.return_value = [stored_json, None]

    with patch.object(redis_store, "_get_client", return_value=mock_client):
        batch = redis_store.get_transcode_progress_batch(["vid_1", "vid_2"])
        assert batch["vid_1"]["progress"] == 0.5
        assert batch["vid_1"]["stage"] == "indexing"
        assert batch["vid_2"]["progress"] == 0.0
