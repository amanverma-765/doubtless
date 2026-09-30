"""NCERT textbook chunks persistence, FTS5 lexical index, and BM25 search."""

import re
from typing import Any

from doubtless.domain import BookChunk
from doubtless.storage.connection import get_db

_WORD = re.compile(r"[A-Za-z0-9]+")

_STOP_WORDS = (
    "a an the is are was were be been being am do does did doing have has had "
    "of in on at to for from by with about into over under and or but if then "
    "than that this these those it its as we you your they them their he she "
    "his her i what why how when where which who whom whose can could should "
    "would will shall may might must not no nor so such only own same too very "
    "give given write explain define describe name state list mention discuss "
    "following each other any all some many much more most"
)
_STOP = frozenset(_STOP_WORDS.split())


def fts_query(text: str) -> str:
    """Rewrite query as an FTS5 OR query with stopword removal."""
    terms = [w for w in _WORD.findall(text) if len(w) > 1 and w.lower() not in _STOP]
    return " OR ".join(f'"{term}"' for term in terms)


def insert_chunks(chunks: list[Any]) -> None:
    """Batch insert NCERT textbook chunks into SQLite and FTS5 index."""
    if not chunks:
        return

    with get_db() as conn:
        for c in chunks:
            chunk_key = getattr(c, "chunk_key", None)
            if not chunk_key:
                idx = getattr(c, "index", 0)
                chunk_key = f"{c.grade}/{c.book}/{c.chapter}/{idx}"

            existing = conn.execute(
                "SELECT id FROM ncert_chunks WHERE chunk_key = ?", (chunk_key,)
            ).fetchone()
            if existing:
                row_id = int(existing["id"])
                conn.execute("DELETE FROM ncert_chunks_fts WHERE rowid = ?", (row_id,))
                conn.execute("DELETE FROM ncert_chunks WHERE id = ?", (row_id,))

            cur = conn.execute(
                """
                INSERT INTO ncert_chunks (chunk_key, grade, book, chapter, page, text)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chunk_key, c.grade, c.book, c.chapter, c.page, c.text),
            )
            conn.execute(
                "INSERT INTO ncert_chunks_fts (rowid, text) VALUES (?, ?)",
                (cur.lastrowid, c.text),
            )


def search_bm25(query: str, k: int = 30) -> list[tuple[str, float]]:
    """Search NCERT textbook chunks using SQLite FTS5 BM25 scoring."""
    clean_query = fts_query(query)
    if not clean_query:
        return []

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.chunk_key, bm25(ncert_chunks_fts) AS score
            FROM ncert_chunks_fts f
            JOIN ncert_chunks c ON c.id = f.rowid
            WHERE ncert_chunks_fts MATCH ?
            ORDER BY score ASC
            LIMIT ?
            """,
            (clean_query, k),
        ).fetchall()

    return [(str(r["chunk_key"]), -float(r["score"])) for r in rows]


def get_chunks_by_keys(keys: list[str]) -> dict[str, BookChunk]:
    """Retrieve hydrated BookChunk objects for a list of chunk keys."""
    if not keys:
        return {}

    placeholders = ",".join("?" * len(keys))
    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT chunk_key, grade, book, chapter, page, text
            FROM ncert_chunks
            WHERE chunk_key IN ({placeholders})
            """,
            keys,
        ).fetchall()

    return {
        str(r["chunk_key"]): BookChunk(
            grade=int(r["grade"]),
            book=str(r["book"]),
            chapter=int(r["chapter"]),
            page=int(r["page"]),
            text=str(r["text"]),
        )
        for r in rows
    }
