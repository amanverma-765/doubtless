"""Dedicated AI background agent for educational study notes generation."""

import logging

from pydantic_ai import Agent

from doubtless.core.formatting import format_timestamp
from doubtless.domain.schemas import (
    TranscriptSegment,
    VideoChapter,
    VideoNotes,
    VideoNotesPayload,
)
from doubtless.rag.llm import ai_model
from doubtless.storage import db
from doubtless.study.context import format_lecture_context

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an academic tutor creating clean, student lecture notes.

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

notes_agent = Agent[None, VideoNotesPayload](
    model=ai_model,
    output_type=VideoNotesPayload,
    system_prompt=_SYSTEM_PROMPT,
)


def generate_notes(
    video_id: str,
    segments: list[TranscriptSegment],
    chapters: list[VideoChapter],
) -> VideoNotes:
    """Generate structured study notes based on transcript and chapters."""
    if not segments:
        empty_notes = VideoNotes(
            video_id=video_id,
            title="Lecture Notes",
            markdown=(
                "# Lecture Notes\n\n"
                "> No spoken lecture audio was detected for this video."
            ),
        )
        db.save_video_notes(empty_notes)
        return empty_notes

    context_text = format_lecture_context(
        segments, chapters, chapter_header="[PRE-IDENTIFIED CHAPTERS]:"
    )
    prompt = (
        "Generate clean, comprehensive, professional Markdown study notes based on the "
        f"chapters and transcript below:\n\n{context_text}"
    )

    try:
        result = notes_agent.run_sync(prompt)
        payload = result.output
        notes = VideoNotes(
            video_id=video_id,
            title=payload.title,
            markdown=payload.markdown,
        )
    except Exception as exc:
        logger.exception("Failed to generate notes via notes_agent: %s", exc)
        chapter_sections: list[str] = []
        for idx, c in enumerate(chapters, 1):
            ts = format_timestamp(c.start_time)
            chapter_sections.append(f"## {idx}. {c.title} [{ts}]\n\n{c.description}\n")

        fallback_md = (
            "# Lecture Study Notes\n\n"
            "> **Overview:** High-level summary of lecture topics.\n\n"
            "## 📌 Key Topics\n\n"
            f"{''.join(chapter_sections)}"
        )
        notes = VideoNotes(
            video_id=video_id,
            title="Lecture Study Notes",
            markdown=fallback_md,
        )

    db.save_video_notes(notes)
    return notes
