"""Vector search across lecture transcript chunks."""

from doubtless.domain import LectureChunk
from doubtless.rag.embeddings import embed_texts
from doubtless.rag.query_expansion import expand_query
from doubtless.storage.vector_store import get_lectures_collection

_MAX_LECTURE_DISTANCE = 1.25


async def search_lecture(
    video_id: str,
    query: str,
    k: int = 3,
    max_distance: float = _MAX_LECTURE_DISTANCE,
) -> list[LectureChunk]:
    """Search across lecture transcript chunks with bilingual query expansion."""
    clean_query = query.strip() if query else ""
    if not video_id or not clean_query:
        return []

    # 1. Expand query into English, Hindi, and technical variations
    queries = await expand_query(clean_query)
    vectors = embed_texts(queries, query=True)

    # 2. Batch vector search in ChromaDB
    hits = get_lectures_collection().query(
        query_embeddings=vectors,
        n_results=k,
        where={"video_id": video_id},
        include=["documents", "metadatas", "distances"],
    )

    docs_batch = hits.get("documents") or []
    metas_batch = hits.get("metadatas") or []
    dists_batch = hits.get("distances") or []

    # 3. Merge & deduplicate across all query variants (keep lowest distance per chunk)
    best_chunks: dict[tuple[float, float], tuple[LectureChunk, float]] = {}

    for docs, metas, dists in zip(docs_batch, metas_batch, dists_batch, strict=False):
        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            d = float(dist)
            if d > max_distance:
                continue

            start_t = float(str(meta["start_time"]))
            end_t = float(str(meta["end_time"]))
            key = (start_t, end_t)

            if key not in best_chunks or d < best_chunks[key][1]:
                best_chunks[key] = (
                    LectureChunk(
                        video_id=str(meta["video_id"]),
                        start_time=start_t,
                        end_time=end_t,
                        text=str(doc),
                    ),
                    d,
                )

    # 4. Sort by best semantic distance and return top k
    sorted_items = sorted(best_chunks.values(), key=lambda item: item[1])
    return [chunk for chunk, _ in sorted_items[:k]]
