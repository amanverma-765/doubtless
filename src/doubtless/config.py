"""Centralized type-safe application configuration and directory paths."""

import os
from pathlib import Path

import dotenv

# Load environment variables from .env file at startup
dotenv.load_dotenv()

# Base storage directories
DATA_DIR = Path(os.getenv("DOUBTLESS_DATA", "data")).resolve()
VIDEO_DIR = DATA_DIR / "video"
HLS_DIR = DATA_DIR / "hls"
INDEX_DIR = DATA_DIR / "index"
BOOKS_DIR = DATA_DIR / "books"

# Network & Server configuration
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Upload constraints
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES") or 4 * 1024**3)  # 4 GB
ALLOWED_EXTENSIONS: set[str] = {"mp4", "mkv", "mov", "webm", "m4v", "avi", "ts"}

_cors_raw = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS: list[str] = [
    origin.strip() for origin in _cors_raw.split(",") if origin.strip()
]

# Presentation & static file URLs
HLS_URL_PREFIX = os.getenv("HLS_URL_PREFIX", "/hls")

# AI & RAG configuration
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "cx/gpt-5.6-luna")
AI_BASE_URL = os.getenv("AI_BASE_URL", "http://localhost:20128/v1")
AI_API_KEY = os.getenv("NINEROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
