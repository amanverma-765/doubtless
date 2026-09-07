from dataclasses import dataclass
from typing import cast

import redis
from redis import Redis
from redis.typing import FieldT, EncodableT

from doubtless.config import REDIS_URL

KEY = "doubtless:current_video"
_client: Redis | None = None


def _redis() -> Redis:
    global _client

    if _client is None:
        _client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
        )

    return _client


@dataclass
class VideoRecord:
    id: str
    task_id: str | None = None


def save(record: VideoRecord) -> None:
    mapping = {"id": record.id}

    if record.task_id is not None:
        mapping["task_id"] = record.task_id

    _redis().hset(
        KEY,
        mapping=cast(dict[FieldT, EncodableT], mapping),
    )


def get() -> VideoRecord | None:
    data = _redis().hgetall(KEY)

    if not data or "id" not in data:
        return None

    return VideoRecord(
        id=str(data["id"]),
        task_id=str(data["task_id"]) if "task_id" in data else None,
    )


def clear() -> None:
    _redis().delete(KEY)
