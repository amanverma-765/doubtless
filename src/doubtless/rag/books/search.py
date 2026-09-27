"""Query-time lookup against the NCERT textbook vector index."""

from typing import Any

from doubtless.domain import BookChunk
from doubtless.rag.retrieval import vector_search
from doubtless.storage.vector_store import get_books_collection

_MAX_BOOK_DISTANCE = 1.15


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
    """Search indexed NCERT textbooks with bilingual query expansion."""
    return await vector_search(
        collection=get_books_collection(),
        query=query,
        k=k,
        max_distance=max_distance,
        n_results=4 * k,
        item_factory=_book_chunk_factory,
        dedup_key=_book_dedup_key,
        post_filter=_filter_adjacent_pages,
    )
