"""Structured prompt context generation from transcripts and chapter markers."""

from doubtless.core.formatting import format_timestamp
from doubtless.domain.schemas import TranscriptSegment, VideoChapter


def format_lecture_context(
    segments: list[TranscriptSegment],
    chapters: list[VideoChapter],
    chapter_header: str = "[CHAPTER OUTLINE]:",
) -> str:
    """Combine chapter outline and transcript text into structured prompt context."""
    # ponytail: clean list comprehensions instead of imperative append loops
    chapter_lines = [chapter_header] + [
        f"- [{format_timestamp(c.start_time)}] {c.title}: {c.description}"
        for c in chapters
    ]
    transcript_lines = ["\n[LECTURE TRANSCRIPT]:"] + [
        f"[{format_timestamp(s.start)}] {s.text}" for s in segments
    ]
    return "\n".join(chapter_lines + transcript_lines)
