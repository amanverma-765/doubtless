"""Refetch the textbooks under data/books, which git does not carry."""

import subprocess
import sys
from pathlib import Path

from doubtless.rag.model import Book

BOOKS_DIR = Path(__file__).resolve().parents[3] / "data" / "books"

BOOKS = (
    Book(
        code="jemh1",
        grade=10,
        subject="mathematics",
        folder="class_10_mathematics",
        offset=0,
    ),
    Book(
        code="jesc1",
        grade=10,
        subject="science",
        folder="class_10_science",
        offset=0,
    ),
    Book(
        code="keph1",
        grade=11,
        subject="physics",
        folder="class_11_physics_physics_part_i",
        offset=0,
    ),
    Book(
        code="keph2",
        grade=11,
        subject="physics",
        folder="class_11_physics_physics_part_ii",
        offset=7,
    ),
    Book(
        code="kech1",
        grade=11,
        subject="chemistry",
        folder="class_11_chemistry_chemistry_part_i",
        offset=0,
    ),
    Book(
        code="kech2",
        grade=11,
        subject="chemistry",
        folder="class_11_chemistry_chemistry_part_ii",
        offset=6,
    ),
    Book(
        code="kemh1",
        grade=11,
        subject="mathematics",
        folder="class_11_mathematics",
        offset=0,
    ),
    Book(
        code="kebo1",
        grade=11,
        subject="biology",
        folder="class_11_biology",
        offset=0,
    ),
    Book(
        code="leph1",
        grade=12,
        subject="physics",
        folder="class_12_physics_physics_part_i",
        offset=0,
    ),
    Book(
        code="leph2",
        grade=12,
        subject="physics",
        folder="class_12_physics_physics_part_ii",
        offset=8,
    ),
    Book(
        code="lech1",
        grade=12,
        subject="chemistry",
        folder="class_12_chemistry_chemistry_i",
        offset=0,
    ),
    Book(
        code="lech2",
        grade=12,
        subject="chemistry",
        folder="class_12_chemistry_chemistry_ii",
        offset=5,
    ),
    Book(
        code="lemh1",
        grade=12,
        subject="mathematics",
        folder="class_12_mathematics_mathematics_part_i",
        offset=0,
    ),
    Book(
        code="lemh2",
        grade=12,
        subject="mathematics",
        folder="class_12_mathematics_mathematics_part_ii",
        offset=6,
    ),
    Book(
        code="lebo1",
        grade=12,
        subject="biology",
        folder="class_12_biology",
        offset=0,
    ),
)

BY_FOLDER = {book.folder: book for book in BOOKS}


def download_books(outdir: Path = BOOKS_DIR) -> list[Path]:
    """Download all books as chapter-level PDFs and return their paths.

    Existing book folders are skipped, and preliminary pages are excluded.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    cached = all((outdir / book.folder).is_dir() for book in BOOKS)
    # Prelims are the cover and contents: no prose to retrieve, and their page
    # numbering does not line up with the chapters'.
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "ncert_cli",
            *(book.code for book in BOOKS),
            "--chapters",
            "--no-prelims",
            "-o",
            str(outdir),
        ],
        stdout=subprocess.PIPE if cached else None,
        stderr=subprocess.STDOUT,
        text=True,
    )
    chapters = sorted(outdir.glob("*/chapter_*.pdf"))
    if done.returncode:
        raise RuntimeError(
            f"ncert exited {done.returncode}; {len(chapters)} chapters landed. "
            "Call download_books() again to retry only the books that failed."
            + (f"\n{done.stdout}" if done.stdout else "")
        )
    return chapters
