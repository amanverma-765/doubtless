"""Multi-stage video ingestion pipeline: transcoding, transcription, and indexing."""

import concurrent.futures
import contextlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import logfire

from doubtless.domain import (
    Flashcard,
    QuizQuestion,
    TranscriptSegment,
    VideoChapter,
)
from doubtless.media.probe import MediaProbe, probe_video
from doubtless.media.transcoder import extract_poster, transcode_with_progress
from doubtless.media.transcriber import extract_audio, transcribe_audio
from doubtless.rag.lecture.chunker import chunk_transcript
from doubtless.rag.lecture.indexer import index_lecture_chunks
from doubtless.storage import file_storage, redis_store
from doubtless.storage.cascade_delete import cascade_delete_video
from doubtless.storage.repositories import study_repo, transcript_repo, video_repo
from doubtless.study.generator import (
    generate_chapters,
    generate_flashcards,
    generate_notes,
    generate_quiz,
)

_logger = logging.getLogger(__name__)

STAGE_PROGRESS_RANGES: dict[str, tuple[float, float]] = {
    "transcoding": (0.00, 0.25),
    "transcribing": (0.25, 0.70),
    "indexing": (0.70, 0.85),
    "generating_notes": (0.85, 1.00),
}


class PipelineCancelledError(Exception):
    """Raised when the active pipeline task has been marked cancelled."""

    pass


def calc_overall_progress(stage: str, stage_progress: float) -> float:
    """Map local stage progress monotonically into overall pipeline progress."""
    start, end = STAGE_PROGRESS_RANGES.get(stage, (0.0, 1.0))
    clamped = min(1.0, max(0.0, stage_progress))
    return round(start + clamped * (end - start), 4)


