"""Dedicated AI background agent for lecture chapterisation."""

import logging

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from doubtless.core.formatting import format_timestamp
from doubtless.domain.schemas import (
    ChaptersPayload,
    TranscriptSegment,
    VideoChapter,
)
from doubtless.rag.llm import ai_model
from doubtless.storage import db

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an editor specializing in educational video chapters.

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

chapter_agent = Agent[None, ChaptersPayload](
    model=ai_model,
    output_type=ChaptersPayload,
    system_prompt=_SYSTEM_PROMPT,
    model_settings=ModelSettings(temperature=0.1, timeout=60.0),
)


def _format_transcript_for_prompt(segments: list[TranscriptSegment]) -> str:
    """Format speech-to-text segments into chronological timestamped blocks."""
    lines: list[str] = []
    for s in segments:
        ts = format_timestamp(s.start)
        lines.append(f"[{ts}] {s.text}")
    return "\n".join(lines)


def generate_chapters(
    video_id: str,
    segments: list[TranscriptSegment],
) -> list[VideoChapter]:
    """Generate structured lecture chapters from speech transcript."""
    if not segments:
        return []

    transcript_text = _format_transcript_for_prompt(segments)
    prompt = (
        "Analyze the following timestamped lecture transcript and generate "
        f"clear chronological chapters:\n\n{transcript_text}"
    )

    try:
        result = chapter_agent.run_sync(prompt)
        chapters = result.output.chapters
    except Exception as exc:
        logger.exception("Failed to generate chapters via chapter_agent: %s", exc)
        total_duration = segments[-1].end if segments else 0.0
        chapters = [
            VideoChapter(
                start_time=0.0,
                end_time=round(total_duration, 2),
                title="Full Lecture",
                description="Complete recording of the lecture session.",
            )
        ]

    db.save_chapters(video_id, chapters)
    return chapters
