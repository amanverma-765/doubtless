"""Dedicated AI background agent for lecture quiz generation."""

import logging

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from doubtless.domain.schemas import (
    QuizPayload,
    QuizQuestion,
    TranscriptSegment,
    VideoChapter,
)
from doubtless.rag.llm import ai_model
from doubtless.storage import db
from doubtless.study.context import format_lecture_context

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert tutor creating multiple-choice quiz questions.

Analyze the timestamped lecture transcript and chapter outline to generate
up to 15 conceptual quiz questions (typically 8 to 15) testing student comprehension.

Grounding in Lecture Content:
- Every question MUST test a concept, formula, derivation, or problem
  explicitly taught by the teacher in the transcript.
- Do NOT introduce outside trivia or unmentioned curriculum prerequisites.
- `timestamp`: Float in seconds matching the EXACT lecture timestamp where the
  teacher explains or demonstrates the answer.

Option Balance and Anti-Bias:
- Distribute `correct_index` evenly across 0, 1, 2, and 3 (options A, B, C, D):
  * Ensure all four indices are represented in roughly equal proportions.
  * Never place the correct answer predominantly at index 0 or 1.
- Provide exactly 4 plausible, distinct options of similar length and phrasing.
- NEVER use "All of the above", "None of the above", or "Both A and B".

Schema and Formatting Rules:
1. `id`: Sequential integer starting at 1.
2. `question`: Focused question testing conceptual understanding.
3. `options`: List of exactly 4 strings. Use Unicode math (e.g. x², Δv/Δt)
   rather than LaTeX $ delimiters.
4. `correct_index`: Zero-based integer (0 to 3) indicating the correct option.
5. `explanation`: 1-2 concise sentences explaining why the option is correct,
   referencing the teacher's lesson.
6. `timestamp`: Float timestamp in seconds from the transcript where the
   solution is taught."""

quiz_agent = Agent[None, QuizPayload](
    model=ai_model,
    output_type=QuizPayload,
    system_prompt=_SYSTEM_PROMPT,
    model_settings=ModelSettings(temperature=0.1, timeout=60.0),
)


def generate_quiz(
    video_id: str,
    segments: list[TranscriptSegment],
    chapters: list[VideoChapter],
) -> list[QuizQuestion]:
    """Generate interactive multiple-choice quiz questions for a video lecture."""
    if not segments:
        db.save_video_quiz(video_id, [])
        return []

    context_text = format_lecture_context(segments, chapters)
    prompt = (
        "Generate up to 15 multiple-choice quiz questions (8 to 15) with explanations "
        f"and timestamps based on the following lecture:\n\n{context_text}"
    )

    try:
        result = quiz_agent.run_sync(prompt)
        questions = result.output.questions
    except Exception as exc:
        logger.exception("Failed to generate quiz via quiz_agent: %s", exc)
        questions = []

    db.save_video_quiz(video_id, questions)
    return questions
