"""Dedicated AI background agent for educational revision flashcards extraction."""

import logging

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from doubtless.domain import (
    Flashcard,
    FlashcardsPayload,
    TranscriptSegment,
    VideoChapter,
)
from doubtless.rag.llm import ai_model
from doubtless.storage.repositories import study_repo
from doubtless.study.context import format_lecture_context

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an academic tutor creating revision flashcards.

Analyze the transcript and chapter markers to extract up to 20 atomic revision
flashcards (typically 10 to 20) grounded directly in the teacher's lesson.

Grounding in Lecture Content:
- Extract atomic facts, key terms, formulas, definitions, and teacher shortcuts
  explicitly spoken in the lecture.
- `timestamp`: Float in seconds matching the EXACT segment in the transcript
  where the concept was introduced.

Card Sizing and Layout Constraints (Frontend 230px Card):
- The frontend renders each card in a compact fixed-height 230px container.
  Strict word limits must be observed:
  1. `front`: MAXIMUM 15 WORDS. Concise prompt, term, question, or formula name
     (e.g., "What is the formula for centripetal acceleration?").
  2. `back`: MAXIMUM 40 WORDS. Crisp, atomic definition, formula, or core fact.
     Do NOT write multi-paragraph explanations.
- Mathematical notation: Use clean Unicode math (e.g. x², Δv/Δt, F = ma) or
  inline backticks (`v = u + at`). Do NOT use LaTeX $ delimiters.

Schema and Field Specifications:
1. `id`: Sequential integer starting at 1.
2. `front`: Concise prompt (<= 15 words).
3. `back`: Concise answer or definition (<= 40 words).
4. `category`: One of 'Formula', 'Definition', 'Concept', or 'Shortcut'.
5. `timestamp`: Float in seconds matching the transcript where concept is taught."""

flashcards_agent = Agent[None, FlashcardsPayload](
    model=ai_model,
    name="flashcards_generator",
    output_type=FlashcardsPayload,
    system_prompt=_SYSTEM_PROMPT,
    model_settings=ModelSettings(temperature=0.1, timeout=60.0),
)


def generate_flashcards(
    video_id: str,
    segments: list[TranscriptSegment],
    chapters: list[VideoChapter],
) -> list[Flashcard]:
    """Generate quick-revision flashcards for a video lecture."""
    if not segments:
        study_repo.save_video_flashcards(video_id, [])
        return []

    context_text = format_lecture_context(segments, chapters)
    prompt = (
        "Extract up to 20 atomic revision flashcards (10 to 20) covering key "
        f"definitions, formulas, and concepts from the lecture:\n\n{context_text}"
    )

    try:
        result = flashcards_agent.run_sync(prompt)
        cards = result.output.cards
    except Exception as exc:
        logger.exception("Failed to generate flashcards: %s", exc)
        cards = []

    study_repo.save_video_flashcards(video_id, cards)
    return cards
