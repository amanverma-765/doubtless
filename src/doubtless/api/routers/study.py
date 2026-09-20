"""Lecture study endpoints: chapters, study notes, quizzes, and flashcards."""

from fastapi import APIRouter, HTTPException

from doubtless.domain.schemas import (
    VideoChaptersResponse,
    VideoFlashcardsResponse,
    VideoNotesResponse,
    VideoQuizResponse,
)
from doubtless.storage import db

router = APIRouter(prefix="/videos", tags=["study"])


@router.get("/{video_id}/chapters", response_model=VideoChaptersResponse)
def get_video_chapters(video_id: str) -> VideoChaptersResponse:
    """Retrieve pre-generated topic chapters for a video."""
    if not db.get_video(video_id):
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )
    chapters = db.get_chapters(video_id)
    return VideoChaptersResponse(video_id=video_id, chapters=chapters)


@router.get("/{video_id}/notes", response_model=VideoNotesResponse)
def get_video_notes(video_id: str) -> VideoNotesResponse:
    """Retrieve structured study notes and takeaways for a video."""
    if not db.get_video(video_id):
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )
    notes = db.get_video_notes(video_id)
    return VideoNotesResponse(video_id=video_id, notes=notes)


@router.get("/{video_id}/quiz", response_model=VideoQuizResponse)
def get_video_quiz(video_id: str) -> VideoQuizResponse:
    """Retrieve generated interactive quiz questions for a video."""
    if not db.get_video(video_id):
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )
    questions = db.get_video_quiz(video_id)
    return VideoQuizResponse(video_id=video_id, questions=questions)


@router.get("/{video_id}/flashcards", response_model=VideoFlashcardsResponse)
def get_video_flashcards(video_id: str) -> VideoFlashcardsResponse:
    """Retrieve generated revision flashcards for a video."""
    if not db.get_video(video_id):
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )
    cards = db.get_video_flashcards(video_id)
    return VideoFlashcardsResponse(video_id=video_id, cards=cards)
