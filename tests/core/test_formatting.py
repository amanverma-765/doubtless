"""Unit tests for time and presentation formatting utilities."""

from doubtless.core.formatting import format_timestamp


def test_format_timestamp_zero() -> None:
    assert format_timestamp(0.0) == "00:00"


def test_format_timestamp_seconds_only() -> None:
    assert format_timestamp(45.0) == "00:45"
    assert format_timestamp(59.9) == "00:59"


def test_format_timestamp_minutes() -> None:
    assert format_timestamp(60.0) == "01:00"
    assert format_timestamp(75.5) == "01:15"
    assert format_timestamp(3599.0) == "59:59"


def test_format_timestamp_hours() -> None:
    assert format_timestamp(3600.0) == "01:00:00"
    assert format_timestamp(3665.0) == "01:01:05"
    assert format_timestamp(7322.0) == "02:02:02"


def test_format_timestamp_negative_clamp() -> None:
    assert format_timestamp(-10.0) == "00:00"
