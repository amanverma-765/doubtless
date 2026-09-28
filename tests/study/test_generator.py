"""Unit tests for the consolidated study generator module."""

from unittest.mock import MagicMock, patch

import pytest

from doubtless.domain import (
    ChaptersPayload,
    Flashcard,
    FlashcardsPayload,
    QuizPayload,
    QuizQuestion,
    StudyGenerationError,
    TranscriptSegment,
    VideoChapter,
    VideoNotesPayload,
)
from doubtless.study.generator import (
    generate_chapters,
    generate_flashcards,
    generate_notes,
    generate_quiz,
)


def _sample_segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start=0.0, end=30.0, text="Introduction to thermodynamics."),
        TranscriptSegment(
            start=30.0, end=60.0, text="First law explains conservation of energy."
        ),
    ]


def _sample_chapters() -> list[VideoChapter]:
    return [
        VideoChapter(
            start_time=0.0,
            end_time=60.0,
            title="Thermodynamics Intro",
            description="Overview of energy conservation",
        )
    ]


def test_generate_chapters_empty() -> None:
    """Empty segments produce empty chapter list."""
    assert generate_chapters([]) == []


def test_generate_chapters_success() -> None:
    """Successful agent output converts to VideoChapter list."""
    mock_payload = ChaptersPayload(
        chapters=[
            VideoChapter(
                start_time=0.0,
                end_time=60.0,
                title="Intro",
                description="Intro chapter",
            )
        ]
    )
    mock_result = MagicMock()
    mock_result.output = mock_payload

    with patch(
        "doubtless.study.generator.chapter_agent.run_sync", return_value=mock_result
    ):
        chapters = generate_chapters(_sample_segments())
        assert len(chapters) == 1
        assert chapters[0].title == "Intro"


def test_generate_chapters_raises_on_agent_error() -> None:
    """Agent failure raises StudyGenerationError."""
    with (
        patch(
            "doubtless.study.generator.chapter_agent.run_sync",
            side_effect=RuntimeError("LLM failed"),
        ),
        pytest.raises(StudyGenerationError, match="Failed to generate chapters"),
    ):
        generate_chapters(_sample_segments())


def test_generate_chapters_raises_on_empty_chapters() -> None:
    """Agent returning zero chapters raises StudyGenerationError."""
    mock_payload = ChaptersPayload(chapters=[])
    mock_result = MagicMock()
    mock_result.output = mock_payload

    with (
        patch(
            "doubtless.study.generator.chapter_agent.run_sync", return_value=mock_result
        ),
        pytest.raises(StudyGenerationError, match="produced 0 chapters"),
    ):
        generate_chapters(_sample_segments())


def test_generate_notes_empty() -> None:
    """Empty segments produce empty notes document."""
    notes = generate_notes("vid123", [], [])
    assert notes.video_id == "vid123"
    assert "No spoken lecture audio" in notes.markdown


def test_generate_notes_success() -> None:
    """Successful agent execution produces VideoNotes."""
    mock_payload = VideoNotesPayload(
        title="Custom Title",
        markdown="# Custom Title\n\nContent here",
    )
    mock_result = MagicMock()
    mock_result.output = mock_payload

    with patch(
        "doubtless.study.generator.notes_agent.run_sync", return_value=mock_result
    ):
        notes = generate_notes("vid123", _sample_segments(), _sample_chapters())
        assert notes.video_id == "vid123"
        assert notes.title == "Custom Title"
        assert "Content here" in notes.markdown


def test_generate_notes_raises_on_agent_error() -> None:
    """Agent failure raises StudyGenerationError."""
    with (
        patch(
            "doubtless.study.generator.notes_agent.run_sync",
            side_effect=RuntimeError("LLM timeout"),
        ),
        pytest.raises(StudyGenerationError, match="Failed to generate study notes"),
    ):
        generate_notes("vid123", _sample_segments(), _sample_chapters())


