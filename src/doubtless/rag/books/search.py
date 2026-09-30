"""Query-time hybrid lookup against the NCERT textbook corpus."""

from typing import Any

from doubtless.domain import BookChunk
from doubtless.rag.retrieval import reciprocal_rank_fusion, vector_search
from doubtless.storage.repositories import ncert_repo
from doubtless.storage.vector_store import get_books_collection

_MAX_BOOK_DISTANCE = 1.15
_HYBRID_DEPTH = 30


def _book_chunk_factory(doc: str, meta: dict[str, Any]) -> BookChunk:
    return BookChunk(
        grade=int(str(meta["grade"])),
        book=str(meta["book"]),
        chapter=int(str(meta["chapter"])),
        page=int(str(meta["page"])),
        text=doc,
    )


def _book_dedup_key(meta: dict[str, Any]) -> tuple[int, str, int, int]:
    return (
        int(str(meta["grade"])),
        str(meta["book"]),
        int(str(meta["chapter"])),
        int(str(meta["page"])),
    )


def _filter_adjacent_pages(
    items: list[tuple[BookChunk, float]],
    k: int,
) -> list[BookChunk]:
    """Filter adjacent pages from the same chapter to ensure diverse context."""
    kept: list[BookChunk] = []
    for chunk, _ in items:
        if not any(
            (c.grade, c.book, c.chapter) == (chunk.grade, chunk.book, chunk.chapter)
            and abs(c.page - chunk.page) <= 1
            for c in kept
        ):
            kept.append(chunk)

        if len(kept) == k:
            break

    return kept


async def search_books(
    query: str,
    k: int = 5,
    max_distance: float = _MAX_BOOK_DISTANCE,
) -> list[BookChunk]:
    """Search NCERT textbooks using BM25 FTS5 and dense vector search fused via RRF."""
    clean_query = query.strip() if query else ""
    if not clean_query:
        return []

    page_map: dict[tuple[int, str, int, int], BookChunk] = {}

    # 1. Lexical BM25 branch (SQLite FTS5)
    lexical_hits = ncert_repo.search_bm25(clean_query, k=_HYBRID_DEPTH)
    lexical_chunk_keys = [key for key, _ in lexical_hits]
    hydrated_lexical = ncert_repo.get_chunks_by_keys(lexical_chunk_keys)

    lexical_ranking: list[tuple[int, str, int, int]] = []
    for key in lexical_chunk_keys:
        if key in hydrated_lexical:
            chunk = hydrated_lexical[key]
            page_key = (chunk.grade, chunk.book, chunk.chapter, chunk.page)
            if page_key not in page_map:
                page_map[page_key] = chunk
            lexical_ranking.append(page_key)

    # 2. Dense vector branch (ChromaDB + SentenceTransformers)
    dense_results = await vector_search(
        collection=get_books_collection(),
        query=clean_query,
        k=_HYBRID_DEPTH,
        max_distance=max_distance,
        n_results=4 * k,
        item_factory=_book_chunk_factory,
        dedup_key=_book_dedup_key,
        post_filter=None,
    )

    dense_ranking: list[tuple[int, str, int, int]] = []
    for chunk in dense_results:
        page_key = (chunk.grade, chunk.book, chunk.chapter, chunk.page)
        if page_key not in page_map:
            page_map[page_key] = chunk
        dense_ranking.append(page_key)

    if not lexical_ranking and not dense_ranking:
        return []

    # 3. Reciprocal Rank Fusion (RRF)
    rankings: list[list[tuple[int, str, int, int]]] = []
    if lexical_ranking:
        rankings.append(lexical_ranking)
    if dense_ranking:
        rankings.append(dense_ranking)

    fused = reciprocal_rank_fusion(rankings, k=_HYBRID_DEPTH)
    fused_items: list[tuple[BookChunk, float]] = [
        (page_map[page_key], score) for page_key, score in fused if page_key in page_map
    ]

    # 4. Filter adjacent pages and return top-k
    return _filter_adjacent_pages(fused_items, k)
