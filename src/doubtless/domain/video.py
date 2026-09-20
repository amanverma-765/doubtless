"""Video domain entities, state types, and API schemas."""

from typing import Literal

from pydantic import BaseModel

VideoStatusState = Literal["idle", "uploading", "processing", "ready", "error"]


class VideoRecord(BaseModel):
    """Internal database record representing a video asset."""

    id: str
    title: str
    filename: str
    task_id: str | None = None
    playlist: str | None = None
    poster: str | None = None
    status: VideoStatusState = "uploading"
    error: str | None = None
    created_at: str


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
    stage: str | None = None
    stage_message: str | None = None
    error: str | None = None
    created_at: str


class VideoStatusResponse(BaseModel):
    """Schema returned when querying transcoding or upload status."""

    state: VideoStatusState
    progress: float = 0.0
    stage: str | None = None
    stage_message: str | None = None
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
