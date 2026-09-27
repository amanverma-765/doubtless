"""HTTP router for student doubt-solving chat and SSE streaming."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from doubtless.domain import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)
from doubtless.rag import chat_service
from doubtless.storage.repositories import chat_repo, video_repo

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/{video_id}", response_model=ChatHistoryResponse)
def get_chat_history(video_id: str) -> ChatHistoryResponse:
    """Retrieve full doubt-solving message history for a specific video."""
    if not video_repo.get_video(video_id):
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )

    return ChatHistoryResponse(
        video_id=video_id,
        messages=chat_repo.get_messages(video_id),
    )


@router.delete("/{video_id}")
def clear_chat_history(video_id: str) -> dict[str, Any]:
    """Delete all doubt-solving message history for a specific video."""
    if not video_repo.get_video(video_id):
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )

    deleted_count = chat_repo.clear_messages(video_id)
    return {
        "status": "cleared",
        "video_id": video_id,
        "deleted_count": deleted_count,
    }


@router.post("", response_model=None)
async def ask_doubt(
    request: ChatRequest,
    raw_request: Request,
) -> StreamingResponse | ChatResponse:
    """Submit a student doubt, persist it, and generate an answer (SSE or JSON)."""
    target_id = (request.video_id or "").strip()
    if not target_id:
        raise HTTPException(
            status_code=400,
            detail="video_id is required to submit a doubt for a lecture video",
        )

    video = video_repo.get_video(target_id)
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

    current_time = request.current_time if request.current_time is not None else 0.0

    # Check for SSE streaming request
    accept_header = raw_request.headers.get("accept", "")
    wants_stream = (
        "text/event-stream" in accept_header
        or raw_request.query_params.get("stream") == "true"
    )

    if wants_stream:
        return StreamingResponse(
            chat_service.chat_stream(
                video_id=target_id,
                question=q,
                current_time=current_time,
                video_title=video.title,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    reply = await chat_service.chat_reply(
        video_id=target_id,
        question=q,
        current_time=current_time,
        video_title=video.title,
    )
    return ChatResponse(reply=reply, video_id=target_id)
