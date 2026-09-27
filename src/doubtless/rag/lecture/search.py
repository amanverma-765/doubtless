"""Vector search across lecture transcript chunks."""

from typing import Any

from doubtless.domain import LectureChunk
from doubtless.rag.retrieval import vector_search
from doubtless.storage.vector_store import get_lectures_collection

_MAX_LECTURE_DISTANCE = 1.25


def _chunk_factory(doc: str, meta: dict[str, Any]) -> LectureChunk:
    return LectureChunk(
        video_id=str(meta["video_id"]),
        start_time=float(str(meta["start_time"])),
        end_time=float(str(meta["end_time"])),
        text=doc,
    )


def _dedup_key(meta: dict[str, Any]) -> tuple[float, float]:
    return (float(str(meta["start_time"])), float(str(meta["end_time"])))


async def search_lecture(
    video_id: str,
    query: str,
    k: int = 3,
    max_distance: float = _MAX_LECTURE_DISTANCE,
) -> list[LectureChunk]:
    """Search across lecture transcript chunks with bilingual query expansion."""
    if not video_id:
        return []

    return await vector_search(
        collection=get_lectures_collection(),
        query=query,
        k=k,
        max_distance=max_distance,
        item_factory=_chunk_factory,
        dedup_key=_dedup_key,
        where={"video_id": video_id},
    )
