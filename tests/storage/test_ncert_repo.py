"""Unit tests for NCERT SQLite repository and FTS5 BM25 search."""

from pathlib import Path

from doubtless.domain import BookChunk
from doubtless.storage.repositories import ncert_repo


def test_ncert_repo_insert_and_bm25_search(temp_db: Path) -> None:
    """Test inserting book chunks into SQLite + FTS5 and retrieving via BM25."""
    chunks = [
        BookChunk(
            grade=11,
            book="physics_1",
            chapter=3,
            page=42,
            text=(
                "Newton second law of motion states force equals mass times "
                "acceleration F = ma."
            ),
        ),
        BookChunk(
            grade=12,
            book="chemistry_1",
            chapter=5,
            page=110,
            text=(
                "Phenolphthalein is an acid base indicator turning pink in "
                "basic solutions."
            ),
        ),
    ]

    ncert_repo.insert_chunks(chunks)

    # Search for exact chemical term
    hits = ncert_repo.search_bm25("phenolphthalein indicator", k=5)
    assert len(hits) >= 1
    chunk_key, score = hits[0]
    assert chunk_key == "12/chemistry_1/5/0"

    # Hydrate chunk
    chunk_map = ncert_repo.get_chunks_by_keys([chunk_key])
    assert chunk_key in chunk_map
    hydrated = chunk_map[chunk_key]
    assert hydrated.book == "chemistry_1"
    assert hydrated.chapter == 5
    assert hydrated.page == 110
    assert "Phenolphthalein" in hydrated.text


def test_ncert_repo_fts_query_empty() -> None:
    """Empty or stopword-only queries return empty FTS string and empty search."""
    assert ncert_repo.fts_query("") == ""
    assert ncert_repo.fts_query("what is the") == ""
    assert ncert_repo.search_bm25("what is the") == []
