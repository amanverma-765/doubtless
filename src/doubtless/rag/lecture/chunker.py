"""Semantic chunking of speech-to-text transcript segments."""

from doubtless.domain import LectureChunk, TranscriptSegment


def chunk_transcript(
    video_id: str,
    segments: list[TranscriptSegment],
    target_duration: float = 45.0,
    min_duration: float = 20.0,
) -> list[LectureChunk]:
    """Aggregate small speech segments into coherent 30-60s chunks with overlap."""
    if not segments:
        return []

    chunks: list[LectureChunk] = []
    current_segments: list[TranscriptSegment] = []

    for seg in segments:
        current_segments.append(seg)
        chunk_dur = current_segments[-1].end - current_segments[0].start

        if chunk_dur >= target_duration:
            text = " ".join(s.text for s in current_segments).strip()
            if text:
                chunks.append(
                    LectureChunk(
                        video_id=video_id,
                        start_time=current_segments[0].start,
                        end_time=current_segments[-1].end,
                        text=text,
                    )
                )
            # Keep the last segment for boundary overlap
            current_segments = current_segments[-1:]

    # Handle remaining segments
    if current_segments:
        text = " ".join(s.text for s in current_segments).strip()
        dur = current_segments[-1].end - current_segments[0].start
        if text and (dur >= min_duration or not chunks):
            chunks.append(
                LectureChunk(
                    video_id=video_id,
                    start_time=current_segments[0].start,
                    end_time=current_segments[-1].end,
                    text=text,
                )
            )
        elif text and chunks:
            # Append trailing short speech to the previous chunk
            prev = chunks[-1]
            chunks[-1] = LectureChunk(
                video_id=video_id,
                start_time=prev.start_time,
                end_time=current_segments[-1].end,
                text=f"{prev.text} {text}".strip(),
            )

    return chunks
