"""Unit tests for SQLite storage repositories and connection lifecycle."""

from pathlib import Path

from doubtless.domain import (
    Flashcard,
    QuizQuestion,
    TranscriptSegment,
    VideoChapter,
    VideoNotes,
)
from doubtless.storage import connection
from doubtless.storage.repositories import (
    chat_repo,
    study_repo,
    transcript_repo,
    video_repo,
)
from doubtless.study.context import get_transcript_dialogue_window


def test_connection_health(temp_db: Path) -> None:
    """Test database health check returns True on valid connection."""
    assert connection.check_db_health() is True


def test_video_crud_lifecycle(temp_db: Path) -> None:
    """Test video creation, retrieval, listing, updating, and deletion."""
    created = video_repo.create_video(
        video_id="v1",
        title="Calculus Lecture",
        filename="v1.mp4",
        status="uploading",
    )
    assert created.id == "v1"
    assert created.status == "uploading"

    fetched = video_repo.get_video("v1")
    assert fetched is not None
    assert fetched.id == "v1"
    assert fetched.title == "Calculus Lecture"

    # List
    all_videos = video_repo.list_videos()
    assert len(all_videos) == 1
    assert all_videos[0].id == "v1"

    # Update
    video_repo.update_video("v1", status="ready", playlist="/hls/v1/index.m3u8")
    updated = video_repo.get_video("v1")
    assert updated is not None
    assert updated.status == "ready"
    assert updated.playlist == "/hls/v1/index.m3u8"

    # Delete
    deleted = video_repo.delete_video("v1")
    assert deleted is True
    assert video_repo.get_video("v1") is None


def test_study_artifacts_storage(temp_db: Path) -> None:
    """Test saving and retrieving chapters, notes, quiz, and flashcards."""
    video_repo.create_video("v2", "Physics", "v2.mp4")

    # Chapters
    chapters = [
        VideoChapter(
            start_time=0.0,
            end_time=30.0,
            title="Intro",
            description="Introduction",
        ),
        VideoChapter(
            start_time=30.0,
            end_time=90.0,
            title="Kinematics",
            description="Motion",
        ),
    ]
    study_repo.save_chapters("v2", chapters)
    retrieved_chapters = study_repo.get_chapters("v2")
    assert len(retrieved_chapters) == 2
    assert retrieved_chapters[0].title == "Intro"
    assert retrieved_chapters[1].title == "Kinematics"

    # Notes
    notes = VideoNotes(
        video_id="v2",
        title="Physics Notes",
        markdown="# Motion\n$v = u + at$",
    )
    study_repo.save_video_notes(notes)
    retrieved_notes = study_repo.get_video_notes("v2")
    assert retrieved_notes is not None
    assert retrieved_notes.title == "Physics Notes"
    assert "Motion" in retrieved_notes.markdown

    # Quiz
    quiz = [
        QuizQuestion(
            id=1,
            question="What is the unit of force?",
            options=["Newton", "Joule", "Watt", "Pascal"],
            correct_index=0,
            explanation="1 N = 1 kg*m/s^2",
        )
    ]
    study_repo.save_video_quiz("v2", quiz)
    retrieved_quiz = study_repo.get_video_quiz("v2")
    assert len(retrieved_quiz) == 1
    assert retrieved_quiz[0].options[0] == "Newton"

    # Flashcards
    cards = [
        Flashcard(
            id=1,
            front="Force formula",
            back="F = ma",
            category="Formula",
        )
    ]
    study_repo.save_video_flashcards("v2", cards)
    retrieved_cards = study_repo.get_video_flashcards("v2")
    assert len(retrieved_cards) == 1
    assert retrieved_cards[0].back == "F = ma"

    # Transcripts & dialogue window
    segments = [
        TranscriptSegment(start=0.0, end=10.0, text="Welcome students."),
        TranscriptSegment(start=10.0, end=25.0, text="Today we discuss Newton's laws."),
    ]
    transcript_repo.insert_transcripts("v2", segments)
    db_segments = transcript_repo.get_transcript_segments_window(
        "v2", current_time=15.0
    )
    assert len(db_segments) == 2
    assert db_segments[0].text == "Welcome students."

    window = get_transcript_dialogue_window("v2", current_time=15.0)
    assert "[00:00] Welcome students." in window
    assert "[00:10] Today we discuss Newton's laws." in window

    # Dialogue window should be empty when current_time is far ahead of spoken segments
    empty_window = get_transcript_dialogue_window("v2", current_time=200.0)
    assert empty_window == ""

    # Active chapter at time
    ch_intro = study_repo.get_chapter_at_time("v2", 15.0)
    ch_kin = study_repo.get_chapter_at_time("v2", 45.0)
    assert ch_intro is not None and ch_intro.title == "Intro"
    assert ch_kin is not None and ch_kin.title == "Kinematics"

    # Chat messages
    chat_repo.add_message("v2", role="user", content="What is force?")
    chat_repo.add_message("v2", role="assistant", content="Force is an interaction...")
    msgs = chat_repo.get_messages("v2")
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[1].role == "assistant"

    # Clear chat messages
    deleted_count = chat_repo.clear_messages("v2")
    assert deleted_count == 2
    assert len(chat_repo.get_messages("v2")) == 0
