"""System diagnostic and health check schemas."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Service liveness and dependency health status."""

    status: Literal["ok", "degraded", "error"]
    redis: bool
    data_dir: bool
    db: bool
