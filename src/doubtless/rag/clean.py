"""Repair the text that comes out of a PDF, one page at a time."""

import re
from collections import Counter

# "I N T R O D U C T I O N": headings set with letter tracking. Four letters
# minimum so ordinary prose ("I a m") is never a candidate.
_TRACKED = re.compile(r"\b(?:[A-Z] ){3,}[A-Z]\b")

# a word broken across a line: "photo-\nsynthesis". Only when the next line
# starts lowercase, so "well-\nKnown" style compounds survive.
_HYPHEN_BREAK = re.compile(r"(\w)-\n([a-z])")

# NCERT opens sections with a drop cap, which extracts as a lone capital on its
# own line ahead of the rest of the word
_DROP_CAP = re.compile(r"^([A-Z])\n(?=[a-z])", re.MULTILINE)

# NCERT fakes bold by overprinting a line 3-5 times and extraction keeps every
# copy. Runs of exactly 2 are real (table columns, repeated variables), so only
# 3+ collapse.
_OVERPRINT = re.compile(r"^(.+)$(?:\n\1$){2,}", re.MULTILINE)

_PAGE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")

# A page number sits in the top or bottom two lines. A lone number mid-page is
# content: a table cell or an equation coefficient.
_PAGE_EDGE = 2


def _is_page_number(text: str, position: int, total: int) -> bool:
    """Report whether a line is a page number rather than content."""
    if not _PAGE_NUMBER.match(text):
        return False
    return position < _PAGE_EDGE or position >= total - _PAGE_EDGE


def clean_text(text: str) -> str:
    """Normalize one page's extracted text."""
    text = text.replace("\xa0", " ")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _DROP_CAP.sub(r"\1", text)
    text = _TRACKED.sub(lambda m: m.group().replace(" ", ""), text)
    # keep newlines: strip_running_heads matches furniture line by line
    text = re.sub(r"[ \t]+", " ", text)
    # after the space collapse, so copies that differed only in spacing match
    text = _OVERPRINT.sub(r"\1", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def strip_running_heads(pages: list[str], threshold: float = 0.4) -> list[str]:
    """Drop short lines that repeat on 40%+ of a chapter's pages: the book
    title, chapter name and page numbers."""
    if len(pages) < 3:
        return pages

    counts = Counter(
        line.strip()
        for page in pages
        for line in page.splitlines()
        if 0 < len(line.strip()) <= 60
    )
    furniture = {
        line for line, n in counts.items() if n >= max(2, threshold * len(pages))
    }

    kept = []
    for page in pages:
        lines = [line for line in page.splitlines() if line.strip()]
        kept.append(
            "\n".join(
                line
                for position, line in enumerate(lines)
                if line.strip() not in furniture
                and not _is_page_number(line, position, len(lines))
            ).strip()
        )
    return kept
