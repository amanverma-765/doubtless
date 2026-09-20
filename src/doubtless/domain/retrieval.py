"""Vector and transcript retrieval chunk schemas."""

from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    """Timestamped segment produced by speech-to-text transcription."""

    start: float
    end: float
    text: str


class LectureChunk(BaseModel):
    """Semantic chunk from a lecture transcript stored in vector database."""

    video_id: str
    start_time: float
    end_time: float
    text: str


class BookChunk(BaseModel):
    """Textbook passage chunk retrieved from NCERT vector index."""

    grade: int
    book: str
    chapter: int
    page: int
    text: str
