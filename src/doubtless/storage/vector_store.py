"""Centralized ChromaDB vector store client and collection access."""

import contextlib
from functools import cache

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from doubtless.config import INDEX_DIR


@cache
def get_chroma_client() -> ClientAPI:
    """Return cached ChromaDB persistent client."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(INDEX_DIR / "chroma_db"))


def get_books_collection() -> Collection:
    """Return ChromaDB collection for NCERT textbooks with cosine similarity."""
    return get_chroma_client().get_or_create_collection(
        name="ncert",
        metadata={"hnsw:space": "cosine"},
    )


def get_lectures_collection() -> Collection:
    """Return ChromaDB collection for lecture transcripts with cosine similarity."""
    return get_chroma_client().get_or_create_collection(
        name="lectures",
        metadata={"hnsw:space": "cosine"},
    )


def delete_lecture_vectors(video_id: str) -> None:
    """Delete all vector embeddings belonging to a specific video."""
    with contextlib.suppress(Exception):
        get_lectures_collection().delete(where={"video_id": video_id})
