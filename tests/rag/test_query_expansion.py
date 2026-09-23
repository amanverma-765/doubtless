"""Unit tests for query expansion and enhanced vector search."""

from unittest.mock import MagicMock, patch

import pytest

from doubtless.rag.books.search import search_books
from doubtless.rag.lecture.search import search_lecture
from doubtless.rag.query_expansion import (
    ExpandedQueriesPayload,
    _expander_agent,
    _expansion_cache,
    expand_query,
)


@pytest.fixture(autouse=True)
def clean_expansion_cache() -> None:
    """Ensure in-memory expansion cache does not leak across tests."""
    _expansion_cache.clear()
    yield
    _expansion_cache.clear()


@pytest.mark.asyncio
async def test_expand_query_structure_and_caching() -> None:
    """Test query expansion returns original query and handles caching."""
    q = "wo jo 6 wala ligand tha"
    mock_run = MagicMock()
    mock_run.output = ExpandedQueriesPayload(
        queries=["EDTA hexadentate ligand", "coordination compounds"]
    )
    with patch.object(_expander_agent, "run", return_value=mock_run) as mock_agent_run:
        res1 = await expand_query(q)
        assert len(res1) >= 1
        assert res1[0] == q
        assert "EDTA hexadentate ligand" in res1
        mock_agent_run.assert_called_once()

        # Check that calling again hits the in-memory cache without calling agent
        res2 = await expand_query(q)
        assert res1 == res2
        assert mock_agent_run.call_count == 1


@pytest.mark.asyncio
async def test_expand_query_empty() -> None:
    """Test empty or whitespace queries return empty list."""
    assert await expand_query("") == []
    assert await expand_query("   ") == []


@pytest.mark.asyncio
async def test_expand_query_fallback() -> None:
    """Test expand_query gracefully falls back to [query] if LLM fails."""
    with patch(
        "doubtless.rag.query_expansion._expander_agent.run",
        side_effect=RuntimeError("timeout"),
    ):
        fallback_res = await expand_query("some new unknown query term 12345")
        assert fallback_res == ["some new unknown query term 12345"]


@pytest.mark.asyncio
async def test_search_lecture_with_expansion() -> None:
    """Test search_lecture expands query and executes batch vector query."""
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["Teacher explains EDTA hexadentate ligand."]],
        "metadatas": [[{"video_id": "vid1", "start_time": 650.0, "end_time": 680.0}]],
        "distances": [[0.85]],
    }

    with (
        patch(
            "doubtless.rag.lecture.search.get_lectures_collection",
            return_value=mock_collection,
        ),
        patch("doubtless.rag.lecture.search.embed_texts", return_value=[[0.1, 0.2]]),
    ):
        results = await search_lecture("vid1", "wo jo 6 wala ligand tha", k=2)
        assert len(results) == 1
        assert results[0].start_time == 650.0
        assert "EDTA" in results[0].text


@pytest.mark.asyncio
async def test_search_books_with_expansion() -> None:
    """Test search_books expands query and drops passages exceeding threshold."""
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["Passage 1 about ligands.", "Far irrelevant passage."]],
        "metadatas": [
            [
                {"grade": 12, "book": "Chemistry", "chapter": 5, "page": 10},
                {"grade": 11, "book": "Physics", "chapter": 1, "page": 5},
            ]
        ],
        "distances": [[0.75, 1.45]],
    }

    with (
        patch(
            "doubtless.rag.books.search.get_books_collection",
            return_value=mock_collection,
        ),
        patch("doubtless.rag.books.search.embed_texts", return_value=[[0.1, 0.2]]),
    ):
        results = await search_books("ligands", k=5, max_distance=1.15)
        # 1.45 distance is dropped
        assert len(results) == 1
        assert results[0].chapter == 5
        assert results[0].page == 10
