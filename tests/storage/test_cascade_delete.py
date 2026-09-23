"""Tests for complete cascading deletion of video and all associated artifacts."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import chromadb

from doubtless.domain.schemas import (
    Flashcard,
    QuizQuestion,
    TranscriptSegment,
    VideoChapter,
    VideoNotes,
)
from doubtless.storage import db, file_storage, redis_store
from doubtless.storage.cascade_delete import cascade_delete_video
from doubtless.storage.vector_store import get_lectures_collection


def test_cascade_delete_purges_all_layers(temp_db: Path, tmp_path: Path) -> None:
    """Verify that deleting a video cleans files, SQLite, Redis, and ChromaDB."""
    vid = "cascadetest1"

    test_video_dir = tmp_path / "videos"
    test_hls_dir = tmp_path / "hls"
    test_video_dir.mkdir(parents=True, exist_ok=True)
    test_hls_dir.mkdir(parents=True, exist_ok=True)

    test_chroma = chromadb.EphemeralClient()
    mock_redis = MagicMock()

    with (
        patch.object(file_storage, "VIDEO_DIR", test_video_dir),
        patch.object(file_storage, "HLS_DIR", test_hls_dir),
        patch(
            "doubtless.storage.vector_store.get_chroma_client",
            return_value=test_chroma,
        ),
        patch.object(redis_store, "_get_client", return_value=mock_redis),
    ):
        # 1. Create DB records across all 7 tables
        db.create_video(vid, title="Cascade Test Video", filename=f"{vid}.mp4")
        db.add_message(vid, role="user", content="Test question")
        db.add_message(vid, role="assistant", content="Test answer")
        db.insert_transcripts(
            vid,
            [TranscriptSegment(start=0.0, end=10.0, text="Test transcript segment.")],
        )
        db.save_chapters(
            vid,
            [
                VideoChapter(
                    start_time=0.0,
                    end_time=10.0,
                    title="Ch1",
                    description="Desc1",
                )
            ],
        )
        db.save_video_notes(
            VideoNotes(video_id=vid, title="Notes", markdown="# Notes Content")
        )
        db.save_video_quiz(
            vid,
            [
                QuizQuestion(
                    id=1,
                    question="Q?",
                    options=["A", "B", "C", "D"],
                    correct_index=0,
                    explanation="E",
                )
            ],
        )
        db.save_video_flashcards(
            vid,
            [Flashcard(id=1, front="F", back="B", category="Concept")],
        )

        # Verify rows exist before delete
        assert db.get_video(vid) is not None
        assert len(db.get_messages(vid)) == 2
        assert len(db.get_chapters(vid)) == 1
        assert db.get_video_notes(vid) is not None
        assert len(db.get_video_quiz(vid)) == 1
        assert len(db.get_video_flashcards(vid)) == 1
        assert db.get_transcript_dialogue_window(vid, current_time=5.0) != ""

        # 2. Create dummy filesystem artifacts
        source_file = file_storage.VIDEO_DIR / f"{vid}.mp4"
        source_file.write_text("dummy video bytes")
        hls_folder = file_storage.hls_dir(vid)
        hls_folder.mkdir(parents=True, exist_ok=True)
        (hls_folder / "index.m3u8").write_text("playlist")
        (hls_folder / "audio.wav").write_text("audio")
        (hls_folder / "poster.jpg").write_text("poster")
        (hls_folder / "seg0000.ts").write_text("segment")

        assert source_file.exists()
        assert hls_folder.exists()

        # 3. Create dummy ChromaDB vectors
        col = get_lectures_collection()
        col.add(
            ids=[f"{vid}_chunk_0"],
            documents=["Test chunk for cascade delete"],
            metadatas=[{"video_id": vid, "start_time": 0.0, "end_time": 10.0}],
            embeddings=[[0.05] * 1024],
        )
        assert col.get(where={"video_id": vid})["ids"] == [f"{vid}_chunk_0"]

        # 4. Create Redis progress data
        redis_store.set_transcode_progress(
            vid, 0.5, stage="transcoding", message="Test"
        )

        # 5. Execute cascading deletion
        result = cascade_delete_video(vid)
        assert result["deleted"] is True
        assert result["video_id"] == vid

        # 6. Verify SQLite: all 7 tables return 0 rows for vid
        assert db.get_video(vid) is None
        assert len(db.get_messages(vid)) == 0
        assert len(db.get_chapters(vid)) == 0
        assert db.get_video_notes(vid) is None
        assert len(db.get_video_quiz(vid)) == 0
        assert len(db.get_video_flashcards(vid)) == 0
        assert db.get_transcript_dialogue_window(vid, current_time=5.0) == ""

        # 7. Verify Filesystem: source and HLS directory purged
        assert not source_file.exists()
        assert not hls_folder.exists()

        # 8. Verify ChromaDB: vector embeddings deleted
        assert col.get(where={"video_id": vid})["ids"] == []

        # 9. Verify Redis: progress data deleted and cancellation set
        mock_redis.delete.assert_called_with(f"transcode:prog:{vid}")
        mock_redis.set.assert_any_call(f"video:cancel:{vid}", "1", ex=3600)
