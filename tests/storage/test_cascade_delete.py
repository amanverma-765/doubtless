"""Tests for complete cascading deletion of video and all associated artifacts."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import chromadb

from doubtless.domain import (
    Flashcard,
    QuizQuestion,
    TranscriptSegment,
    VideoChapter,
    VideoNotes,
)
from doubtless.storage import file_storage, redis_store
from doubtless.storage.cascade_delete import cascade_delete_video
from doubtless.storage.repositories import (
    chat_repo,
    study_repo,
    transcript_repo,
    video_repo,
)
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
        video_repo.create_video(vid, title="Cascade Test Video", filename=f"{vid}.mp4")
        chat_repo.add_message(vid, role="user", content="Test question")
        chat_repo.add_message(vid, role="assistant", content="Test answer")
        transcript_repo.insert_transcripts(
            vid,
            [TranscriptSegment(start=0.0, end=10.0, text="Test transcript segment.")],
        )
        study_repo.save_chapters(
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
        study_repo.save_video_notes(
            VideoNotes(video_id=vid, title="Notes", markdown="# Notes Content")
        )
        study_repo.save_video_quiz(
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
        study_repo.save_video_flashcards(
            vid,
            [Flashcard(id=1, front="F", back="B", category="Concept")],
        )

        # Verify rows exist before delete
        assert video_repo.get_video(vid) is not None
        assert len(chat_repo.get_messages(vid)) == 2
        assert len(study_repo.get_chapters(vid)) == 1
        assert study_repo.get_video_notes(vid) is not None
        assert len(study_repo.get_video_quiz(vid)) == 1
        assert len(study_repo.get_video_flashcards(vid)) == 1
        assert (
            len(transcript_repo.get_transcript_segments_window(vid, current_time=5.0))
            > 0
        )

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
        assert video_repo.get_video(vid) is None
        assert len(chat_repo.get_messages(vid)) == 0
        assert len(study_repo.get_chapters(vid)) == 0
        assert study_repo.get_video_notes(vid) is None
        assert len(study_repo.get_video_quiz(vid)) == 0
        assert len(study_repo.get_video_flashcards(vid)) == 0
        assert (
            len(transcript_repo.get_transcript_segments_window(vid, current_time=5.0))
            == 0
        )

        # 7. Verify Filesystem: source and HLS directory purged
        assert not source_file.exists()
        assert not hls_folder.exists()

        # 8. Verify ChromaDB: vector embeddings deleted
        assert col.get(where={"video_id": vid})["ids"] == []

        # 9. Verify Redis: progress data deleted and cancellation set
        mock_redis.delete.assert_called_with(f"transcode:prog:{vid}")
        mock_redis.set.assert_any_call(f"video:cancel:{vid}", "1", ex=3600)


def test_delete_video_files_handles_read_only_files(tmp_path: Path) -> None:
    """Verify delete_video_files cleans folders and files with restricted mode."""
    test_video_dir = tmp_path / "videos"
    test_hls_dir = tmp_path / "hls"
    test_video_dir.mkdir(parents=True, exist_ok=True)
    test_hls_dir.mkdir(parents=True, exist_ok=True)

    vid = "readonlyvid1"
    hls_folder = test_hls_dir / vid
    hls_folder.mkdir(parents=True, exist_ok=True)
    sub_folder = hls_folder / "subdir"
    sub_folder.mkdir(parents=True, exist_ok=True)

    child_file = sub_folder / "chunk.ts"
    child_file.write_text("dummy chunk data")
    seg_file = hls_folder / "seg0001.ts"
    seg_file.write_text("dummy segment data")

    # Restrict permissions on files and folders to trigger PermissionError on POSIX
    child_file.chmod(0o444)
    seg_file.chmod(0o444)
    sub_folder.chmod(0o555)
    hls_folder.chmod(0o555)

    src_file = test_video_dir / f"{vid}.mp4"
    src_file.write_text("dummy video")
    src_file.chmod(0o444)
    test_video_dir.chmod(0o555)

    try:
        with (
            patch.object(file_storage, "VIDEO_DIR", test_video_dir),
            patch.object(file_storage, "HLS_DIR", test_hls_dir),
        ):
            file_storage.delete_video_files(vid)

        assert not hls_folder.exists()
        assert not src_file.exists()
    finally:
        # Restore permissions so pytest tmp_path cleanup never fails
        for p in (test_video_dir, test_hls_dir, hls_folder, sub_folder):
            if p.exists():
                p.chmod(0o777)


def test_cascade_delete_resilient_to_filesystem_failure(
    temp_db: Path, tmp_path: Path
) -> None:
    """Verify cascade deletion completes DB/Redis cleanup on filesystem error."""
    vid = "fsexceptionvid"
    video_repo.create_video(vid, title="FS Failure Test", filename=f"{vid}.mp4")

    mock_redis = MagicMock()
    with (
        patch(
            "doubtless.storage.cascade_delete.file_storage.delete_video_files",
            side_effect=OSError("Disk error"),
        ),
        patch.object(redis_store, "_get_client", return_value=mock_redis),
        patch("doubtless.storage.cascade_delete.delete_lecture_vectors"),
    ):
        res = cascade_delete_video(vid)

    assert res["deleted"] is True
    assert res["fs_deleted"] is False
    assert video_repo.get_video(vid) is None
    mock_redis.delete.assert_called_with(f"transcode:prog:{vid}")


def test_clean_hls_dir(tmp_path: Path) -> None:
    """Verify that clean_hls_dir removes only the target video HLS folder."""
    test_hls_dir = tmp_path / "hls"
    test_hls_dir.mkdir(parents=True, exist_ok=True)

    vid1 = "vidone11"
    vid2 = "vidtwo22"

    hls1 = test_hls_dir / vid1
    hls1.mkdir()
    (hls1 / "playlist.m3u8").write_text("data1")

    hls2 = test_hls_dir / vid2
    hls2.mkdir()
    (hls2 / "playlist.m3u8").write_text("data2")

    with patch.object(file_storage, "HLS_DIR", test_hls_dir):
        file_storage.clean_hls_dir(vid1)

    assert not hls1.exists()
    assert hls2.exists()
    assert (hls2 / "playlist.m3u8").exists()
