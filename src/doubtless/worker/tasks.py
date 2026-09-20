"""Asynchronous Celery tasks for media transcoding, transcription, and indexing."""

import concurrent.futures
import contextlib
import shutil
from pathlib import Path
from typing import Any

from doubtless.media.probe import probe_video
from doubtless.media.transcoder import extract_poster, transcode_with_progress
from doubtless.media.transcriber import extract_audio, transcribe_audio
from doubtless.rag.lecture.chunker import chunk_transcript
from doubtless.rag.lecture.indexer import index_lecture_chunks
from doubtless.storage import db, file_storage, redis_store
from doubtless.storage.vector_store import delete_lecture_vectors
from doubtless.study.chapteriser import generate_chapters
from doubtless.study.flashcards import generate_flashcards
from doubtless.study.notes import generate_notes
from doubtless.study.quiz import generate_quiz
from doubtless.worker.celery_app import celery_app


@celery_app.task(bind=True)
def transcode_video(
    self: Any,
    video_id: str,
    src: str,
) -> dict[str, Any]:
    """Execute HLS transcoding, audio transcription, and vector indexing."""
    src_path = Path(src)
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
        clamped = min(1.0, max(0.0, p))
        self.update_state(
            state="PROGRESS",
            meta={"progress": clamped, "stage": stage, "message": message},
        )
        redis_store.set_transcode_progress(
            video_id, clamped, stage=stage, message=message
        )

    def _cleanup_cancelled() -> dict[str, Any]:
        audio_wav.unlink(missing_ok=True)
        shutil.rmtree(out, ignore_errors=True)
        delete_lecture_vectors(video_id)
        db.delete_video(video_id)
        redis_store.delete_transcode_progress(video_id)
        redis_store.clear_cancellation(video_id)
        return {"cancelled": True}

    try:
        # Phase 1: Poster extraction & HLS transcoding (transcoding 0% -> 100%)
        _update_progress(
            0.0, stage="transcoding", message="Preparing video transcoding…"
        )
        extract_poster(src_path, out / "poster.jpg")

        def _on_hls_prog(p: float) -> None:
            _update_progress(
                p,
                stage="transcoding",
                message=f"Transcoding video {int(p * 100)}%",
            )

        transcode_with_progress(
            src_path,
            out,
            on_progress=_on_hls_prog,
            should_stop=_is_cancelled,
        )

        if _is_cancelled():
            return _cleanup_cancelled()

        _update_progress(1.0, stage="transcoding", message="Transcoding complete 100%")

        # Phase 2: Audio extraction & Whisper transcription (transcribing 0% -> 100%)
        _update_progress(0.0, stage="transcribing", message="Extracting audio track…")
        has_audio = extract_audio(src_path, audio_wav)

        if _is_cancelled():
            return _cleanup_cancelled()

        segments = []
        if has_audio and audio_wav.is_file():
            duration = 0.0
            with contextlib.suppress(Exception):
                duration = probe_video(src_path).duration

            def _on_whisper_prog(p: float) -> None:
                _update_progress(
                    p,
                    stage="transcribing",
                    message=f"Transcribing speech with AI {int(p * 100)}%",
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

        _update_progress(
            1.0, stage="transcribing", message="Transcription complete 100%"
        )

        # Phase 3: Semantic indexing (indexing 0% -> 100%)
        _update_progress(0.0, stage="indexing", message="Saving transcript segments…")
        if segments:
            db.insert_transcripts(video_id, segments)

        if _is_cancelled():
            return _cleanup_cancelled()

        if segments:
            _update_progress(0.3, stage="indexing", message="Creating semantic chunks…")
            chunks = chunk_transcript(video_id, segments)
            _update_progress(
                0.6,
                stage="indexing",
                message="Embedding & indexing lecture vectors…",
            )
            index_lecture_chunks(chunks)

        if _is_cancelled():
            return _cleanup_cancelled()

        _update_progress(1.0, stage="indexing", message="Indexing complete 100%")

        # Phase 4: Chapterisation, Notes, Quiz & Cards (0% -> 100%)
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
