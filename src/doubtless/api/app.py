"""FastAPI application entrypoint with modular REST routers and HLS static files."""

import mimetypes
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from doubtless.api.routers import chat_router, health_router, video_router
from doubtless.config import CORS_ORIGINS, HLS_DIR
from doubtless.storage import file_storage
from doubtless.storage.db import init_db

# Ensure proper MIME types on Linux for HLS streaming files
mimetypes.add_type("video/mp2t", ".ts")
mimetypes.add_type("application/vnd.apple.mpegurl", ".m3u8")


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Initialize filesystem directories and SQLite database on boot."""
    file_storage.ensure_dirs()
    init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="doubtless API",
        description=(
            "Video lecture streaming, HLS transcoding, and AI doubt-solving backend"
        ),
        version="1.0.0",
        lifespan=_lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static file mount for HLS video chunks and playlists
    app.mount("/hls", StaticFiles(directory=HLS_DIR), name="hls")

    # Routers
    app.include_router(health_router)
    app.include_router(video_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")

    return app


app = create_app()
