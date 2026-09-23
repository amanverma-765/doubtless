"""Asynchronous Celery tasks for media transcoding, transcription, and indexing."""

import concurrent.futures
import logging
import shutil
from pathlib import Path
from typing import Any

from doubtless.media.probe import probe_video
from doubtless.media.transcoder import extract_poster, transcode_with_progress
from doubtless.media.transcriber import extract_audio, transcribe_audio
from doubtless.rag.lecture.chunker import chunk_transcript
from doubtless.rag.lecture.indexer import index_lecture_chunks
from doubtless.storage import db, file_storage, redis_store
from doubtless.storage.cascade_delete import cascade_delete_video
from doubtless.study.chapteriser import generate_chapters
from doubtless.study.flashcards import generate_flashcards
from doubtless.study.notes import generate_notes
from doubtless.study.quiz import generate_quiz
from doubtless.worker.celery_app import celery_app

_logger = logging.getLogger(__name__)


STAGE_PROGRESS_RANGES: dict[str, tuple[float, float]] = {
    "transcoding": (0.00, 0.25),
    "transcribing": (0.25, 0.70),
    "indexing": (0.70, 0.85),
    "generating_notes": (0.85, 1.00),
}


def calc_overall_progress(stage: str, stage_progress: float) -> float:
    """Map local stage progress monotonically into overall pipeline progress."""
    start, end = STAGE_PROGRESS_RANGES.get(stage, (0.0, 1.0))
    clamped = min(1.0, max(0.0, stage_progress))
    return round(start + clamped * (end - start), 4)


@celery_app.task(bind=True)
def transcode_video(
    self: Any,
    video_id: str,
    src: str,
) -> dict[str, Any]:
    """Execute HLS transcoding, audio transcription, and vector indexing."""
    src_path = Path(src)
    if not src_path.is_file():
        _logger.info(
            "Source file %s no longer exists on disk (video deleted/cancelled). "
            "Skipping task for video %s.",
            src_path,
            video_id,
        )
        return {"cancelled": True}

    out = file_storage.hls_dir(video_id)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    audio_wav = out / "audio.wav"

    def _is_cancelled() -> bool:
        return redis_store.is_cancelled(video_id) or db.get_video(video_id) is None

    def _update_progress(
        p: float,
        stage: str = "transcoding",
        message: str = "",
    ) -> None:
        overall = calc_overall_progress(stage, p)
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": overall,
                "stage": stage,
                "stage_progress": min(1.0, max(0.0, p)),
                "message": message,
            },
        )
        redis_store.set_transcode_progress(
            video_id, overall, stage=stage, message=message
        )

    def _cleanup_cancelled() -> dict[str, Any]:
        audio_wav.unlink(missing_ok=True)
        cascade_delete_video(video_id)
        redis_store.clear_cancellation(video_id)
        return {"cancelled": True}

    try:
        # Probe media file once for duration and streams
        media_info = probe_video(src_path)

        # Phase 1: Poster extraction & HLS transcoding (transcoding 0% -> 25%)
        _update_progress(
            0.0, stage="transcoding", message="Preparing video transcoding…"
        )
        extract_poster(src_path, out / "poster.jpg")

        def _on_hls_prog(p: float) -> None:
            _update_progress(
                p,
                stage="transcoding",
                message="Transcoding video (HLS)",
            )

        transcode_with_progress(
            src_path,
            out,
            on_progress=_on_hls_prog,
            should_stop=_is_cancelled,
            info=media_info,
        )

        if _is_cancelled():
            return _cleanup_cancelled()

        _update_progress(1.0, stage="transcoding", message="Transcoding complete")

        # Phase 2: Audio extraction & Whisper transcription (transcribing 25% -> 70%)
        _update_progress(0.0, stage="transcribing", message="Extracting audio track…")
        has_audio = extract_audio(
            src_path,
            audio_wav,
            has_audio=media_info.acodec is not None,
        )

        if _is_cancelled():
            return _cleanup_cancelled()

        segments = []
        if has_audio and audio_wav.is_file():
            duration = media_info.duration

            def _on_whisper_prog(p: float) -> None:
                _update_progress(
                    p,
                    stage="transcribing",
                    message="Transcribing speech with AI (GPU)",
                )

            segments = transcribe_audio(
                audio_wav,
                total_duration=duration,
                on_progress=_on_whisper_prog,
                should_stop=_is_cancelled,
            )
            audio_wav.unlink(missing_ok=True)

        if _is_cancelled():
            return _cleanup_cancelled()

        _update_progress(1.0, stage="transcribing", message="Transcription complete")

        # Phase 3: Semantic indexing (indexing 70% -> 85%)
        _update_progress(0.0, stage="indexing", message="Saving transcript segments…")
        if segments:
            db.insert_transcripts(video_id, segments)

        if _is_cancelled():
            return _cleanup_cancelled()

        if segments:
            _update_progress(0.1, stage="indexing", message="Creating semantic chunks…")
            chunks = chunk_transcript(video_id, segments)

            def _on_index_prog(p: float) -> None:
                _update_progress(
                    p,
                    stage="indexing",
                    message="Indexing lecture vectors",
                )

            index_lecture_chunks(chunks, on_progress=_on_index_prog)

        if _is_cancelled():
            return _cleanup_cancelled()

        _update_progress(1.0, stage="indexing", message="Indexing complete")

        # Phase 4: Chapterisation, Notes, Quiz & Cards (generating_notes 85% -> 100%)
        _update_progress(
            0.0, stage="generating_notes", message="Generating topic chapters…"
        )
        chapters = generate_chapters(video_id, segments) if segments else []

        if _is_cancelled():
            return _cleanup_cancelled()

        _update_progress(
            0.30,
            stage="generating_notes",
            message="Generating study notes, quiz & flashcards…",
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_notes = executor.submit(generate_notes, video_id, segments, chapters)
            future_quiz = executor.submit(generate_quiz, video_id, segments, chapters)
            future_cards = executor.submit(
                generate_flashcards, video_id, segments, chapters
            )

            future_notes.result()
            quiz_questions = future_quiz.result() or []
            flashcards = future_cards.result() or []

        if _is_cancelled():
            return _cleanup_cancelled()

        _update_progress(1.0, stage="generating_notes", message="Finalizing lecture…")

        # Complete: Mark video ready
        playlist = file_storage.playlist_url(video_id)
        poster = file_storage.poster_url(video_id)
        db.update_video(
            video_id,
            status="ready",
            playlist=playlist,
            poster=poster,
        )
        redis_store.delete_transcode_progress(video_id)
        return {
            "playlist": playlist,
            "poster": poster,
            "segments_count": len(segments),
            "chapters_count": len(chapters),
            "quiz_count": len(quiz_questions),
            "flashcards_count": len(flashcards),
        }

    except Exception as exc:
        audio_wav.unlink(missing_ok=True)
        db.update_video(
            video_id,
            status="error",
            error=str(exc),
        )
        redis_store.delete_transcode_progress(video_id)
        raise exc
