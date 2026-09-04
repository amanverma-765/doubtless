"""Refetch the textbooks under data/books, which git does not carry."""

import subprocess
import sys
from pathlib import Path

BOOKS_DIR = Path(__file__).resolve().parents[3] / "data" / "books"

# English PCMB, classes 10-12. Class 10 has no split physics/chemistry/biology:
# one 'Science' book (jesc1) covers all three. Codes come from `ncert --list`.
CODES = (
    "jemh1",
    "jesc1",  # class 10
    "keph1",
    "keph2",
    "kech1",
    "kech2",
    "kemh1",
    "kebo1",  # class 11
    "leph1",
    "leph2",
    "lech1",
    "lech2",
    "lemh1",
    "lemh2",
    "lebo1",  # class 12
)


def download_books(outdir: Path = BOOKS_DIR) -> list[Path]:
    """Download every book as one PDF per chapter. Returns the PDFs on disk."""
    outdir.mkdir(parents=True, exist_ok=True)
    # Prelims are the cover and contents: no prose to retrieve, and their page
    # numbering does not line up with the chapters'.
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "ncert_cli",
            *CODES,
            "--chapters",
            "--no-prelims",
            "-o",
            str(outdir),
        ]
    )
    chapters = sorted(outdir.glob("*/chapter_*.pdf"))
    if done.returncode:
        raise RuntimeError(
            f"ncert exited {done.returncode}; {len(chapters)} chapters landed. "
            "Call download() again to retry only the books that failed."
        )
    return chapters
