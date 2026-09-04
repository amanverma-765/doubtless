"""Repair the text extracted from a PDF, one page at a time."""

import re
from collections import Counter

# Match headings set with letter tracking (e.g., "I N T R O D U C T I O N").
# Requires a minimum of four letters so ordinary prose ("I a m") is ignored.
_TRACKED = re.compile(r"\b(?:[A-Z] ){3,}[A-Z]\b")

# Match words hyphenated across a line break (e.g., "photo-\nsynthesis").
# Matches only when the next line starts with a lowercase letter, preserving
# capitalized compounds like "well-\nKnown".
_HYPHEN_BREAK = re.compile(r"(\w)-\n([a-z])")

# Match drop caps, which often extract as a lone capital letter on its own line
# preceding the rest of the word.
_DROP_CAP = re.compile(r"^([A-Z])\n(?=[a-z])", re.MULTILINE)

# Match pseudo-bold text created by overprinting a line 3-5 times.
# Duplicates (exactly 2) are kept as they may be table columns or repeated variables.
_OVERPRINT = re.compile(r"^(.+)$(?:\n\1$){2,}", re.MULTILINE)

# Match standard page number formats.
_PAGE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")

# Define the margin (number of lines at the top or bottom) where a page number
# is expected. A lone number mid-page is treated as content (e.g., a table cell).
_PAGE_EDGE = 2

# Map private-use codepoints used by some fonts in NCERT PDFs.
# 0xF000 is added to the byte the font drew. For the Symbol font, that byte
# is the Adobe Symbol encoding. For others, it is cp1252.
_SYMBOL_GLYPHS: dict[int, str | None] = {
    0x22: "∀", 0x24: "∃", 0x27: "∍", 0x2A: "∗", 0x2D: "−", 0x40: "≅",
    0x5C: "∴", 0x5E: "⊥", 0x60: None, 0x7E: "∼",
    **dict(zip(range(0x41, 0x5B), "ΑΒΧΔΕΦΓΗΙϑΚΛΜΝΟΠΘΡΣΤΥςΩΞΨΖ", strict=True)),
    **dict(zip(range(0x61, 0x7B), "αβχδεφγηιϕκλμνοπθρστυϖωξψζ", strict=True)),
    0xA1: "ϒ", 0xA2: "′", 0xA3: "≤", 0xA4: "⁄", 0xA5: "∞", 0xA6: "ƒ",
    0xAB: "↔", 0xAC: "←", 0xAD: "↑", 0xAE: "→", 0xAF: "↓",
    0xB0: "°", 0xB1: "±", 0xB2: "″", 0xB3: "≥", 0xB4: "×", 0xB5: "∝",
    0xB6: "∂", 0xB7: "•", 0xB8: "÷", 0xB9: "≠", 0xBA: "≡", 0xBB: "≈", 0xBC: "…",
    0xC0: "ℵ", 0xC1: "ℑ", 0xC2: "ℜ", 0xC3: "℘", 0xC4: "⊗", 0xC5: "⊕",
    0xC6: "∅", 0xC7: "∩", 0xC8: "∪", 0xC9: "⊃", 0xCA: "⊇", 0xCB: "⊄",
    0xCC: "⊂", 0xCD: "⊆", 0xCE: "∈", 0xCF: "∉",
    0xD0: "∠", 0xD1: "∇", 0xD2: "®", 0xD3: "©", 0xD4: "™", 0xD5: "∏",
    0xD6: "√", 0xD7: "⋅", 0xD8: "¬", 0xD9: "∧", 0xDA: "∨", 0xDB: "⇔",
    0xDC: "⇐", 0xDD: "⇑", 0xDE: "⇒", 0xDF: "⇓",
    0xE0: "◊", 0xE1: "〈", 0xE5: "∑", 0xF1: "〉", 0xF2: "∫",
}  # fmt: skip

# Drop the entire private-use area, then selectively map back readable codes.
# Unmapped glyph ids are dropped rather than embedded as junk characters.
_DROP: dict[int, str | None] = dict.fromkeys(range(0xE000, 0xF900))

_SYMBOL = _DROP | {
    0xF000 + c: _SYMBOL_GLYPHS.get(c, chr(c) if c < 0x7F else None)
    for c in range(0x20, 0x100)
}

_SHIFTED = _DROP | {
    0xF000 + c: bytes([c]).decode("cp1252", "ignore") or None
    for c in range(0x20, 0x100)
}


def decode_glyphs(text: str, font: str) -> str:
    """Decode private-use codepoints back to standard text based on the origin font."""
    return text.translate(_SYMBOL if font.startswith("Symbol") else _SHIFTED)


def _is_page_number(text: str, position: int, total: int) -> bool:
    """Determine if a line is a page number based on formatting and position."""
    if not _PAGE_NUMBER.match(text):
        return False
    return position < _PAGE_EDGE or position >= total - _PAGE_EDGE


def clean_text(text: str) -> str:
    """Normalize and clean the extracted text of a single page."""
    text = text.replace("\xa0", " ")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _DROP_CAP.sub(r"\1", text)
    text = _TRACKED.sub(lambda m: m.group().replace(" ", ""), text)

    # Retain newlines: strip_running_heads relies on line-by-line matching.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove overprinted lines after space collapse ensures exact matches.
    text = _OVERPRINT.sub(r"\1", text)

    return re.sub(r"\n{3,}", "\n\n", text).strip()


def strip_running_heads(pages: list[str], threshold: float = 0.4) -> list[str]:
    """
    Remove recurring headers, footers, and page numbers across a chapter.

    Lines that repeat on a high percentage of pages (default 40%+)
    are treated as document furniture and stripped.
    """
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
