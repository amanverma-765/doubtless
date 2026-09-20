"""FastAPI routers package exports."""

from doubtless.api.routers.chat import router as chat_router
from doubtless.api.routers.health import router as health_router
from doubtless.api.routers.study import router as study_router
from doubtless.api.routers.video import router as video_router

__all__ = ["chat_router", "health_router", "study_router", "video_router"]
