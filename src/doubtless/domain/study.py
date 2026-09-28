"""Lecture study artifact schemas: chapters, notes, quizzes, and flashcards."""

from pydantic import BaseModel, Field


class VideoChapter(BaseModel):
    """Timestamped lecture chapter marking a topic transition."""

    start_time: float
    end_time: float
    title: str
    description: str


class ChaptersPayload(BaseModel):
    """Structured LLM output payload for chapterisation."""

    chapters: list[VideoChapter] = Field(default_factory=list)


class VideoChaptersResponse(BaseModel):
    """API response model for video chapters."""

    video_id: str
    chapters: list[VideoChapter]


class VideoNotes(BaseModel):
    """Full lecture study notes formatted as a clean Markdown document."""

    video_id: str
    markdown: str
    title: str | None = None


class VideoNotesPayload(BaseModel):
    """Structured LLM output payload for lecture notes generation."""

    title: str = Field(description="Clean descriptive title of the lecture notes")
    markdown: str = Field(
        description="Comprehensive, beautifully structured Markdown study notes."
    )


class VideoNotesResponse(BaseModel):
    """API response model for video notes."""

    video_id: str
    notes: VideoNotes | None = None


class QuizQuestion(BaseModel):
    """Single multiple-choice question testing understanding of a lecture topic."""

    id: int
    question: str
    options: list[str] = Field(description="4 distinct answer options")
    correct_index: int = Field(description="0-based index of the correct option (0-3)")
    explanation: str = Field(description="Why the correct answer is right")
    timestamp: float | None = Field(
        default=None,
        description="Exact lecture timestamp (in seconds) where concept is taught",
    )


class QuizPayload(BaseModel):
    """Structured LLM output payload for quiz generation."""

    questions: list[QuizQuestion] = Field(default_factory=list)


class VideoQuizResponse(BaseModel):
    """API response model for video quiz."""

    video_id: str
    questions: list[QuizQuestion]


class Flashcard(BaseModel):
    """Single revision card with a concept/formula on front and answer on back."""

    id: int
    front: str = Field(description="Prompt, formula name, or concept question")
    back: str = Field(description="Concise definition, formula, or explanation")
    category: str = Field(
        default="Concept",
        description="Category: Formula, Definition, Concept, or Shortcut",
    )
    timestamp: float | None = Field(
        default=None,
        description="Lecture timestamp (in seconds) where term is explained",
    )


class FlashcardsPayload(BaseModel):
    """Structured LLM output payload for flashcards extraction."""

    cards: list[Flashcard] = Field(default_factory=list)


class VideoFlashcardsResponse(BaseModel):
    """API response model for video flashcards."""

    video_id: str
    cards: list[Flashcard]


class StudyGenerationError(Exception):
    """Raised when lecture study artifact generation fails or output is invalid."""
