"""Health check and service diagnostic endpoints."""

from typing import Literal

from fastapi import APIRouter

from doubtless.config import DATA_DIR
from doubtless.domain.schemas import HealthResponse
from doubtless.storage import redis_store
from doubtless.storage.db import check_db_health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Check service health across database, cache, and filesystem."""
    redis_ok = redis_store.ping_redis()
    db_ok = check_db_health()
    data_dir_ok = DATA_DIR.exists()

    overall_ok = redis_ok and db_ok and data_dir_ok
    status_val: Literal["ok", "degraded", "error"] = "ok" if overall_ok else "degraded"

    return HealthResponse(
        status=status_val,
        redis=redis_ok,
        data_dir=data_dir_ok,
        db=db_ok,
    )
