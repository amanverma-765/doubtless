"""Vector indexing of lecture chunks into ChromaDB."""

from typing import Any

import torch

from doubtless.domain.schemas import LectureChunk
from doubtless.rag.embeddings import embed_texts
from doubtless.storage.vector_store import get_lectures_collection


def index_lecture_chunks(chunks: list[LectureChunk]) -> None:
    """Embed and upsert lecture transcript chunks into ChromaDB."""
    if not chunks:
        return

    vectors = embed_texts([c.text for c in chunks])

    ids = [
        f"{c.video_id}_{i}_{c.start_time:.1f}_{c.end_time:.1f}"
        for i, c in enumerate(chunks)
    ]
    documents = [c.text for c in chunks]
    metadatas: list[dict[str, Any]] = [
        {
            "video_id": c.video_id,
            "start_time": c.start_time,
            "end_time": c.end_time,
        }
        for c in chunks
    ]

    store = get_lectures_collection()
    store.upsert(
        ids=ids,
        embeddings=vectors,
        documents=documents,
        metadatas=metadatas,  # type: ignore[arg-type]
    )

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
