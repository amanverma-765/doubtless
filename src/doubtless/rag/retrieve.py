"""Query-time lookup against the index built by index.py."""

from doubtless.rag.index import embed, vector_store
from doubtless.rag.model import Chunk


def search(query: str, k: int = 5) -> list[Chunk]:
    """Return the k chunks nearest the query, at most one per stretch of text:
    a chunk next to one already chosen shares 125 tokens with it and is
    skipped so k answers cover k passages."""
    vector = embed([query], True)
    hits = vector_store().query(
        query_embeddings=vector,
        n_results=4 * k,  # room to drop neighbours and still fill k
        include=["documents", "metadatas"],
    )
    docs, metas = hits["documents"], hits["metadatas"]
    assert docs is not None and metas is not None

    kept: list[Chunk] = []
    for doc, meta in zip(docs[0], metas[0], strict=True):
        chunk = Chunk.model_validate({**meta, "text": doc})
        # skip a window that overlaps one already kept: same chapter, index ±1
        if not any(
            (c.grade, c.book, c.chapter) == (chunk.grade, chunk.book, chunk.chapter)
            and abs(c.index - chunk.index) == 1
            for c in kept
        ):
            kept.append(chunk)
        if len(kept) == k:
            break
    return kept
