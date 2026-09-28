"""Consolidated AI background generator for lecture study artifacts.

Produces structured topic chapters, Markdown study notes, revision quizzes,
and flashcards grounded directly in lecture transcripts. Pure generation
functions return domain models without performing database writes.
"""

import logging

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from doubtless.domain import (
    ChaptersPayload,
    Flashcard,
    FlashcardsPayload,
    QuizPayload,
    QuizQuestion,
    StudyGenerationError,
    TranscriptSegment,
    VideoChapter,
    VideoNotes,
    VideoNotesPayload,
)
from doubtless.rag.llm import ai_model
from doubtless.study.context import format_dialogue_window, format_lecture_context

logger = logging.getLogger(__name__)

# --- System Prompts ---

_CHAPTERS_SYSTEM_PROMPT = """You are an editor for educational video chapters.

Your task is to analyze a timestamped transcript of a video lecture and detect
clear, chronological topic transitions and chapter boundaries.

Grounding in Spoken Transcript:
- Anchor chapter boundaries strictly to spoken topic shifts where the teacher
  introduces a new concept, begins a derivation, starts a numerical example,
  or delivers closing remarks.
- `title`: Clear, descriptive title reflecting the specific topic taught
  (e.g. 'Newton's Second Law & Momentum').
- `description`: 1-2 concise sentences summarizing the teacher's explanation
  and examples in that segment.

Strict Temporal Consistency and Invariants:
1. Origin: The first chapter must start at 0.0 seconds (`start_time: 0.0`).
2. Contiguous & Non-Overlapping: Every subsequent chapter's `start_time` must
   EXACTLY equal the preceding chapter's `end_time` (start_i = end_{i-1}).
   No time gaps and no overlaps.
3. Minimum Duration: Every chapter must span at least 45.0 seconds
   (end_time - start_time >= 45.0), unless the entire lecture is shorter than
   45 seconds.
4. Total Coverage: The final chapter's `end_time` must match or exceed the
   timestamp of the last segment in the transcript.
5. Chapter Count: Divide the lecture into 3 to 8 logical, non-overlapping
   chapters based on natural lecture progression."""

_NOTES_SYSTEM_PROMPT = """You are an academic tutor creating lecture notes.

Your task is to analyze a timestamped lecture transcript and pre-identified
chapters to produce a structured Markdown study guide grounded directly in the
teacher's spoken instruction.

Grounding in Spoken Lecture and Chapters:
- Ground notes strictly in the teacher's actual verbal explanations,
  step-by-step derivations, numerical examples, and analogies from class.
- Do NOT output generic textbook summaries that ignore what was taught. If the
  teacher solved a specific problem with specific numbers, document that solution.
- Follow the exact chronological sequence of the provided [PRE-IDENTIFIED CHAPTERS].

Mathematical & Typography Formatting:
1. Math Expressions:
   - Use clean Unicode symbols (e.g. x², x₁, Δv/Δt, v = u + at, F = dp/dt, θ, λ,
     α, β, π, √x, ∫, ≈, ≠, ±, ×, ÷) or inline backticks (`v = u + at`).
   - NEVER use LaTeX math delimiters ($...$ or $$...$$). The frontend renders
     standard Markdown and will display broken LaTeX code.
2. Interactive Video Timestamp Tags:
   - Embed exact timestamp tags `[MM:SS]` (e.g. `[02:15]`) in section headings
     and beside key derivations.
   - Timestamps must accurately match transcript moments to enable video seeking.
3. Clean Document Structure:
   - `# <Clear, Descriptive Lecture Title>`
   - `> **Overview:** 2-3 sentences summarizing core topic and outcomes.`
   - `## 📌 Key Takeaways`
     - High-yield bullet points capturing core formulas, definitions, and rules.
   - Chapter Sections (one section per pre-identified chapter):
     `## <N>. <Topic Name> [MM:SS]`
     - Conceptual breakdown in concise paragraphs and bullet points.
     - Step-by-step derivations or numerical steps formatted in clean blocks.
     - Exam callouts: `> 💡 **Key Concept:** ...`
   - `## 🔄 Quick Review & Summary`
     - Concise comparison table or bulleted summary recapping main takeaways.
4. Spacing:
   - Always separate headings, paragraphs, callouts, and lists with a blank line.
   - Produce only structured notes without conversational chit-chat."""

_QUIZ_SYSTEM_PROMPT = """You are an academic tutor creating quiz questions for exams.

Your task is to generate up to 15 high-yield multiple-choice questions (typically
8 to 15 questions) directly testing concepts taught in the video lecture.

Question Design & Cognitive Balance:
- Distribute questions across multiple Bloom's taxonomy levels:
  1. Direct Recall (40%): Definitions, laws, formulas, units, SI units, and values.
  2. Conceptual Understanding (40%): Explaining why a phenomenon occurs, identifying
     underlying causes, predicting what happens when variables change.
  3. Numerical Application & Calculation (20%): Simple step-by-step numerical
     problems matching the exact formulas and numbers demonstrated in the lecture.
- Ground all questions strictly in what the teacher explained in the transcript.
  Do NOT test obscure trivia outside the video lecture content.

Option Guidelines (4 Options per Question):
- Exactly 4 options per question: options must be distinct and mutually exclusive.
- Plausible Distractors: Incorrect options must reflect common student misconceptions,
  algebraic sign errors (e.g. + vs -), or common arithmetic mistakes.
- Avoid obvious giveaways like 'All of the above' or 'None of the above'.
- Keep option lengths reasonably balanced to prevent clueing the correct answer.

Explanation & Timestamp Grounding:
- `explanation`: 1-2 concise, clear sentences explaining why the correct option is
  right and highlighting the key concept.
- `timestamp`: Float in seconds matching the EXACT segment in the transcript where
  the teacher explained this concept. Enables the student to jump to the lecture
  moment to review."""

