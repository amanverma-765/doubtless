"""Build a vector index from the downloaded NCERT PDF books."""

from bisect import bisect_right
from pathlib import Path
from typing import Any, cast

import numpy as np
import pymupdf
from numpy.typing import NDArray
from pydantic import BaseModel

from doubtless.config import BOOKS_DIR
from doubtless.rag.books.clean import clean_text, decode_glyphs, strip_running_heads
from doubtless.rag.books.download import BY_FOLDER, download_books
from doubtless.rag.embeddings import embed_texts, get_tokenizer
from doubtless.storage.vector_store import get_books_collection


class Chunk(BaseModel):
    """One indexed slice of a chapter, with the citation it came from."""

    index: int
    grade: int
    book: str
    chapter: int
    page: int  # 1-based page within the chapter PDF
    text: str


def _book_source(pdf: Path) -> tuple[int, str, int]:
    """Extract grade, subject, and chapter number from a chapter's PDF file path."""
    book = BY_FOLDER[pdf.parent.name]
    return book.grade, book.subject, book.offset + int(pdf.stem.split("_")[1])


def _load(path: Path) -> list[str]:
    """Read a chapter PDF into cleaned text strings, one per page."""
    with pymupdf.open(path) as doc:  # type: ignore[no-untyped-call]
        pages = [clean_text(_page_text(page)) for page in doc.pages()]
    return strip_running_heads(pages)


def _page_text(page: pymupdf.Page) -> str:
    """Extract a page's text, decoding each span with its own font's glyph map."""
    page_dict = cast(dict[str, Any], page.get_text("dict"))  # type: ignore[no-untyped-call]
    decoded_lines = []

    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            line_text = "".join(
                decode_glyphs(span["text"], span["font"])
                for span in line.get("spans", [])
            )
            decoded_lines.append(line_text)

    return "\n".join(decoded_lines)


def _chunk(
    pages: list[str],
    grade: int,
    book: str,
    chapter: int,
    size: int = 512,
    overlap: int = 125,
) -> list[Chunk]:
    """Split chapter text into overlapping token-sized chunks."""
    if overlap >= size:
        raise ValueError(f"overlap ({overlap}) must be less than size ({size})")

    encoder = get_tokenizer()

    tokens: list[int] = []
    page_starts: list[int] = []
    for text in pages:
        page_starts.append(len(tokens))
        if tokens:
            tokens.extend(encoder.encode(" ", add_special_tokens=False))
        tokens.extend(encoder.encode(" ".join(text.split()), add_special_tokens=False))

    chunks: list[Chunk] = []
    start = 0
    while start < len(tokens):
        end = min(start + size, len(tokens))
        chunks.append(
            Chunk(
                index=len(chunks),
                grade=grade,
                book=book,
                chapter=chapter,
                page=bisect_right(page_starts, start),
                text=cast(str, encoder.decode(tokens[start:end])).strip(),
            )
        )
        if end >= len(tokens):
            break
        start = end - overlap
    return chunks


def _ingest(chunks: list[Chunk], vectors: NDArray[np.float32]) -> None:
    """Upsert chunks, their embeddings, and metadata into the books vector store."""
    assert len(chunks) == len(vectors)
    get_books_collection().upsert(
        ids=[f"{c.grade}/{c.book}/{c.chapter}/{c.index}" for c in chunks],
        embeddings=vectors,
        documents=[c.text for c in chunks],
        metadatas=[c.model_dump(exclude={"text"}) for c in chunks],
    )


def build_index(books_dir: Path = BOOKS_DIR) -> None:
    """Build the vector index from all downloaded book chapters."""
    store = get_books_collection()

    for pdf in download_books(books_dir):
        grade, book, chapter = _book_source(pdf)

        if store.get(ids=[f"{grade}/{book}/{chapter}/0"], include=[])["ids"]:
            continue

        pages = _load(pdf)
        chunks = _chunk(pages, grade, book, chapter)
        if not chunks:
            print(
                f"class {grade} {book} ch {chapter}: 0 chunks (skipped)",
                flush=True,
            )
            continue

        vectors = embed_texts([c.text for c in chunks])
        _ingest(chunks, vectors)

        print(
            f"class {grade} {book} ch {chapter}: {len(chunks)} chunks",
            flush=True,
        )