class PipelineRunner:
    """Encapsulates video processing lifecycle across all media and AI stages."""

    def __init__(
        self,
        video_id: str,
        src_path: Path,
        progress_callback: Callable[[float, str, float, str], None] | None = None,
    ) -> None:
        self.video_id = video_id
        self.src_path = src_path
        self.progress_callback = progress_callback
        self.out_dir = file_storage.hls_dir(video_id)
        self.audio_wav = self.out_dir / "audio.wav"

    def is_cancelled(self) -> bool:
        """Evaluate if video has been cancelled via Redis or deleted from SQLite."""
        return (
            redis_store.is_cancelled(self.video_id)
            or video_repo.get_video(self.video_id) is None
        )

    def check_cancelled(self) -> None:
        """Raise PipelineCancelledError if cancellation condition is met."""
        if self.is_cancelled():
            raise PipelineCancelledError(
                f"Video {self.video_id} processing was cancelled."
            )

    def update_progress(
        self,
        stage: str,
        stage_progress: float,
        message: str = "",
    ) -> None:
        """Update Redis and invoke progress callback with monotonic overall progress."""
        self.check_cancelled()
        p = min(1.0, max(0.0, stage_progress))
        overall = calc_overall_progress(stage, p)
        redis_store.set_transcode_progress(
            self.video_id, overall, stage=stage, message=message
        )
        if self.progress_callback:
            self.progress_callback(overall, stage, p, message)

    def _phase_transcode(self, media_info: MediaProbe) -> None:
        """Extract poster thumbnail and execute HLS video transcoding."""
        self.update_progress("transcoding", 0.0, "Preparing video transcoding…")
        with logfire.span("pipeline.transcode_hls", video_id=self.video_id):
            extract_poster(self.src_path, self.out_dir / "poster.jpg")

            def _on_hls_prog(p: float) -> None:
                self.update_progress("transcoding", p, "Transcoding video (HLS)")

            transcode_with_progress(
                self.src_path,
                self.out_dir,
                on_progress=_on_hls_prog,
                should_stop=self.is_cancelled,
                info=media_info,
            )

        self.check_cancelled()
        self.update_progress("transcoding", 1.0, "Transcoding complete")

    def _phase_transcribe(self, media_info: MediaProbe) -> list[TranscriptSegment]:
        """Extract 16kHz mono audio and run Whisper speech-to-text."""
        self.update_progress("transcribing", 0.0, "Extracting audio track…")
        segments: list[TranscriptSegment] = []

        with logfire.span("pipeline.transcribe", video_id=self.video_id):
            has_audio = extract_audio(
                self.src_path,
                self.audio_wav,
                has_audio=media_info.acodec is not None,
            )
            self.check_cancelled()

            if has_audio and self.audio_wav.is_file():
                duration = media_info.duration

                def _on_whisper_prog(p: float) -> None:
                    self.update_progress(
                        "transcribing",
                        p,
                        "Transcribing speech with AI (GPU)",
                    )

                segments = transcribe_audio(
                    self.audio_wav,
                    total_duration=duration,
                    on_progress=_on_whisper_prog,
                    should_stop=self.is_cancelled,
                )
                self.audio_wav.unlink(missing_ok=True)

        self.update_progress("transcribing", 1.0, "Transcription complete")
        return segments

    def _phase_indexing(self, segments: list[TranscriptSegment]) -> None:
        """Store raw transcript in database, chunk dialogue, and index into ChromaDB."""
        self.update_progress("indexing", 0.0, "Saving transcript segments…")
        with logfire.span(
            "pipeline.index_chunks",
            video_id=self.video_id,
            segment_count=len(segments),
        ):
            if segments:
                transcript_repo.insert_transcripts(self.video_id, segments)

            self.check_cancelled()

            if segments:
                self.update_progress("indexing", 0.1, "Creating semantic chunks…")
                chunks = chunk_transcript(self.video_id, segments)

                def _on_index_prog(p: float) -> None:
                    self.update_progress("indexing", p, "Indexing lecture vectors")

                index_lecture_chunks(chunks, on_progress=_on_index_prog)

        self.update_progress("indexing", 1.0, "Indexing complete")

    def _phase_study_generation(
        self,
        segments: list[TranscriptSegment],
    ) -> tuple[list[VideoChapter], list[QuizQuestion], list[Flashcard]]:
        """Generate topic chapters, study notes, quiz questions, and flashcards."""
        self.update_progress("generating_notes", 0.0, "Generating topic chapters…")
        with logfire.span("pipeline.study_generation", video_id=self.video_id):
            chapters = generate_chapters(segments) if segments else []
            if chapters:
                study_repo.save_chapters(self.video_id, chapters)

            self.check_cancelled()

            self.update_progress(
                "generating_notes",
                0.30,
                "Generating study notes, quiz & flashcards…",
            )

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_notes = executor.submit(
                    generate_notes, self.video_id, segments, chapters
                )
                future_quiz = executor.submit(generate_quiz, segments, chapters)
                future_cards = executor.submit(generate_flashcards, segments, chapters)

                notes = future_notes.result()
                study_repo.save_video_notes(notes)
                quiz_questions = future_quiz.result() or []
                study_repo.save_video_quiz(self.video_id, quiz_questions)
                flashcards = future_cards.result() or []
                study_repo.save_video_flashcards(self.video_id, flashcards)

        self.update_progress("generating_notes", 1.0, "Finalizing lecture…")
        return chapters, quiz_questions, flashcards

    def _cleanup_cancelled(self) -> dict[str, Any]:
        """Tear down partial filesystem and database state on cancelled task."""
        self.audio_wav.unlink(missing_ok=True)
        cascade_delete_video(self.video_id)
        redis_store.clear_cancellation(self.video_id)
        return {"cancelled": True}

    def run(self) -> dict[str, Any]:
        """Execute the complete multi-stage pipeline."""
        if not self.src_path.is_file():
            _logger.info(
                "Source file %s no longer exists on disk (video deleted/cancelled). "
                "Skipping task for video %s.",
                self.src_path,
                self.video_id,
            )
            return {"cancelled": True}

        file_storage.clean_hls_dir(self.video_id)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            self.out_dir.chmod(0o777)

        try:
            with logfire.span(
                "pipeline.process_video", video_id=self.video_id, src=str(self.src_path)
            ):
                with logfire.span("pipeline.probe", video_id=self.video_id):
                    media_info = probe_video(self.src_path)

                self._phase_transcode(media_info)
                segments = self._phase_transcribe(media_info)
                self._phase_indexing(segments)
                chapters, quiz_questions, flashcards = self._phase_study_generation(
                    segments
                )

                playlist = file_storage.playlist_url(self.video_id)
                poster = file_storage.poster_url(self.video_id)
                video_repo.update_video(
                    self.video_id,
                    status="ready",
                    playlist=playlist,
                    poster=poster,
                )
                redis_store.delete_transcode_progress(self.video_id)

                return {
                    "playlist": playlist,
                    "poster": poster,
                    "segments_count": len(segments),
                    "chapters_count": len(chapters),
                    "quiz_count": len(quiz_questions),
                    "flashcards_count": len(flashcards),
                }

        except PipelineCancelledError:
            return self._cleanup_cancelled()

        except Exception as exc:
            logfire.exception(
                "Video processing failed: {error}",
                error=str(exc),
                video_id=self.video_id,
            )
            self.audio_wav.unlink(missing_ok=True)
            video_repo.update_video(
                self.video_id,
                status="error",
                error=str(exc),
            )
            redis_store.delete_transcode_progress(self.video_id)
            raise exc
