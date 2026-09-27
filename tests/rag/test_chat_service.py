"""Unit tests for the deep chat service module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from doubtless.rag.chat_service import chat_reply, chat_stream
from doubtless.storage.repositories import chat_repo, video_repo


@pytest.mark.asyncio
async def test_chat_reply_success() -> None:
    """chat_reply saves message, invokes agent, saves reply, and returns text."""
    video_repo.create_video("vid_reply_test", "Physics 101", "p101.mp4", status="ready")

    mock_run_result = MagicMock()
    mock_run_result.output = "Energy is conserved."

    with patch(
        "doubtless.rag.chat_service.rag_agent.run", new_callable=AsyncMock
    ) as mock_agent_run:
        mock_agent_run.return_value = mock_run_result

        reply = await chat_reply(
            "vid_reply_test", "What is the first law?", current_time=12.0
        )
        assert reply == "Energy is conserved."

    messages = chat_repo.get_messages("vid_reply_test")
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert "What is the first law?" in messages[0].content
    assert messages[1].role == "assistant"
    assert "Energy is conserved." in messages[1].content


@pytest.mark.asyncio
async def test_chat_reply_fallback_on_error() -> None:
    """chat_reply catches agent failures, returns fallback message, and persists it."""
    video_repo.create_video(
        "vid_reply_err", "Chemistry 101", "c101.mp4", status="ready"
    )

    with patch(
        "doubtless.rag.chat_service.rag_agent.run",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Provider offline"),
    ):
        reply = await chat_reply("vid_reply_err", "Explain orbitals", current_time=0.0)
        assert "Chemistry 101" in reply
        assert "Explain orbitals" in reply

    messages = chat_repo.get_messages("vid_reply_err")
    assert len(messages) == 2
    assert messages[1].role == "assistant"
    assert "Chemistry 101" in messages[1].content


@pytest.mark.asyncio
async def test_chat_stream_fallback_on_error() -> None:
    """chat_stream yields error frame and persists fallback message on agent error."""
    video_repo.create_video("vid_stream_err", "Math 101", "m101.mp4", status="ready")

    with patch(
        "doubtless.rag.chat_service.rag_agent.run_stream_events",
        side_effect=RuntimeError("Stream failed"),
    ):
        frames: list[str] = []
        async for frame in chat_stream(
            "vid_stream_err", "What is pi?", current_time=5.0
        ):
            frames.append(frame)

        assert any("error" in f for f in frames)
        assert any("Math 101" in f for f in frames)

    messages = chat_repo.get_messages("vid_stream_err")
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
