"""Speech transcription segments persistence and window retrieval."""

from doubtless.domain import TranscriptSegment
from doubtless.storage.connection import get_db


def insert_transcripts(video_id: str, segments: list[TranscriptSegment]) -> None:
    """Batch insert timestamped transcription segments for a video."""
    if not segments:
        return
    rows = [(video_id, seg.start, seg.end, seg.text) for seg in segments]
    with get_db() as conn:
        conn.executemany(
            """
            INSERT INTO lecture_transcripts (video_id, start_time, end_time, text)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )


def get_transcript_segments_window(
    video_id: str,
    current_time: float,
    window_before: float = 60.0,
    window_after: float = 15.0,
) -> list[TranscriptSegment]:
    """Retrieve spoken dialogue segments within the local timestamp window."""
    start_bound = max(0.0, current_time - window_before)
    end_bound = current_time + window_after

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT start_time, end_time, text FROM lecture_transcripts
            WHERE video_id = ? AND end_time >= ? AND start_time <= ?
            ORDER BY start_time ASC
            """,
            (video_id, start_bound, end_bound),
        ).fetchall()

    return [
        TranscriptSegment(
            start=float(r["start_time"]),
            end=float(r["end_time"]),
            text=str(r["text"]),
        )
        for r in rows
    ]
