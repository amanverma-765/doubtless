"""Unit tests verifying domain schema structure and exports."""

from doubtless.domain import (
    ChatMessage,
    Flashcard,
    HealthResponse,
    LectureChunk,
    QuizQuestion,
    TranscriptSegment,
    VideoChapter,
    VideoItemResponse,
    VideoNotes,
    VideoRecord,
)


def test_domain_schemas_reexports() -> None:
    """Verify that doubtless.domain exports domain models."""
    msg = ChatMessage(role="user", content="Hello test")
    assert msg.role == "user"
    assert msg.content == "Hello test"
    assert msg.created_at

    record = VideoRecord(
        id="vid_123",
        title="Physics 101",
        filename="vid_123.mp4",
        status="ready",
        created_at="2026-09-19T00:00:00Z",
    )
    assert record.id == "vid_123"
    assert record.status == "ready"

    item = VideoItemResponse(
        id="vid_123",
        title="Physics 101",
        status="ready",
        progress=1.0,
        created_at="2026-09-19T00:00:00Z",
    )
    assert item.progress == 1.0

    chapter = VideoChapter(
        start_time=0.0,
        end_time=60.0,
        title="Introduction",
        description="Intro to physics",
    )
    assert chapter.start_time == 0.0

    notes = VideoNotes(video_id="vid_123", markdown="# Notes")
    assert notes.video_id == "vid_123"

    quiz_q = QuizQuestion(
        id=1,
        question="What is v?",
        options=["Velocity", "Volume", "Voltage", "Vector"],
        correct_index=0,
        explanation="v stands for velocity.",
    )
    assert quiz_q.correct_index == 0

    card = Flashcard(id=1, front="F = ma", back="Newton's second law")
    assert card.category == "Concept"

    chunk = LectureChunk(
        video_id="vid_123",
        start_time=10.0,
        end_time=20.0,
        text="Sample text",
    )
    assert chunk.video_id == "vid_123"

    segment = TranscriptSegment(start=0.0, end=5.0, text="Hello world")
    assert segment.text == "Hello world"

    health = HealthResponse(status="ok", redis=True, data_dir=True, db=True)
    assert health.status == "ok"
