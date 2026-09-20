"""Chat and doubt-solving schemas and message contracts."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

MessageRole = Literal["user", "assistant", "system"]


class ChatMessage(BaseModel):
    """Schema representing an individual chat message."""

    role: MessageRole
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ChatRequest(BaseModel):
    """Request payload for submitting a student doubt."""

    message: str
    video_id: str
    current_time: float | None = None


class ChatResponse(BaseModel):
    """Response returned by the doubt-solving assistant."""

    reply: str
    video_id: str | None = None


class ChatHistoryResponse(BaseModel):
    """History of doubt-solving messages associated with a video."""

    video_id: str
    messages: list[ChatMessage]
