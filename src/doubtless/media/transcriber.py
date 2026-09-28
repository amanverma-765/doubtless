"""Audio extraction and speech-to-text transcription via Groq Whisper API."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import logfire

from doubtless import config
from doubtless.domain import TranscriptSegment
from doubtless.media.probe import MediaError, has_audio_stream, probe_audio_duration

if TYPE_CHECKING:
    from groq import Groq

_logger = logging.getLogger(__name__)

# Domain cues without language name tokens to prevent repetition collapse
_HINGLISH_PROMPT = (
    "Video lecture on Physics, Chemistry, Mathematics, exam questions, formulas, "
    "equations, velocity, acceleration, reactions, solutions, and derivations."
)

_MAX_CHUNK_BYTES = 24 * 1024 * 1024  # 24 MB (under Groq's 25 MB limit)
_DEFAULT_CHUNK_DURATION = 600.0  # 10 minutes per chunk

_AAC_AUDIO_ARGS = [
    "-vn",
    "-acodec",
    "aac",
    "-b:a",
    "32k",
    "-ar",
    "16000",
    "-ac",
    "1",
]


def get_groq_client(api_key: str | None = None) -> Groq:
    """Instantiate Groq client using configured or provided API key."""
    from groq import Groq

    key = api_key or config.GROQ_API_KEY
    if not key:
        raise MediaError(
            "GROQ_API_KEY is not configured. Required for speech transcription."
        )
    return Groq(api_key=key, max_retries=3)


def extract_audio(
    video_path: Path,
    output_path: Path,
    has_audio: bool | None = None,
) -> bool:
    """Extract audio track as 16kHz mono AAC (default) or WAV."""
    audio_present = has_audio if has_audio is not None else has_audio_stream(video_path)
    if not audio_present:
        return False

    with logfire.span(
        "audio.extract", video_path=str(video_path), output_path=str(output_path)
    ):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        is_wav = output_path.suffix.lower() == ".wav"
        codec_args = (
            ["-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1"]
            if is_wav
            else _AAC_AUDIO_ARGS
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(video_path),
            *codec_args,
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            output_path.unlink(missing_ok=True)
            raise MediaError(f"FFmpeg audio extraction failed: {result.stderr.strip()}")

        return output_path.is_file() and output_path.stat().st_size > 0


def _filter_segment_text(raw_text: str) -> str | None:
    """Clean raw segment text and filter hallucinations or repetition collapse."""
    text = raw_text.strip()
    if not text:
        return None
    lower = text.lower().strip(".,?![]()")
    if not lower:
        return None
    if lower in ("hindi", "english", "urdu", "subtitles by", "captioning by"):
        return None
    words = text.split()
    if len(words) > 5 and len(set(words)) == 1:
        return None
    return text


def _slice_audio(
    audio_path: Path,
    start_sec: float,
    duration_sec: float,
    out_slice: Path,
) -> None:
    """Slice a time window from an audio file using FFmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-ss",
        f"{start_sec:.2f}",
        "-t",
        f"{duration_sec:.2f}",
        "-i",
        str(audio_path),
        "-c",
        "copy",
        str(out_slice),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    has_valid_slice = out_slice.is_file() and out_slice.stat().st_size > 0
    if result.returncode != 0 or not has_valid_slice:
        fallback_cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            f"{start_sec:.2f}",
            "-t",
            f"{duration_sec:.2f}",
            "-i",
            str(audio_path),
            *_AAC_AUDIO_ARGS,
            str(out_slice),
        ]
        fallback_res = subprocess.run(
            fallback_cmd, capture_output=True, text=True, check=False
        )
        if fallback_res.returncode != 0:
            out_slice.unlink(missing_ok=True)
            raise MediaError(
                f"FFmpeg audio slice failed: {fallback_res.stderr.strip()}"
            )


def _transcribe_file(
    client: Groq,
    file_path: Path,
    model: str,
    time_offset: float = 0.0,
) -> list[TranscriptSegment]:
    """Send an audio file to Groq Whisper API and parse verbose_json segments."""
    with open(file_path, "rb") as f:
        response = client.audio.transcriptions.create(
            file=(file_path.name, f),
            model=model,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
            temperature=0.0,
            prompt=_HINGLISH_PROMPT,
        )

    segments_data = getattr(response, "segments", None) or []
    results: list[TranscriptSegment] = []

    for seg in segments_data:
        raw_text = (
            seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
        )
        cleaned_text = _filter_segment_text(raw_text)
        if not cleaned_text:
            continue

        start_val = (
            seg.get("start", 0.0)
            if isinstance(seg, dict)
            else getattr(seg, "start", 0.0)
        )
        end_val = (
            seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0)
        )

        results.append(
            TranscriptSegment(
                start=round(float(start_val) + time_offset, 2),
                end=round(float(end_val) + time_offset, 2),
                text=cleaned_text,
            )
        )

    return results


def transcribe_audio(
    audio_path: Path,
    total_duration: float = 0.0,
    on_progress: Callable[[float], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[TranscriptSegment]:
    """Transcribe audio into timestamped segments via Groq Whisper API with chunking."""
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        return []

    model = config.GROQ_WHISPER_MODEL
    file_size = audio_path.stat().st_size

    with logfire.span(
        "whisper.transcribe",
        audio_path=str(audio_path),
        total_duration=total_duration,
        model=model,
        file_size=file_size,
    ) as span:
        client = get_groq_client()

        # Single request if within 24MB limit
        if file_size <= _MAX_CHUNK_BYTES:
            if should_stop and should_stop():
                return []
            segments = _transcribe_file(client, audio_path, model, time_offset=0.0)
            if on_progress:
                on_progress(1.0)
            span.set_attribute("segments_count", len(segments))
            return segments

        # Multi-chunk processing for large audio files (>24MB)
        duration = total_duration
        if duration <= 0.0:
            duration = probe_audio_duration(audio_path)

        if duration <= 0.0:
            segments = _transcribe_file(client, audio_path, model, time_offset=0.0)
            if on_progress:
                on_progress(1.0)
            span.set_attribute("segments_count", len(segments))
            return segments

        chunk_duration = _DEFAULT_CHUNK_DURATION
        total_chunks = max(1, int((duration + chunk_duration - 1) // chunk_duration))
        all_segments: list[TranscriptSegment] = []

        with tempfile.TemporaryDirectory(prefix="groq_whisper_") as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            for chunk_idx in range(total_chunks):
                if should_stop and should_stop():
                    break

                offset = chunk_idx * chunk_duration
                slice_duration = min(chunk_duration, duration - offset)
                if slice_duration <= 0:
                    break

                slice_file = tmp_dir / f"chunk_{chunk_idx:04d}{audio_path.suffix}"
                _slice_audio(audio_path, offset, slice_duration, slice_file)

                if not slice_file.is_file() or slice_file.stat().st_size == 0:
                    continue

                chunk_segs = _transcribe_file(
                    client, slice_file, model, time_offset=offset
                )
                all_segments.extend(chunk_segs)

                slice_file.unlink(missing_ok=True)

                if on_progress:
                    prog = min(1.0, (offset + slice_duration) / duration)
                    on_progress(prog)

        span.set_attribute("segments_count", len(all_segments))
        return all_segments
