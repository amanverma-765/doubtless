"""Unit tests for transcript semantic chunker."""

from doubtless.domain import TranscriptSegment
from doubtless.rag.lecture.chunker import chunk_transcript


def test_chunk_transcript_empty() -> None:
    """Empty segments produce empty chunks."""
    assert chunk_transcript("v1", []) == []


def test_chunk_transcript_aggregates_to_target_duration() -> None:
    """Small segments aggregate until reaching target duration with overlap."""
    segments = [
        TranscriptSegment(start=0.0, end=15.0, text="First sentence."),
        TranscriptSegment(start=15.0, end=30.0, text="Second sentence."),
        TranscriptSegment(start=30.0, end=46.0, text="Third sentence."),
        TranscriptSegment(start=46.0, end=65.0, text="Fourth sentence."),
        TranscriptSegment(start=65.0, end=95.0, text="Fifth sentence."),
    ]
    chunks = chunk_transcript("v1", segments, target_duration=45.0, min_duration=15.0)
    assert len(chunks) >= 2
    # First chunk spans first 3 segments (0.0 to 46.0s)
    assert chunks[0].start_time == 0.0
    assert chunks[0].end_time == 46.0
    assert "First sentence." in chunks[0].text
    assert "Third sentence." in chunks[0].text

    # Second chunk has boundary overlap from the third segment
    assert chunks[1].start_time == 30.0


def test_chunk_transcript_merges_trailing_short_segments() -> None:
    """Trailing segments under min_duration merge into the preceding chunk."""
    segments = [
        TranscriptSegment(start=0.0, end=40.0, text="Main discussion part 1."),
        TranscriptSegment(start=40.0, end=46.0, text="Main discussion part 2."),
        TranscriptSegment(start=46.0, end=48.0, text="Thank you."),  # short 2s
    ]
    chunks = chunk_transcript("v1", segments, target_duration=45.0, min_duration=20.0)
    assert len(chunks) == 1
    assert chunks[0].start_time == 0.0
    assert chunks[0].end_time == 48.0
    assert "Thank you." in chunks[0].text


def test_chunk_transcript_does_not_duplicate_boundary_overlap() -> None:
    """Ensure boundary overlap segment is not duplicated in final chunk."""
    segments = [
        TranscriptSegment(start=0.0, end=40.0, text="Segment 1."),
        TranscriptSegment(start=40.0, end=50.0, text="Segment 2."),
    ]
    chunks = chunk_transcript("v1", segments, target_duration=45.0, min_duration=20.0)
    assert len(chunks) == 1
    assert chunks[0].start_time == 0.0
    assert chunks[0].end_time == 50.0
    # Must appear exactly once, not duplicated as 'Segment 2. Segment 2.'
    assert chunks[0].text == "Segment 1. Segment 2."
