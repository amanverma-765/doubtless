"""Pydantic schemas and Data Transfer Objects for API contracts."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from doubtless.domain.types import MessageRole, VideoStatusState


class VideoItemResponse(BaseModel):
    """Schema representing an individual video in listings."""

    id: str
    title: str
    filename: str | None = None
    task_id: str | None = None
    playlist: str | None = None
    poster: str | None = None
    status: VideoStatusState = "ready"
    progress: float = 1.0
    error: str | None = None
    created_at: str


class VideoStatusResponse(BaseModel):
    """Schema returned when querying transcoding or upload status."""

    state: VideoStatusState
    progress: float = 0.0
    id: str | None = None
    playlist: str | None = None
    error: str | None = None


class UploadAcceptedResponse(BaseModel):
    """Response returned upon accepting a video upload stream."""

    id: str


class VideoDeleteResponse(BaseModel):
    """Payload returned after successful video deletion."""

    status: str = "deleted"
    id: str


class UploadConfigResponse(BaseModel):
    """Configuration constraints for clients uploading media."""

    max_upload_bytes: int
    allowed_extensions: list[str]


class ChatMessage(BaseModel):
    """Schema representing an individual chat message."""

    role: MessageRole
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ChatRequest(BaseModel):
    """Request payload for submitting a student doubt."""

    message: str
    video_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response returned by the doubt-solving assistant."""

    reply: str
    video_id: str | None = None


class ChatHistoryResponse(BaseModel):
    """History of doubt-solving messages associated with a video."""

    video_id: str
    messages: list[ChatMessage]


class HealthResponse(BaseModel):
    """Service liveness and dependency health status."""

    status: Literal["ok", "degraded", "error"]
    redis: bool
    data_dir: bool
    db: bool
