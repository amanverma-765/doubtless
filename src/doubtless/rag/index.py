"""Build a vector index from the downloaded PDF books."""

from bisect import bisect_right
from functools import cache
from pathlib import Path
from typing import cast

import chromadb
import numpy as np
import torch
from chromadb.api.models.Collection import Collection
from numpy.typing import NDArray
from pymupdf import pymupdf
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, PreTrainedTokenizerBase

from doubtless.rag.clean import clean_text, decode_glyphs, strip_running_heads
from doubtless.rag.download import BOOKS_DIR, BY_FOLDER
from doubtless.rag.model import Chunk

MODEL = "Qwen/Qwen3-Embedding-0.6B"


@cache
def vector_store() -> Collection:
    """Initialize and return the ChromaDB collection for the vector store."""
    _INDEX_DIR = Path(__file__).resolve().parents[3] / "data" / "index"
    client = chromadb.PersistentClient(path=_INDEX_DIR / "chroma_db")
    return client.get_or_create_collection(name="ncert")


@cache
def _tokenizer() -> PreTrainedTokenizerBase:
    """Load the embedding model's tokenizer so chunk windows are sized in its
    own token units."""
    return AutoTokenizer.from_pretrained(MODEL)


@cache
def _model() -> SentenceTransformer:
    """Load and return the SentenceTransformer embedding model."""
    return SentenceTransformer(MODEL, model_kwargs={"torch_dtype": torch.float32})


def _book_source(pdf: Path) -> tuple[int, str, int]:
    """Extract the grade, subject, and chapter number from a chapter's PDF file path."""
    book = BY_FOLDER[pdf.parent.name]
    return book.grade, book.subject, book.offset + int(pdf.stem.split("_")[1])


def _load(path: Path) -> list[str]:
    """Read a chapter PDF into cleaned text strings, one per page."""
    with pymupdf.open(path) as doc:  # type: ignore[no-untyped-call]
        pages = [clean_text(_page_text(page)) for page in doc.pages()]
    return strip_running_heads(pages)


def _page_text(page: pymupdf.Page) -> str:
    """Extract a page's text, decoding each span with its own font's glyph map."""
    page_dict = page.get_text("dict")  # type: ignore[no-untyped-call]
    decoded_lines = []

    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            # Decode each span and join them into a single line string
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

    encoder = _tokenizer()

    # Encode each page into tokens, inserting a space between pages.
    tokens: list[int] = []
    page_starts: list[int] = []  # Token offset where each page begins.
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
                # Pages are in order, so bisect gives the page the chunk starts on.
                page=bisect_right(page_starts, start),
                # decode is typed as returning a batch; one sequence in, one out.
                text=cast(str, encoder.decode(tokens[start:end])).strip(),
            )
        )
        if end >= len(tokens):
            break
        start = end - overlap
    return chunks


def embed(texts: list[str], query: bool = False) -> NDArray[np.float32]:
    """Embed texts, optionally with the query prompt for retrieval."""
    query_prompt = (
        "Instruct: Given a student's question about a school science or mathematics "
        "topic, retrieve the textbook passage that answers it\nQuery:"
    )

    return _model().encode(
        texts,
        prompt=query_prompt if query else None,
        normalize_embeddings=True,
        batch_size=8,
    )


def _ingest(chunks: list[Chunk], vectors: NDArray[np.float32]) -> None:
    """Upsert chunks, their embeddings and metadata into the store."""
    assert len(chunks) == len(vectors)
    vector_store().upsert(
        ids=[f"{c.grade}/{c.book}/{c.chapter}/{c.index}" for c in chunks],
        embeddings=vectors,
        documents=[c.text for c in chunks],
        metadatas=[c.model_dump(exclude={"text"}) for c in chunks],
    )


def build_index(books_dir: Path = BOOKS_DIR) -> None:
    """Build the vector index chapter by chapter, skipping chapters already in
    the store so an interrupted run resumes."""
    store = vector_store()
    for pdf in sorted(books_dir.rglob("chapter_*.pdf")):
        grade, book, chapter = _book_source(pdf)

        # A chapter is one upsert, so chunk 0 present means the chapter is indexed.
        if store.get(ids=[f"{grade}/{book}/{chapter}/0"], include=[])["ids"]:
            continue

        # Create overlapping token chunks from the chapter pages.
        pages = _load(pdf)
        chunks = _chunk(pages, grade, book, chapter)

        # Generate vector embeddings for all text chunks.
        vectors = embed([c.text for c in chunks])

        # Ingest chunks into ChromaDB.
        _ingest(chunks, vectors)
        print(f"class {grade} {book} ch {chapter}: {len(chunks)} chunks", flush=True)
