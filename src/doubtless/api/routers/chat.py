import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
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

from doubtless.domain.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)
from doubtless.rag.agent import DoubtContext, rag_agent
from doubtless.storage import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/{video_id}", response_model=ChatHistoryResponse)
def get_chat_history(video_id: str) -> ChatHistoryResponse:
    """Retrieve full doubt-solving message history for a specific video."""
    if not db.get_video(video_id):
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )

    return ChatHistoryResponse(
        video_id=video_id,
        messages=db.get_messages(video_id),
    )


def _sse(data: dict[str, Any]) -> str:
    """Format a dictionary payload as a Server-Sent Event (SSE) frame."""
    return f"data: {json.dumps(data)}\n\n"


def _safe_add_message(
    video_id: str,
    role: Literal["user", "assistant"],
    content: str,
) -> None:
    """Persist a chat message safely with error suppression."""
    try:
        db.add_message(video_id, role=role, content=content)
    except Exception as exc:
        logger.error(
            "Failed to persist %s message for video %s: %s",
            role,
            video_id,
            exc,
        )


async def _stream_chat_events(
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
                    yield _sse({"type": "status", "message": status})

                elif isinstance(event, FunctionToolResultEvent):
                    yield _sse({"type": "status", "message": "Synthesizing answer..."})

                elif (
                    isinstance(event, PartStartEvent)
                    and isinstance(event.part, TextPart)
                    and event.part.content
                ):
                    chunk = event.part.content
                    accumulated_tokens.append(chunk)
                    yield _sse({"type": "token", "delta": chunk})

                elif (
                    isinstance(event, PartDeltaEvent)
                    and isinstance(event.delta, TextPartDelta)
                    and event.delta.content_delta
                ):
                    chunk = event.delta.content_delta
                    accumulated_tokens.append(chunk)
                    yield _sse({"type": "token", "delta": chunk})

                elif isinstance(event, AgentRunResultEvent):
                    full_reply = str(event.result.output)
                    if not saved:
                        _safe_add_message(
                            target_id,
                            role="assistant",
                            content=full_reply,
                        )
                        saved = True
                    yield _sse(
                        {
                            "type": "done",
                            "reply": full_reply,
                            "video_id": target_id,
                        }
                    )

        # Fallback if AgentRunResultEvent wasn't triggered
        if not saved and accumulated_tokens:
            full_reply = "".join(accumulated_tokens)
            _safe_add_message(target_id, role="assistant", content=full_reply)
            saved = True
            yield _sse(
                {
                    "type": "done",
                    "reply": full_reply,
                    "video_id": target_id,
                }
            )

    except asyncio.CancelledError:
        logger.info("Client disconnected from chat stream for video %s", target_id)
        raise

    except UsageLimitExceeded as exc:
        logger.warning(
            "Tool request limit exceeded during chat stream for video %s: %s",
            target_id,
            exc,
        )
        limit_msg = (
            "I reached the maximum search limit while researching your question. "
            "Please try asking a more specific doubt."
        )
        if not saved:
            _safe_add_message(target_id, role="assistant", content=limit_msg)
            saved = True
        yield _sse(
            {
                "type": "error",
                "message": "Search limit reached",
                "fallback": limit_msg,
            }
        )

    except Exception as exc:
        logger.exception("Error during chat stream execution: %s", exc)
        fallback_msg = (
            f'Regarding "{video_title}":\n\n'
            f'I received your question: "{student_question}".\n\n'
            f"(Doubt resolution assistant active for video `{target_id}`. "
            f"Note: RAG provider status: {exc})"
        )
        if not saved:
            _safe_add_message(target_id, role="assistant", content=fallback_msg)
            saved = True
        yield _sse(
            {
                "type": "error",
                "message": str(exc),
                "fallback": fallback_msg,
            }
        )


@router.post("")
async def ask_doubt(
    request: ChatRequest,
    raw_request: Request,
) -> Any:
    """Submit a student doubt, persist it, and generate an answer (SSE or JSON)."""
    target_id = (request.video_id or "").strip()
    if not target_id:
        raise HTTPException(
            status_code=400,
            detail="video_id is required to submit a doubt for a lecture video",
        )

    video = db.get_video(target_id)
    if not video:
        raise HTTPException(
            status_code=404,
            detail=f"Video '{target_id}' not found",
        )

    if video.status != "ready":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Video lecture is currently {video.status}. Doubt solver will "
                "be available once speech transcription and indexing complete."
            ),
        )

    q = request.message.strip()
    if not q:
        raise HTTPException(
            status_code=400,
            detail="message cannot be empty",
        )

    # 1. Convert prior database messages to native Pydantic AI message history
    history: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content=m.content)])
        if m.role == "user"
        else ModelResponse(parts=[TextPart(content=m.content)])
        for m in db.get_messages(target_id, limit=6)
    ]

    # 2. Save student question immediately
    _safe_add_message(target_id, role="user", content=q)

    # 3. Resolve doubt context & clean student prompt
    video_title = video.title
    prompt = q
    deps = DoubtContext(video_id=target_id, current_time=request.current_time)

    # Check for SSE streaming request
    accept_header = raw_request.headers.get("accept", "")
    wants_stream = (
        "text/event-stream" in accept_header
        or raw_request.query_params.get("stream") == "true"
    )

    if wants_stream:
        return StreamingResponse(
            _stream_chat_events(
                prompt=prompt,
                deps=deps,
                history=history,
                target_id=target_id,
                video_title=video_title,
                student_question=q,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Standard non-streaming JSON response
    reply: str
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
            f'I received your question: "{q}".\n\n'
            f"(Doubt resolution assistant active for video `{target_id}`. "
            f"Note: RAG provider status: {exc})"
        )

    _safe_add_message(target_id, role="assistant", content=reply)
    return ChatResponse(reply=reply, video_id=target_id)
