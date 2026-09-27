"""Integration tests for chat endpoints: query, history, and clear history."""

from fastapi.testclient import TestClient

from doubtless.storage.repositories import chat_repo, video_repo


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
    video_repo.create_video("vid_chat", "Test Video", "test.mp4")
    chat_repo.add_message("vid_chat", role="user", content="Hello")
    chat_repo.add_message("vid_chat", role="assistant", content="Hi there")

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


def test_post_chat_validation_errors(client: TestClient) -> None:
    """Test 400 validation on empty fields and 404 on missing video."""
    # Missing video_id
    res_no_vid = client.post("/api/v1/chat", json={"video_id": "", "message": "hi"})
    assert res_no_vid.status_code == 400

    # Nonexistent video
    res_404 = client.post(
        "/api/v1/chat",
        json={"video_id": "nonexistent", "message": "hi"},
    )
    assert res_404.status_code == 404

    # Empty message on existing video
    video_repo.create_video("vid_ready", "Ready", "ready.mp4", status="ready")
    res_empty_msg = client.post(
        "/api/v1/chat",
        json={"video_id": "vid_ready", "message": "   "},
    )
    assert res_empty_msg.status_code == 400


def test_post_chat_conflict_when_not_ready(client: TestClient) -> None:
    """Submitting a doubt to a non-ready video returns 409 conflict."""
    video_repo.create_video("vid_proc", "Processing", "proc.mp4", status="processing")
    res = client.post(
        "/api/v1/chat",
        json={"video_id": "vid_proc", "message": "What is this?"},
    )
    assert res.status_code == 409


def test_post_chat_streaming_success(client: TestClient) -> None:
    """Successful chat submission streams SSE events and saves messages."""
    from unittest.mock import patch

    video_repo.create_video(
        "vid_stream", "Streaming Lecture", "stream.mp4", status="ready"
    )

    async def mock_events(*args, **kwargs):
        yield 'data: {"type": "chunk", "delta": "Test answer"}\n\n'
        yield (
            'data: {"type": "done", "reply": "Test answer", '
            '"video_id": "vid_stream"}\n\n'
        )

    with patch(
        "doubtless.rag.chat_service.stream_chat_events",
        side_effect=mock_events,
    ):
        res = client.post(
            "/api/v1/chat",
            json={
                "video_id": "vid_stream",
                "message": "Explain quantum entanglement",
                "current_time": 42.0,
            },
            headers={"accept": "text/event-stream"},
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        assert '{"type": "chunk", "delta": "Test answer"}' in res.text
        assert '{"type": "done"' in res.text

    # Verify user message was persisted in database
    msgs = chat_repo.get_messages("vid_stream")
    assert any(m.role == "user" and "quantum" in m.content for m in msgs)
