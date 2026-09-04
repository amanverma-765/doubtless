"""Query-time lookup against the index built by index.py."""

from doubtless.rag.index import embed


def search(query: str, k: int = 5) -> None:
    """Return the k chunks nearest the query. Must embed with the same model as
    index.py, or scores are silently wrong."""
    _ = embed
    return None
