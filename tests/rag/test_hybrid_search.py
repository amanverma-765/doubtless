"""Unit tests for RRF rank fusion and hybrid NCERT textbook search."""

from unittest.mock import AsyncMock, patch

import pytest

from doubtless.domain import BookChunk
from doubtless.rag.books.search import search_books
from doubtless.rag.retrieval import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_basic() -> None:
    """RRF correctly boosts candidates appearing high in multiple rankings."""
    ranking1 = ["doc_A", "doc_B", "doc_C"]
    ranking2 = ["doc_B", "doc_D", "doc_A"]

    fused = reciprocal_rank_fusion([ranking1, ranking2], k=4, rrf_k=60)
    top_keys = [key for key, _ in fused]

    # doc_B is #2 in ranking1 and #1 in ranking2: 1/62 + 1/61 ~ 0.0325
    # doc_A is #1 in ranking1 and #3 in ranking2: 1/61 + 1/63 ~ 0.0322
    assert top_keys[0] == "doc_B"
    assert top_keys[1] == "doc_A"


def test_reciprocal_rank_fusion_empty() -> None:
    """Empty ranking lists return empty results."""
    assert reciprocal_rank_fusion([], k=5) == []
    assert reciprocal_rank_fusion([[], []], k=5) == []


@pytest.mark.asyncio
async def test_search_books_hybrid_fusion() -> None:
    """search_books combines lexical BM25 hits and dense vector hits via RRF."""
    chunk_a = BookChunk(
        grade=11, book="chem", chapter=1, page=10, text="Electrolysis details"
    )
    chunk_b = BookChunk(
        grade=11, book="phys", chapter=2, page=20, text="Electrical currents"
    )

    with (
        patch("doubtless.rag.books.search.ncert_repo.search_bm25") as mock_bm25,
        patch(
            "doubtless.rag.books.search.ncert_repo.get_chunks_by_keys"
        ) as mock_hydrate,
        patch(
            "doubtless.rag.books.search.vector_search", new_callable=AsyncMock
        ) as mock_vector,
    ):
        mock_bm25.return_value = [("11/chem/1/0", 5.2)]
        mock_hydrate.return_value = {"11/chem/1/0": chunk_a}
        mock_vector.return_value = [chunk_b]

        results = await search_books("electrolysis current", k=5)

        assert len(results) == 2
        books = {c.book for c in results}
        assert "chem" in books
        assert "phys" in books


@pytest.mark.asyncio
async def test_search_books_empty_query() -> None:
    """Empty search query returns empty list immediately."""
    assert await search_books("") == []
    assert await search_books("   ") == []