def test_generate_notes_raises_on_empty_markdown() -> None:
    """Agent returning empty markdown raises StudyGenerationError."""
    mock_payload = VideoNotesPayload(title="Empty Notes", markdown="   ")
    mock_result = MagicMock()
    mock_result.output = mock_payload

    with (
        patch(
            "doubtless.study.generator.notes_agent.run_sync", return_value=mock_result
        ),
        pytest.raises(StudyGenerationError, match="produced empty markdown"),
    ):
        generate_notes("vid123", _sample_segments(), _sample_chapters())


def test_generate_quiz_empty() -> None:
    """Empty segments return empty quiz question list."""
    assert generate_quiz([], []) == []


def test_generate_quiz_success() -> None:
    """Successful agent run returns quiz questions."""
    mock_payload = QuizPayload(
        questions=[
            QuizQuestion(
                id=1,
                question="What is the first law?",
                options=[
                    "Energy conserved",
                    "Entropy increases",
                    "Absolute zero",
                    "None",
                ],
                correct_index=0,
                explanation="Energy cannot be created or destroyed",
                timestamp=35.0,
            )
        ]
    )
    mock_result = MagicMock()
    mock_result.output = mock_payload

    with patch(
        "doubtless.study.generator.quiz_agent.run_sync", return_value=mock_result
    ):
        questions = generate_quiz(_sample_segments(), _sample_chapters())
        assert len(questions) == 1
        assert questions[0].question == "What is the first law?"


def test_generate_quiz_raises_on_agent_error() -> None:
    """Agent failure raises StudyGenerationError."""
    with (
        patch(
            "doubtless.study.generator.quiz_agent.run_sync",
            side_effect=RuntimeError("API error"),
        ),
        pytest.raises(StudyGenerationError, match="Failed to generate quiz"),
    ):
        generate_quiz(_sample_segments(), _sample_chapters())


def test_generate_quiz_raises_on_empty_questions() -> None:
    """Agent returning 0 questions raises StudyGenerationError."""
    mock_payload = QuizPayload(questions=[])
    mock_result = MagicMock()
    mock_result.output = mock_payload

    with (
        patch(
            "doubtless.study.generator.quiz_agent.run_sync", return_value=mock_result
        ),
        pytest.raises(StudyGenerationError, match="produced 0 questions"),
    ):
        generate_quiz(_sample_segments(), _sample_chapters())


def test_generate_flashcards_empty() -> None:
    """Empty segments return empty flashcards list."""
    assert generate_flashcards([], []) == []


def test_generate_flashcards_success() -> None:
    """Successful agent run returns flashcards."""
    mock_payload = FlashcardsPayload(
        cards=[
            Flashcard(
                id=1,
                front="First Law of Thermodynamics",
                back="Delta U = Q - W",
                category="Formula",
                timestamp=32.0,
            )
        ]
    )
    mock_result = MagicMock()
    mock_result.output = mock_payload

    with patch(
        "doubtless.study.generator.flashcards_agent.run_sync", return_value=mock_result
    ):
        cards = generate_flashcards(_sample_segments(), _sample_chapters())
        assert len(cards) == 1
        assert cards[0].front == "First Law of Thermodynamics"


def test_generate_flashcards_raises_on_agent_error() -> None:
    """Agent failure raises StudyGenerationError."""
    with (
        patch(
            "doubtless.study.generator.flashcards_agent.run_sync",
            side_effect=RuntimeError("API error"),
        ),
        pytest.raises(StudyGenerationError, match="Failed to generate flashcards"),
    ):
        generate_flashcards(_sample_segments(), _sample_chapters())


def test_generate_flashcards_raises_on_empty_cards() -> None:
    """Agent returning 0 cards raises StudyGenerationError."""
    mock_payload = FlashcardsPayload(cards=[])
    mock_result = MagicMock()
    mock_result.output = mock_payload

    with (
        patch(
            "doubtless.study.generator.flashcards_agent.run_sync",
            return_value=mock_result,
        ),
        pytest.raises(StudyGenerationError, match="produced 0 flashcards"),
    ):
        generate_flashcards(_sample_segments(), _sample_chapters())
