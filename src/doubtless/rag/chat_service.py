"""Application service orchestrating AI chat sessions, SSE streams, and persistence."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Literal

import logfire
from pydantic_ai import AgentRunResultEvent, BinaryContent, UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    UserPromptPart,
)

from doubtless.core.formatting import format_timestamp
from doubtless.media.transcoder import extract_frame_at_timestamp
from doubtless.rag.agent import DoubtContext, rag_agent
from doubtless.storage import file_storage
from doubtless.storage.repositories import chat_repo, study_repo, video_repo
from doubtless.study.context import get_transcript_dialogue_window

_logger = logging.getLogger(__name__)

_TOOL_STATUS: dict[str, str] = {
    "get_chapter_notes": "Reviewing chapter notes & lecture outline...",
    "search_lecture": "Searching lecture transcript...",
    "search_books": "Searching NCERT textbooks...",
}


def format_sse(data: dict[str, Any]) -> str:
    """Format a dictionary payload as a Server-Sent Event (SSE) frame."""
    return f"data: {json.dumps(data)}\n\n"


def _safe_add_message(
    video_id: str,
    role: Literal["user", "assistant"],
    content: str,
) -> None:
    """Persist a chat message safely with error suppression."""
    try:
        chat_repo.add_message(video_id, role=role, content=content)
    except Exception as exc:
        _logger.error(
            "Failed to persist %s message for video %s: %s",
            role,
            video_id,
            exc,
        )


def _build_chat_history(video_id: str, limit: int = 6) -> list[ModelMessage]:
    """Convert prior database messages to native Pydantic AI message history."""
    return [
        ModelRequest(parts=[UserPromptPart(content=m.content)])
        if m.role == "user"
        else ModelResponse(parts=[TextPart(content=m.content)])
        for m in chat_repo.get_messages(video_id, limit=limit)
    ]


def _build_chat_prompt(
    video_id: str,
    current_time: float,
    question: str,
) -> tuple[str | list[str | BinaryContent], DoubtContext]:
    """Enrich doubt with playhead dialogue, chapter, time, and video frame."""
    ts_formatted = format_timestamp(current_time)
    dialogue = get_transcript_dialogue_window(
        video_id,
        current_time,
        window_before=90.0,
        window_after=15.0,
    )
    chapter = study_repo.get_chapter_at_time(video_id, current_time)

    context_lines: list[str] = [
        f"[CURRENT PLAYHEAD TIMESTAMP: {ts_formatted}]",
    ]
    if chapter:
        context_lines.append(f"[CURRENT TOPIC / CHAPTER: {chapter.title}]")

    media_path = file_storage.find_video_media_path(video_id)
    frame_bytes: bytes | None = None
    if media_path:
        frame_bytes = extract_frame_at_timestamp(media_path, current_time)

    if frame_bytes:
        context_lines.append(
            f"[ON-SCREEN VIDEO FRAME: Attached JPEG frame captured at {ts_formatted}. "
            "Inspect board notes, slides, equations, and diagrams shown on screen.]"
        )

    if dialogue:
        context_lines.append(f"[SPOKEN DIALOGUE AROUND {ts_formatted}]:\n{dialogue}")
    else:
        context_lines.append(
            f"[STATUS: No spoken dialogue recorded around {ts_formatted}. "
            "Teacher is silent, writing on board, or working through problems.]"
        )

    prompt_text = f"{'\n'.join(context_lines)}\n\nStudent Doubt / Question: {question}"
    deps = DoubtContext(video_id=video_id, current_time=current_time)

    if frame_bytes:
        return [
            prompt_text,
            BinaryContent(data=frame_bytes, media_type="image/jpeg"),
        ], deps

    return prompt_text, deps


async def chat_stream(
    video_id: str,
    question: str,
    current_time: float = 0.0,
    video_title: str | None = None,
) -> AsyncGenerator[str]:
    """Orchestrate doubt-solving session, persisting history and yielding SSE frames."""
    if video_title is None:
        v = video_repo.get_video(video_id)
        video_title = v.title if v else "Lecture Video"

    # 1. Build history and enriched prompt before persisting current question
    history = _build_chat_history(video_id, limit=6)
    prompt, deps = _build_chat_prompt(video_id, current_time, question)

    # 2. Save user inquiry
    _safe_add_message(video_id, role="user", content=question)

    accumulated_tokens: list[str] = []
    saved = False

    with logfire.span("chat.stream", video_id=video_id, video_title=video_title):
        try:
            async with rag_agent.run_stream_events(
                prompt,
                deps=deps,
                message_history=history,
                usage_limits=UsageLimits(request_limit=5),
            ) as events:
                async for event in events:
                    if isinstance(event, FunctionToolCallEvent):
                        tool_name = getattr(event.part, "tool_name", "tool")
                        status = _TOOL_STATUS.get(
                            tool_name, f"Consulting {tool_name}..."
                        )
                        yield format_sse({"type": "status", "message": status})

                    elif isinstance(event, FunctionToolResultEvent):
                        yield format_sse(
                            {"type": "status", "message": "Synthesizing answer..."}
                        )

                    elif (
                        isinstance(event, PartStartEvent)
                        and isinstance(event.part, TextPart)
                        and event.part.content
                    ):
                        chunk = event.part.content
                        accumulated_tokens.append(chunk)
                        yield format_sse({"type": "token", "delta": chunk})

                    elif (
                        isinstance(event, PartDeltaEvent)
                        and isinstance(event.delta, TextPartDelta)
                        and event.delta.content_delta
                    ):
                        chunk = event.delta.content_delta
                        accumulated_tokens.append(chunk)
                        yield format_sse({"type": "token", "delta": chunk})

                    elif isinstance(event, AgentRunResultEvent):
                        full_reply = str(event.result.output)
                        if not saved:
                            _safe_add_message(
                                video_id,
                                role="assistant",
                                content=full_reply,
                            )
                            saved = True
                        yield format_sse(
                            {
                                "type": "done",
                                "reply": full_reply,
                                "video_id": video_id,
                            }
                        )

            # Fallback if AgentRunResultEvent wasn't triggered
            if not saved and accumulated_tokens:
                full_reply = "".join(accumulated_tokens)
                _safe_add_message(video_id, role="assistant", content=full_reply)
                saved = True
                yield format_sse(
                    {
                        "type": "done",
                        "reply": full_reply,
                        "video_id": video_id,
                    }
                )

        except asyncio.CancelledError:
            logfire.info(
                "Chat stream disconnected by client for video {video_id}",
                video_id=video_id,
            )
            _logger.info("Client disconnected from chat stream for video %s", video_id)
            raise

        except UsageLimitExceeded as exc:
            logfire.warning(
                "Chat stream tool limit exceeded for video {video_id}: {error}",
                video_id=video_id,
                error=str(exc),
            )
            _logger.warning(
                "Tool request limit exceeded during chat stream for video %s: %s",
                video_id,
                exc,
            )
            limit_msg = (
                "I reached the maximum search limit while researching your question. "
                "Please try asking a more specific doubt."
            )
            if not saved:
                _safe_add_message(video_id, role="assistant", content=limit_msg)
                saved = True
            yield format_sse(
                {
                    "type": "error",
                    "message": "Search limit reached",
                    "fallback": limit_msg,
                }
            )

        except Exception as exc:
            logfire.exception(
                "Chat stream failed for video {video_id}: {error}",
                video_id=video_id,
                error=str(exc),
            )
            _logger.exception("Error during chat stream execution: %s", exc)
            fallback_msg = (
                f'Regarding "{video_title}":\n\n'
                f'I received your question: "{question}".\n\n'
                f"(Doubt resolution assistant active for video `{video_id}`. "
                f"Note: RAG provider status: {exc})"
            )
            if not saved:
                _safe_add_message(video_id, role="assistant", content=fallback_msg)
                saved = True
            yield format_sse(
                {
                    "type": "error",
                    "message": str(exc),
                    "fallback": fallback_msg,
                }
            )


async def chat_reply(
    video_id: str,
    question: str,
    current_time: float = 0.0,
    video_title: str | None = None,
) -> str:
    """Orchestrate single-turn doubt resolution, returning answer string."""
    if video_title is None:
        v = video_repo.get_video(video_id)
        video_title = v.title if v else "Lecture Video"

    # 1. Build history and enriched prompt before persisting current question
    history = _build_chat_history(video_id, limit=6)
    prompt, deps = _build_chat_prompt(video_id, current_time, question)

    # 2. Save user inquiry
    _safe_add_message(video_id, role="user", content=question)

    try:
        agent_result = await rag_agent.run(
            prompt,
            deps=deps,
            message_history=history,
            usage_limits=UsageLimits(request_limit=5),
        )
        reply = str(agent_result.output)
    except Exception as exc:
        reply = (
            f'Regarding "{video_title}":\n\n'
            f'I received your question: "{question}".\n\n'
            f"(Doubt resolution assistant active for video `{video_id}`. "
            f"Note: RAG provider status: {exc})"
        )

    _safe_add_message(video_id, role="assistant", content=reply)
    return reply
