"""Structured prompt context generation from transcripts and chapter markers."""

from doubtless.core.formatting import format_timestamp
from doubtless.domain.schemas import TranscriptSegment, VideoChapter


def format_lecture_context(
    segments: list[TranscriptSegment],
    chapters: list[VideoChapter],
    chapter_header: str = "[CHAPTER OUTLINE]:",
) -> str:
    """Combine chapter outline and transcript text into structured prompt context."""
    chapter_lines: list[str] = [chapter_header]
    for c in chapters:
        ts = format_timestamp(c.start_time)
        chapter_lines.append(f"- [{ts}] {c.title}: {c.description}")

    transcript_lines: list[str] = ["\n[LECTURE TRANSCRIPT]:"]
    for s in segments:
        ts = format_timestamp(s.start)
        transcript_lines.append(f"[{ts}] {s.text}")

    return "\n".join(chapter_lines + transcript_lines)
