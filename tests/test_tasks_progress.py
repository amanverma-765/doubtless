"""Unit tests for pipeline progress monotonicity and calculations."""

from doubtless.worker.tasks import STAGE_PROGRESS_RANGES, calc_overall_progress


def test_calc_overall_progress_monotonicity() -> None:
    """Verify overall progress increases monotonically across pipeline stages."""
    stages = ["transcoding", "transcribing", "indexing", "generating_notes"]

    last_val = 0.0
    for stage in stages:
        start_bound, end_bound = STAGE_PROGRESS_RANGES[stage]
        # At start of stage (0%)
        val_0 = calc_overall_progress(stage, 0.0)
        assert val_0 >= last_val
        assert val_0 == start_bound

        # At mid stage (50%)
        val_50 = calc_overall_progress(stage, 0.5)
        assert val_50 > val_0
        assert val_50 < end_bound

        # At stage completion (100%)
        val_100 = calc_overall_progress(stage, 1.0)
        assert val_100 == end_bound
        assert val_100 >= val_50

        last_val = val_100

    assert last_val == 1.0


def test_calc_overall_progress_clamping() -> None:
    """Verify stage_progress below 0.0 or above 1.0 is safely clamped."""
    assert calc_overall_progress("transcoding", -0.5) == 0.0
    assert calc_overall_progress("generating_notes", 1.5) == 1.0
