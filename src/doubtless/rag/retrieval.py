"""Unified vector retrieval engine across ChromaDB collections."""

from collections.abc import Callable, Hashable
from typing import Any

from chromadb.api.models.Collection import Collection

from doubtless.rag.embeddings import embed_texts
from doubtless.rag.query_expansion import expand_query


async def vector_search[T](
    *,
    collection: Collection,
    query: str,
    k: int,
    max_distance: float,
    item_factory: Callable[[str, dict[str, Any]], T],
    dedup_key: Callable[[dict[str, Any]], Hashable],
    where: dict[str, Any] | None = None,
    n_results: int | None = None,
    post_filter: Callable[[list[tuple[T, float]], int], list[T]] | None = None,
) -> list[T]:
    """Execute query expansion, batch embedding, ChromaDB search, and deduplication."""
    clean_query = query.strip() if query else ""
    if not clean_query:
        return []

    # 1. Expand query into language / terminology variations
    queries = await expand_query(clean_query)
    vectors = embed_texts(queries, query=True)

    # 2. Batch vector search in ChromaDB
    query_kwargs: dict[str, Any] = {
        "query_embeddings": vectors,
        "n_results": n_results if n_results is not None else k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_kwargs["where"] = where

    hits = collection.query(**query_kwargs)

    docs_batch = hits.get("documents") or []
    metas_batch = hits.get("metadatas") or []
    dists_batch = hits.get("distances") or []

    # 3. Deduplicate across query variants (keep lowest distance per key)
    best_chunks: dict[Hashable, tuple[T, float]] = {}

    for docs, metas, dists in zip(docs_batch, metas_batch, dists_batch, strict=False):
        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            d = float(dist)
            if d > max_distance:
                continue

            meta_dict = dict(meta) if meta else {}
            key = dedup_key(meta_dict)

            if key not in best_chunks or d < best_chunks[key][1]:
                best_chunks[key] = (
                    item_factory(str(doc), meta_dict),
                    d,
                )

    # 4. Sort by best semantic distance
    sorted_items = sorted(best_chunks.values(), key=lambda item: item[1])

    # 5. Apply optional post-filter or default top-k truncation
    if post_filter is not None:
        return post_filter(sorted_items, k)

    return [item for item, _ in sorted_items[:k]]
