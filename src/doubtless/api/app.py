"""FastAPI application entrypoint with modular REST routers and HLS static files."""

import asyncio
import logging
import mimetypes
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from doubtless.api.routers import (
    chat_router,
    health_router,
    study_router,
    video_router,
)
from doubtless.config import CORS_ORIGINS, HLS_DIR, LOGFIRE_SERVICE_NAME
from doubtless.core.telemetry import init_telemetry
from doubtless.storage import file_storage
from doubtless.storage.connection import init_db

logger = logging.getLogger(__name__)

# Ensure proper MIME types on Linux for HLS streaming files
mimetypes.add_type("video/mp2t", ".ts")
mimetypes.add_type("application/vnd.apple.mpegurl", ".m3u8")


class HLSStaticFiles(StaticFiles):
    """Serve HLS files with immutable caching for .ts and no-cache for playlists."""

    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        """Add cache-control headers based on HLS segment vs playlist extension."""
        response = super().file_response(full_path, stat_result, scope, status_code)
        path_str = str(full_path)
        if path_str.endswith(".ts"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path_str.endswith(".m3u8"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Initialize SQLite database and warm models on boot."""
    init_db()

    # Pre-warm SentenceTransformer embedding model asynchronously in background
    async def _warm_models() -> None:
        try:
            from doubtless.rag.embeddings import get_embedding_model

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, get_embedding_model)
            logger.info("SentenceTransformer embedding model warmed successfully.")
        except Exception as exc:
            logger.warning("Embedding model pre-warming encountered an issue: %s", exc)

    asyncio.create_task(_warm_models())

    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    file_storage.ensure_dirs()

    app = FastAPI(
        title="doubtless API",
        description=(
            "Video lecture streaming, HLS transcoding, and AI doubt-solving backend"
        ),
        version="1.0.0",
        lifespan=_lifespan,
    )

    init_telemetry(service_name=LOGFIRE_SERVICE_NAME, app=app)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static file mount for HLS video chunks and playlists with optimized caching
    app.mount("/hls", HLSStaticFiles(directory=HLS_DIR), name="hls")

    # Routers
    app.include_router(health_router)
    app.include_router(video_router, prefix="/api/v1")
    app.include_router(study_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")

    return app


app = create_app()
