"""AI doubt-solving agent built on Pydantic AI and multi-modal retrieval."""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.settings import ModelSettings

from doubtless.core.formatting import format_timestamp
from doubtless.domain.schemas import BookChunk, LectureChunk, VideoNotes
from doubtless.rag.books.search import search_books as _search_books_impl
from doubtless.rag.lecture.search import search_lecture as _search_lecture_impl
from doubtless.rag.llm import ai_model as ai_model
from doubtless.storage import db


@dataclass(slots=True)
class DoubtContext:
    """Context passed into the doubt-solving agent on every student inquiry."""

    video_id: str
    current_time: float | None = None


_INSTRUCTIONS = """You are Doubtless, an expert AI academic tutor for video lectures.

Your mission is to resolve student doubts with uncompromising factual accuracy,
strictly grounded in the video lecture dialogue and official NCERT textbooks.

Hierarchy of Evidence and Grounding:
1. Grounding in [LOCAL PLAYHEAD DIALOGUE]:
   - When the student asks about what the teacher just said, just demonstrated,
     or what is currently happening on screen, inspect the provided
     [LOCAL PLAYHEAD DIALOGUE] first.
   - If the dialogue answers the question, ground your explanation directly
     in those spoken words and cite the exact timestamp.
2. Grounding in Lecture Audio via `search_lecture`:
   - When the question references earlier or later parts of the lecture,
     asks where a topic was taught, or when the local playhead window does not
     contain the required context, call `search_lecture(query)`.
3. Grounding in NCERT Textbooks via `search_books`:
   - When the student asks for formal curriculum definitions, standard theorems,
     official formulas, textbook derivations, SI units, or NCERT exercises,
     call `search_books(query)`.
   - Use NCERT to enrich and validate informal teacher remarks with standard
     curriculum terminology.
4. High-Level Roadmap and Overview via `get_chapter_notes`:
   - When the student asks for an overview, summary, table of contents, syllabus
     roadmap, or what topics are covered across the video, call `get_chapter_notes()`.

Citation Rules (Mandatory for Frontend Rendering):
- Lecture Moments: ALWAYS cite specific video moments using square brackets like
  [MM:SS] (e.g. [03:45]). The timestamp must match the exact time in the transcript
  or playhead dialogue.
- Textbook References: ALWAYS cite textbook passages using the exact format:
  [Class X | Book Name | Chapter Y | Page Z]
  (e.g. [Class 11 | Physics Part 1 | Chapter 3 | Page 42]). Extract Class, Book,
  Chapter, and Page directly from retrieved book chunk metadata.

Anti-Hallucination and Refusal Protocol:
- Every factual claim must be backed by the transcript or textbook sources.
- If information is absent from both the lecture transcript and NCERT textbooks,
  explicitly state that the topic is not covered in this lecture or NCERT books.
  Never invent facts, timestamps, or textbook citations.

Language and Tone:
- Students may ask in English, Hindi, or conversational Hinglish.
- Match the student's language style (friendly English or Hinglish) while
  keeping all scientific and mathematical terminology in standard English.

Formatting:
- Separate all paragraphs, bullet lists, and headings with a blank line
  (double newline). Never output dense walls of text.
- Use clean bullet points (`- `) with concise explanations.
- Write equations using Unicode characters (e.g. x², Δv/Δt, v = u + at, √x, θ)
  or inline code (`formula`), avoiding raw LaTeX math delimiters ($ or $$)."""

rag_agent = Agent[DoubtContext, str](
    model=ai_model,
    deps_type=DoubtContext,
    instructions=_INSTRUCTIONS,
    model_settings=ModelSettings(temperature=0.2, timeout=60.0),
)


@rag_agent.instructions
def inject_playhead_context(ctx: RunContext[DoubtContext]) -> str | None:
    """Dynamically inject local playhead dialogue window around playhead."""
    if ctx.deps.current_time is None:
        return None

    dialogue = db.get_transcript_dialogue_window(
        ctx.deps.video_id,
        ctx.deps.current_time,
        window_before=90.0,
        window_after=15.0,
    )
    if not dialogue:
        return None

    ts_formatted = format_timestamp(ctx.deps.current_time)
    return (
        f"[CURRENT VIDEO TIMESTAMP]: {ts_formatted}\n"
        f"[LOCAL PLAYHEAD DIALOGUE (~90s around pause point, not full video)]:\n"
        f"{dialogue}"
    )


@rag_agent.tool
def get_chapter_notes(ctx: RunContext[DoubtContext]) -> VideoNotes | None:
    """Retrieve pre-generated chapter notes and topic roadmap for this lecture.

    Call this tool when the student asks to summarise the video, asks what topics
    are covered, requests an overview or syllabus roadmap, or wants a high-level
    review of the entire lecture from start to finish.
    """
    return db.get_video_notes(ctx.deps.video_id)


@rag_agent.tool
def search_lecture(ctx: RunContext[DoubtContext], query: str) -> list[LectureChunk]:
    """Search across this specific video lecture's full spoken transcript.

    Call this tool when the student asks about something the teacher said earlier
    or later outside the local playhead window, asks where or at what timestamp a
    topic was explained, or requests a specific derivation from the teacher.
    """
    return _search_lecture_impl(ctx.deps.video_id, query, k=3)


@rag_agent.tool
def search_books(ctx: RunContext[DoubtContext], query: str) -> list[BookChunk]:
    """Search formal NCERT textbooks for official curriculum theory and formulas.

    Call this tool when the student needs official curriculum definitions,
    standard formulas, formal theorem statements, textbook derivations, standard
    notation and SI units, or NCERT exercise problems.
    """
    return _search_books_impl(query, k=5)
