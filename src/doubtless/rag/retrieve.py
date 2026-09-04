"""Query-time lookup against the index built by index.py."""

from doubtless.rag.index import embed, vector_store
from doubtless.rag.model import Chunk


def search(query: str, k: int = 5) -> list[Chunk]:
    """Return the k chunks nearest the query."""
    vector = embed([query], True)
    hits = vector_store().query(
        query_embeddings=vector, n_results=k, include=["documents", "metadatas"]
    )
    docs, metas = hits["documents"], hits["metadatas"]
    assert docs is not None and metas is not None

    chunks = []
    for doc, meta in zip(docs[0], metas[0], strict=True):
        chunks.append(Chunk.model_validate({**meta, "text": doc}))
    return chunks
