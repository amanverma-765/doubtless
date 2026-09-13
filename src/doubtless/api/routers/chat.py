"""Chat and doubt-solving router with persistent SQLite history and RAG integration."""

from fastapi import APIRouter

from doubtless.domain.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)
from doubtless.storage import db

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/{video_id}", response_model=ChatHistoryResponse)
def get_chat_history(video_id: str) -> ChatHistoryResponse:
    """Retrieve full doubt-solving message history for a specific video."""
    return ChatHistoryResponse(
        video_id=video_id,
        messages=db.get_messages(video_id),
    )


@router.post("", response_model=ChatResponse)
async def ask_doubt(request: ChatRequest) -> ChatResponse:
    """Submit a student doubt, persist it, and generate an answer via RAG agent."""
    target_id = request.video_id
    if not target_id:
        latest = db.get_latest_video()
        if latest:
            target_id = latest.id

    q = request.message.strip()
    if not target_id:
        return ChatResponse(
            reply=(
                "Please select or upload a lecture video first so I can "
                "resolve your doubts."
            ),
            video_id=None,
        )

    # 1. Save student question
    db.add_message(target_id, role="user", content=q)

    # 2. Resolve doubt via RAG Agent or fallback
    video = db.get_video(target_id)
    video_title = video.title if video else target_id

    # Format previous conversation history if provided
    prompt = q
    if request.history:
        recent = request.history[-6:]
        formatted_history = "\n".join(
            f"{m.role.capitalize()}: {m.content}" for m in recent
        )
        prompt = (
            f"Previous conversation context:\n{formatted_history}\n\n"
            f"Current student question: {q}"
        )

    reply: str
    try:
        from doubtless.rag.agent import rag_agent

        # Run Pydantic AI RAG agent
        agent_result = await rag_agent.run(prompt)
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
