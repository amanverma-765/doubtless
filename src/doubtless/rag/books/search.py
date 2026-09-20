"""Query-time lookup against the NCERT textbook vector index."""

from doubtless.domain.schemas import BookChunk
from doubtless.rag.embeddings import embed_texts
from doubtless.storage.vector_store import get_books_collection


def search_books(query: str, k: int = 5) -> list[BookChunk]:
    """Search the indexed NCERT textbooks and return the k most relevant passages.

    Nearby chunks from the same chapter are skipped to return passages from
    distinct parts of the document.
    """
    if not query or not query.strip():
        return []

    vector = embed_texts([query], query=True)
    hits = get_books_collection().query(
        query_embeddings=vector,
        n_results=4 * k,
        include=["documents", "metadatas"],
    )
    docs, metas = hits.get("documents"), hits.get("metadatas")
    if not docs or not docs[0] or not metas or not metas[0]:
        return []

    kept: list[BookChunk] = []
    for doc, meta in zip(docs[0], metas[0], strict=True):
        chunk = BookChunk(
            grade=int(str(meta["grade"])),
            book=str(meta["book"]),
            chapter=int(str(meta["chapter"])),
            page=int(str(meta["page"])),
            text=str(doc),
        )
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
