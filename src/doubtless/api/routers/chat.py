"""Chat and doubt-solving router with persistent SQLite history and RAG integration."""

from fastapi import APIRouter, HTTPException
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from doubtless.domain.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)
from doubtless.rag.agent import rag_agent
from doubtless.storage import db

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


@router.post("", response_model=ChatResponse)
async def ask_doubt(request: ChatRequest) -> ChatResponse:
    """Submit a student doubt, persist it, and generate an answer via RAG agent."""
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
        for m in db.get_messages(target_id)[-6:]
    ]

    # 2. Save student question
    db.add_message(target_id, role="user", content=q)

    # 3. Resolve doubt via RAG Agent or fallback
    video_title = video.title

    reply: str
    try:
        # Run Pydantic AI RAG agent with native multi-turn message history
        agent_result = await rag_agent.run(q, message_history=history)
        reply = str(agent_result.output)
    except Exception as exc:
        reply = (
            f'Regarding "{video_title}":\n\n'
            f'I received your question: "{q}".\n\n'
            f"(Doubt resolution assistant active for video `{target_id}`. "
            f"Note: RAG provider status: {exc})"
        )

    # 3. Save assistant reply
    db.add_message(target_id, role="assistant", content=reply)

    return ChatResponse(reply=reply, video_id=target_id)
