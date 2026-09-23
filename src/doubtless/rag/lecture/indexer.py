"""Vector indexing of lecture chunks into ChromaDB."""

from collections.abc import Callable
from typing import Any

import torch

from doubtless.domain.schemas import LectureChunk
from doubtless.rag.embeddings import embed_texts
from doubtless.storage.vector_store import get_lectures_collection


def index_lecture_chunks(
    chunks: list[LectureChunk],
    batch_size: int = 16,
    on_progress: Callable[[float], None] | None = None,
) -> None:
    """Embed and upsert lecture transcript chunks into ChromaDB with progress."""
    if not chunks:
        return

    store = get_lectures_collection()
    total = len(chunks)

    for start_idx in range(0, total, batch_size):
        batch = chunks[start_idx : start_idx + batch_size]
        vectors = embed_texts([c.text for c in batch])

        ids = [
            f"{c.video_id}_{start_idx + i}_{c.start_time:.1f}_{c.end_time:.1f}"
            for i, c in enumerate(batch)
        ]
        documents = [c.text for c in batch]
        metadatas: list[dict[str, Any]] = [
            {
                "video_id": c.video_id,
                "start_time": c.start_time,
                "end_time": c.end_time,
            }
            for c in batch
        ]

        store.upsert(
            ids=ids,
            embeddings=vectors,
            documents=documents,
            metadatas=metadatas,  # type: ignore[arg-type]
        )

        if on_progress:
            done = min(total, start_idx + len(batch))
            on_progress(done / total)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
