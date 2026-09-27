"""Application service orchestrating AI chat sessions, SSE streams, and persistence."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Literal

import logfire
from pydantic_ai import AgentRunResultEvent, UsageLimits
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
from doubtless.rag.agent import DoubtContext, rag_agent
from doubtless.storage.repositories import chat_repo, study_repo
from doubtless.study.context import get_transcript_dialogue_window

_logger = logging.getLogger(__name__)


def format_sse(data: dict[str, Any]) -> str:
    """Format a dictionary payload as a Server-Sent Event (SSE) frame."""
    return f"data: {json.dumps(data)}\n\n"


def safe_add_message(
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


def build_chat_history(video_id: str, limit: int = 6) -> list[ModelMessage]:
    """Convert prior database messages to native Pydantic AI message history."""
    return [
        ModelRequest(parts=[UserPromptPart(content=m.content)])
        if m.role == "user"
        else ModelResponse(parts=[TextPart(content=m.content)])
        for m in chat_repo.get_messages(video_id, limit=limit)
    ]


def build_chat_prompt(
    video_id: str,
    current_time: float,
    question: str,
) -> tuple[str, DoubtContext]:
    """Enrich the student question with playhead dialogue, chapter, and timestamp."""
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
    if dialogue:
        context_lines.append(f"[SPOKEN DIALOGUE AROUND {ts_formatted}]:\n{dialogue}")
    else:
        context_lines.append(
            f"[STATUS: No spoken dialogue recorded around {ts_formatted}. "
            "Teacher is silent, writing on board, or working through problems.]"
        )

    prompt = f"{'\n'.join(context_lines)}\n\nStudent Doubt / Question: {question}"
    deps = DoubtContext(video_id=video_id, current_time=current_time)
    return prompt, deps


async def stream_chat_events(
    prompt: str,
    deps: DoubtContext,
    history: list[ModelMessage],
    target_id: str,
    video_title: str,
    student_question: str,
) -> AsyncGenerator[str]:
    """Execute Pydantic AI agent and stream SSE events to client."""
    accumulated_tokens: list[str] = []
    saved = False

    with logfire.span("chat.stream", video_id=target_id, video_title=video_title):
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
                        if tool_name == "get_chapter_notes":
                            status = "Reviewing chapter notes & lecture outline..."
                        elif tool_name == "search_lecture":
                            status = "Searching lecture transcript..."
                        elif tool_name == "search_books":
                            status = "Searching NCERT textbooks..."
                        else:
                            status = f"Consulting {tool_name}..."
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
                            safe_add_message(
                                target_id,
                                role="assistant",
                                content=full_reply,
                            )
                            saved = True
                        yield format_sse(
                            {
                                "type": "done",
                                "reply": full_reply,
                                "video_id": target_id,
                            }
                        )

            # Fallback if AgentRunResultEvent wasn't triggered
            if not saved and accumulated_tokens:
                full_reply = "".join(accumulated_tokens)
                safe_add_message(target_id, role="assistant", content=full_reply)
                saved = True
                yield format_sse(
                    {
                        "type": "done",
                        "reply": full_reply,
                        "video_id": target_id,
                    }
                )

        except asyncio.CancelledError:
            logfire.info(
                "Chat stream disconnected by client for video {video_id}",
                video_id=target_id,
            )
            _logger.info("Client disconnected from chat stream for video %s", target_id)
            raise

        except UsageLimitExceeded as exc:
            logfire.warning(
                "Chat stream tool limit exceeded for video {video_id}: {error}",
                video_id=target_id,
                error=str(exc),
            )
            _logger.warning(
                "Tool request limit exceeded during chat stream for video %s: %s",
                target_id,
                exc,
            )
            limit_msg = (
                "I reached the maximum search limit while researching your question. "
                "Please try asking a more specific doubt."
            )
            if not saved:
                safe_add_message(target_id, role="assistant", content=limit_msg)
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
                video_id=target_id,
                error=str(exc),
            )
            _logger.exception("Error during chat stream execution: %s", exc)
            fallback_msg = (
                f'Regarding "{video_title}":\n\n'
                f'I received your question: "{student_question}".\n\n'
                f"(Doubt resolution assistant active for video `{target_id}`. "
                f"Note: RAG provider status: {exc})"
            )
            if not saved:
                safe_add_message(target_id, role="assistant", content=fallback_msg)
                saved = True
            yield format_sse(
                {
                    "type": "error",
                    "message": str(exc),
                    "fallback": fallback_msg,
                }
            )


async def generate_chat_reply(
    prompt: str,
    deps: DoubtContext,
    history: list[ModelMessage],
    target_id: str,
    video_title: str,
    student_question: str,
) -> str:
    """Execute single-turn Pydantic AI agent run and return the answer string."""
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
            f'I received your question: "{student_question}".\n\n'
            f"(Doubt resolution assistant active for video `{target_id}`. "
            f"Note: RAG provider status: {exc})"
        )

    safe_add_message(target_id, role="assistant", content=reply)
    return reply
