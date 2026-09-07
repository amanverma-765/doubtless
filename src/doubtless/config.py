import os
from pathlib import Path

PORT = int(os.getenv("PORT", "8000"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Storage directories
DATA_DIR = Path(os.getenv("DOUBTLESS_DATA", "data")).resolve()
VIDEO_DIR = DATA_DIR / "video"
HLS_DIR = DATA_DIR / "hls"
INDEX_DIR = DATA_DIR / "index"
BOOKS_DIR = DATA_DIR / "books"

MAX_UPLOAD_BYTES = 1024 * 1024 * 1024  # 1 GB
ALLOWED_EXTENSIONS = {"mp4", "mov", "mkv", "webm"}
CORS_ORIGINS = ["*"]