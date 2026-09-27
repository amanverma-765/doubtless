"""Structured prompt context generation from transcripts and chapter markers."""

from doubtless.core.formatting import format_timestamp
from doubtless.domain import TranscriptSegment, VideoChapter
from doubtless.storage.repositories import transcript_repo


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


def format_dialogue_window(segments: list[TranscriptSegment]) -> str:
    """Format transcript segments within a window into timestamped dialogue lines."""
    return "\n".join(f"[{format_timestamp(s.start)}] {s.text}" for s in segments)


def get_transcript_dialogue_window(
    video_id: str,
    current_time: float,
    window_before: float = 60.0,
    window_after: float = 15.0,
) -> str:
    """Retrieve dialogue around current_time and format into timestamped lines."""
    segments = transcript_repo.get_transcript_segments_window(
        video_id, current_time, window_before=window_before, window_after=window_after
    )
    return format_dialogue_window(segments)
