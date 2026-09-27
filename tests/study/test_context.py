"""Unit tests for study context formatting."""

from doubtless.domain import TranscriptSegment, VideoChapter
from doubtless.study.context import (
    format_dialogue_window,
    format_lecture_context,
)


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
    assert "- [00:00] Introduction: Basics of chemical bonding" in output
    assert "[LECTURE TRANSCRIPT]:" in output
    assert "[00:00] Hello everyone, today we discuss ionic bonds." in output


def test_format_dialogue_window() -> None:
    """Format transcript segments into timestamped dialogue lines."""
    segments = [
        TranscriptSegment(start=0.0, end=5.0, text="First point."),
        TranscriptSegment(start=65.0, end=70.0, text="Second point."),
    ]
    formatted = format_dialogue_window(segments)
    assert formatted == "[00:00] First point.\n[01:05] Second point."
