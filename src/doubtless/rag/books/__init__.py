"""NCERT textbook retrieval and indexing subsystem."""

from doubtless.rag.books.download import BOOKS, download_books
from doubtless.rag.books.indexer import build_index
from doubtless.rag.books.search import search_books

__all__ = ["BOOKS", "build_index", "download_books", "search_books"]
