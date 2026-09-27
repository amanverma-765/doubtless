"""Unit tests for the unified vector retrieval engine."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from doubtless.rag.retrieval import vector_search


@pytest.mark.asyncio
async def test_vector_search_empty_query() -> None:
    """Empty or whitespace queries immediately return empty list without searching."""
    mock_col = MagicMock()
    res1 = await vector_search(
        collection=mock_col,
        query="",
        k=5,
        max_distance=1.0,
        item_factory=lambda d, m: d,
        dedup_key=lambda m: m["id"],
    )
    res2 = await vector_search(
        collection=mock_col,
        query="   ",
        k=5,
        max_distance=1.0,
        item_factory=lambda d, m: d,
        dedup_key=lambda m: m["id"],
    )
    assert res1 == []
    assert res2 == []
    mock_col.query.assert_not_called()


@pytest.mark.asyncio
async def test_vector_search_deduplication_and_filtering() -> None:
    """Vector search keeps lower distance chunk and drops above threshold."""
    mock_col = MagicMock()
    mock_col.query.return_value = {
        "documents": [
            ["Doc 1 higher distance", "Doc 1 lower distance", "Doc 2 bad distance"]
        ],
        "metadatas": [[{"item_id": "1"}, {"item_id": "1"}, {"item_id": "2"}]],
        "distances": [[0.80, 0.40, 1.50]],
    }

    def _factory(doc: str, meta: dict[str, Any]) -> dict[str, Any]:
        return {"text": doc, "id": meta["item_id"]}

    with (
        patch("doubtless.rag.retrieval.expand_query", return_value=["query"]),
        patch("doubtless.rag.retrieval.embed_texts", return_value=[[0.1, 0.2]]),
    ):
        results = await vector_search(
            collection=mock_col,
            query="test query",
            k=5,
            max_distance=1.0,
            item_factory=_factory,
            dedup_key=lambda m: m["item_id"],
        )

        assert len(results) == 1
        assert results[0]["id"] == "1"
        assert results[0]["text"] == "Doc 1 lower distance"


@pytest.mark.asyncio
async def test_vector_search_custom_post_filter() -> None:
    """Vector search executes custom post-filter when provided."""
    mock_col = MagicMock()
    mock_col.query.return_value = {
        "documents": [["Doc A", "Doc B", "Doc C"]],
        "metadatas": [[{"id": "A"}, {"id": "B"}, {"id": "C"}]],
        "distances": [[0.1, 0.2, 0.3]],
    }

    def _post_filter(items: list[tuple[str, float]], k: int) -> list[str]:
        # Keep only docs that end with B
        return [doc for doc, _ in items if doc.endswith("B")][:k]

    with (
        patch("doubtless.rag.retrieval.expand_query", return_value=["query"]),
        patch("doubtless.rag.retrieval.embed_texts", return_value=[[0.1, 0.2]]),
    ):
        results = await vector_search(
            collection=mock_col,
            query="test query",
            k=2,
            max_distance=1.0,
            item_factory=lambda doc, meta: doc,
            dedup_key=lambda meta: meta["id"],
            post_filter=_post_filter,
        )

        assert results == ["Doc B"]
