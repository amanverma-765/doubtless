"""Unit tests for the multi-stage ingestion PipelineRunner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from doubtless.media.pipeline import (
    PipelineRunner,
    calc_overall_progress,
)
from doubtless.storage.repositories import video_repo


def test_calc_overall_progress_bounds() -> None:
    """Stage progress is mapped within designated stage bounds."""
    assert calc_overall_progress("transcoding", 0.0) == 0.0
    assert calc_overall_progress("transcoding", 1.0) == 0.25
    assert calc_overall_progress("transcribing", 0.0) == 0.25
    assert calc_overall_progress("transcribing", 1.0) == 0.70
    assert calc_overall_progress("indexing", 1.0) == 0.85
    assert calc_overall_progress("generating_notes", 1.0) == 1.0


def test_pipeline_missing_source_file(tmp_path: Path) -> None:
    """Missing source file cleanly returns cancelled without running pipeline."""
    runner = PipelineRunner("missing_vid", tmp_path / "nonexistent.mp4")
    res = runner.run()
    assert res == {"cancelled": True}


def test_pipeline_cancelled_abort(tmp_path: Path) -> None:
    """Cancellation flag aborts execution and triggers cascade deletion cleanup."""
    fake_src = tmp_path / "test.mp4"
    fake_src.write_bytes(b"dummy video content")

    runner = PipelineRunner("cancel_vid", fake_src)

    with (
        patch.object(runner, "is_cancelled", side_effect=[False, True]),
        patch("doubtless.media.pipeline.probe_video"),
        patch("doubtless.media.pipeline.extract_poster"),
        patch("doubtless.media.pipeline.transcode_with_progress"),
        patch("doubtless.media.pipeline.cascade_delete_video") as mock_cascade,
        patch("doubtless.media.pipeline.redis_store"),
    ):
        res = runner.run()
        assert res == {"cancelled": True}
        mock_cascade.assert_called_once_with("cancel_vid")


def test_pipeline_progress_callback(tmp_path: Path) -> None:
    """update_progress invokes progress callback and redis."""
    fake_src = tmp_path / "test.mp4"
    callback_calls: list[tuple[float, str, float, str]] = []

    def _cb(overall: float, stage: str, stage_progress: float, msg: str) -> None:
        callback_calls.append((overall, stage, stage_progress, msg))

    runner = PipelineRunner("prog_vid", fake_src, progress_callback=_cb)

    with (
        patch.object(runner, "is_cancelled", return_value=False),
        patch(
            "doubtless.media.pipeline.redis_store.set_transcode_progress"
        ) as mock_redis,
    ):
        runner.update_progress("transcoding", 0.5, "Halfway transcoding")
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 0.125
        assert callback_calls[0][1] == "transcoding"
        assert callback_calls[0][2] == 0.5
        assert callback_calls[0][3] == "Halfway transcoding"
        mock_redis.assert_called_once()


def test_pipeline_run_success_flow(tmp_path: Path) -> None:
    """Successful pipeline run executes all phases and marks video ready."""
    video_repo.create_video("success_vid", "Success Lecture", "success.mp4")
    fake_src = tmp_path / "lecture.mp4"
    fake_src.write_bytes(b"video bytes")

    runner = PipelineRunner("success_vid", fake_src)
    mock_probe = MagicMock()
    mock_probe.duration = 100.0
    mock_probe.acodec = "aac"

    with (
        patch.object(runner, "is_cancelled", return_value=False),
        patch("doubtless.media.pipeline.probe_video", return_value=mock_probe),
        patch("doubtless.media.pipeline.extract_poster"),
        patch("doubtless.media.pipeline.transcode_with_progress"),
        patch("doubtless.media.pipeline.extract_audio", return_value=False),
        patch("doubtless.media.pipeline.video_repo.update_video") as mock_update,
        patch("doubtless.media.pipeline.redis_store"),
    ):
        result = runner.run()
        assert "playlist" in result
        assert "poster" in result
        assert result["segments_count"] == 0
        mock_update.assert_called_once()
        assert mock_update.call_args[1]["status"] == "ready"


def test_pipeline_error_handling(tmp_path: Path) -> None:
    """Unhandled exception marks video status as error and re-raises."""
    fake_src = tmp_path / "bad.mp4"
    fake_src.write_bytes(b"bad bytes")

    runner = PipelineRunner("err_vid", fake_src)

    with (
        patch.object(runner, "is_cancelled", return_value=False),
        patch(
            "doubtless.media.pipeline.probe_video",
            side_effect=ValueError("Corrupted file"),
        ),
        patch("doubtless.media.pipeline.video_repo.update_video") as mock_update,
        patch("doubtless.media.pipeline.redis_store"),
    ):
        with pytest.raises(ValueError, match="Corrupted file"):
            runner.run()

        mock_update.assert_called_once()
        assert mock_update.call_args[1]["status"] == "error"
        assert "Corrupted file" in mock_update.call_args[1]["error"]
