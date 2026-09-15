"""Domain types shared across the RAG pipeline."""

from typing import NamedTuple

from pydantic import BaseModel


class Book(NamedTuple):
    """One NCERT textbook as pinned in the corpus."""

    code: str  # ncert_cli's download id
    grade: int
    subject: str
    folder: str  # directory ncert_cli writes under BOOKS_DIR
    offset: int = 0  # chapters in the preceding part; 0 for single-part books


class Chunk(BaseModel):
    """One indexed slice of a chapter, with the citation it came from."""

    index: int
    grade: int
    book: str
    chapter: int
    page: int  # 1-based page within the chapter PDF
    text: str
