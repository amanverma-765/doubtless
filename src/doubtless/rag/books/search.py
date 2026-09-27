"""Query-time lookup against the NCERT textbook vector index."""

from doubtless.domain import BookChunk
from doubtless.rag.embeddings import embed_texts
from doubtless.rag.query_expansion import expand_query
from doubtless.storage.vector_store import get_books_collection

_MAX_BOOK_DISTANCE = 1.15


async def search_books(
    query: str,
    k: int = 5,
    max_distance: float = _MAX_BOOK_DISTANCE,
) -> list[BookChunk]:
    """Search indexed NCERT textbooks with bilingual query expansion."""
    clean_query = query.strip() if query else ""
    if not clean_query:
        return []

    # 1. Expand query into academic English and Hindi variations
    queries = await expand_query(clean_query)
    vectors = embed_texts(queries, query=True)

    # 2. Batch vector search in ChromaDB
    hits = get_books_collection().query(
        query_embeddings=vectors,
        n_results=4 * k,
        include=["documents", "metadatas", "distances"],
    )

    docs_batch = hits.get("documents") or []
    metas_batch = hits.get("metadatas") or []
    dists_batch = hits.get("distances") or []

    # 3. Deduplicate across query variants (keep lowest distance per passage)
    best_chunks: dict[tuple[int, str, int, int], tuple[BookChunk, float]] = {}

    for docs, metas, dists in zip(docs_batch, metas_batch, dists_batch, strict=False):
        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            d = float(dist)
            if d > max_distance:
                continue

            grade = int(str(meta["grade"]))
            book = str(meta["book"])
            chapter = int(str(meta["chapter"]))
            page = int(str(meta["page"]))
            key = (grade, book, chapter, page)

            if key not in best_chunks or d < best_chunks[key][1]:
                best_chunks[key] = (
                    BookChunk(
                        grade=grade,
                        book=book,
                        chapter=chapter,
                        page=page,
                        text=str(doc),
                    ),
                    d,
                )

    # 4. Sort by relevance and filter adjacent chapter pages
    sorted_items = sorted(best_chunks.values(), key=lambda item: item[1])

    kept: list[BookChunk] = []
    for chunk, _ in sorted_items:
        # Skip an overlapping window from the same chapter if already kept
        if not any(
            (c.grade, c.book, c.chapter) == (chunk.grade, chunk.book, chunk.chapter)
            and abs(c.page - chunk.page) <= 1
            for c in kept
        ):
            kept.append(chunk)

        if len(kept) == k:
            break

    return kept