_FLASHCARDS_SYSTEM_PROMPT = """You are an academic tutor creating revision flashcards.

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

# --- Agents ---

chapter_agent = Agent[None, ChaptersPayload](
    model=ai_model,
    name="chapteriser",
    output_type=ChaptersPayload,
    system_prompt=_CHAPTERS_SYSTEM_PROMPT,
    model_settings=ModelSettings(temperature=0.1, timeout=60.0),
)

notes_agent = Agent[None, VideoNotesPayload](
    model=ai_model,
    name="study_notes",
    output_type=VideoNotesPayload,
    system_prompt=_NOTES_SYSTEM_PROMPT,
    model_settings=ModelSettings(temperature=0.1, timeout=90.0),
)

quiz_agent = Agent[None, QuizPayload](
    model=ai_model,
    name="quiz_generator",
    output_type=QuizPayload,
    system_prompt=_QUIZ_SYSTEM_PROMPT,
    model_settings=ModelSettings(temperature=0.1, timeout=60.0),
)

flashcards_agent = Agent[None, FlashcardsPayload](
    model=ai_model,
    name="flashcards_generator",
    output_type=FlashcardsPayload,
    system_prompt=_FLASHCARDS_SYSTEM_PROMPT,
    model_settings=ModelSettings(temperature=0.1, timeout=60.0),
)


# --- Pure Generation Functions ---


def generate_chapters(
    segments: list[TranscriptSegment],
) -> list[VideoChapter]:
    """Generate structured lecture chapters from speech transcript."""
    if not segments:
        return []

    transcript_text = format_dialogue_window(segments)
    prompt = (
        "Analyze the following timestamped lecture transcript and generate "
        f"clear chronological chapters:\n\n{transcript_text}"
    )

    try:
        result = chapter_agent.run_sync(prompt)
    except Exception as exc:
        logger.exception("Failed to generate chapters via chapter_agent: %s", exc)
        raise StudyGenerationError(f"Failed to generate chapters: {exc}") from exc

    chapters = result.output.chapters
    if not chapters:
        raise StudyGenerationError("Chapter generator produced 0 chapters.")
    return chapters


def generate_notes(
    video_id: str,
    segments: list[TranscriptSegment],
    chapters: list[VideoChapter],
) -> VideoNotes:
    """Generate structured study notes based on transcript and chapters."""
    if not segments:
        return VideoNotes(
            video_id=video_id,
            title="Lecture Notes",
            markdown=(
                "# Lecture Notes\n\n"
                "> No spoken lecture audio was detected for this video."
            ),
        )

    context_text = format_lecture_context(
        segments, chapters, chapter_header="[PRE-IDENTIFIED CHAPTERS]:"
    )
    prompt = (
        "Generate clean, comprehensive, professional Markdown study notes based on the "
        f"chapters and transcript below:\n\n{context_text}"
    )

    try:
        result = notes_agent.run_sync(prompt)
    except Exception as exc:
        logger.exception("Failed to generate notes via notes_agent: %s", exc)
        raise StudyGenerationError(f"Failed to generate study notes: {exc}") from exc

    payload = result.output
    if not payload.markdown or not payload.markdown.strip():
        raise StudyGenerationError("Notes generator produced empty markdown.")

    return VideoNotes(
        video_id=video_id,
        title=payload.title,
        markdown=payload.markdown,
    )


def generate_quiz(
    segments: list[TranscriptSegment],
    chapters: list[VideoChapter],
) -> list[QuizQuestion]:
    """Generate interactive multiple-choice quiz questions for a video lecture."""
    if not segments:
        return []

    context_text = format_lecture_context(segments, chapters)
    prompt = (
        "Generate up to 15 multiple-choice quiz questions (8 to 15) with explanations "
        f"and timestamps based on the following lecture:\n\n{context_text}"
    )

    try:
        result = quiz_agent.run_sync(prompt)
    except Exception as exc:
        logger.exception("Failed to generate quiz via quiz_agent: %s", exc)
        raise StudyGenerationError(f"Failed to generate quiz: {exc}") from exc

    questions = result.output.questions
    if not questions:
        raise StudyGenerationError("Quiz generator produced 0 questions.")
    return questions


def generate_flashcards(
    segments: list[TranscriptSegment],
    chapters: list[VideoChapter],
) -> list[Flashcard]:
    """Generate quick-revision flashcards for a video lecture."""
    if not segments:
        return []

    context_text = format_lecture_context(segments, chapters)
    prompt = (
        "Extract up to 20 atomic revision flashcards (10 to 20) covering key "
        f"definitions, formulas, and concepts from the lecture:\n\n{context_text}"
    )

    try:
        result = flashcards_agent.run_sync(prompt)
    except Exception as exc:
        logger.exception("Failed to generate flashcards: %s", exc)
        raise StudyGenerationError(f"Failed to generate flashcards: {exc}") from exc

    cards = result.output.cards
    if not cards:
        raise StudyGenerationError("Flashcards generator produced 0 flashcards.")
    return cards
