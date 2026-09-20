"""Vector search across lecture transcript chunks."""

from doubtless.domain.schemas import LectureChunk
from doubtless.rag.embeddings import embed_texts
from doubtless.storage.vector_store import get_lectures_collection


def search_lecture(video_id: str, query: str, k: int = 3) -> list[LectureChunk]:
    """Search anywhere in this specific lecture's transcript for relevant moments."""
    if not video_id or not query or not query.strip():
        return []

    vector = embed_texts([query], query=True)
    hits = get_lectures_collection().query(
        query_embeddings=vector,
        n_results=k,
        where={"video_id": video_id},
        include=["documents", "metadatas"],
    )

    docs, metas = hits.get("documents"), hits.get("metadatas")
    if not docs or not docs[0] or not metas or not metas[0]:
        return []

    results: list[LectureChunk] = []
    for doc, meta in zip(docs[0], metas[0], strict=True):
        results.append(
            LectureChunk(
                video_id=str(meta["video_id"]),
                start_time=float(str(meta["start_time"])),
                end_time=float(str(meta["end_time"])),
                text=str(doc),
            )
        )

    return results
