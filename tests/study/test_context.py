"""Unit tests for study context formatting."""

from doubtless.domain.schemas import TranscriptSegment, VideoChapter
from doubtless.study.context import format_lecture_context


def test_format_lecture_context() -> None:
    """Format chapter outlines and timestamped transcript into prompt text."""
    chapters = [
        VideoChapter(
            start_time=0.0,
            end_time=30.0,
            title="Introduction",
            description="Basics of chemical bonding",
        )
    ]
    segments = [
        TranscriptSegment(
            start=0.0,
            end=10.0,
            text="Hello everyone, today we discuss ionic bonds.",
        )
    ]
    output = format_lecture_context(segments, chapters)
    assert "[CHAPTER OUTLINE]:" in output
    assert "[00:00] Introduction: Basics of chemical bonding" in output
    assert "[LECTURE TRANSCRIPT]:" in output
    assert "[00:00] Hello everyone, today we discuss ionic bonds." in output
