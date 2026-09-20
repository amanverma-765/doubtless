"""Audio extraction and speech-to-text transcription via faster-whisper."""

import contextlib
import gc
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import torch

from doubtless.domain.schemas import TranscriptSegment
from doubtless.media.probe import MediaError, has_audio_stream

_logger = logging.getLogger(__name__)

_WHISPER_MODEL_SIZE = "medium"
_HINGLISH_PROMPT = (
    "Yeh ek educational video lecture hai on Physics, Chemistry, Mathematics, "
    "and exam preparation. Hindi aur English dono bhashayein use hoti hain with "
    "technical terms like velocity, acceleration, formula, equation, roadmap, strategy."
)

_whisper_model_cache: dict[tuple[str, str], Any] = {}


def load_whisper_model(device: str = "cpu", compute_type: str = "int8") -> Any:
    """Retrieve or load a cached WhisperModel for the device and precision."""
    key = (device, compute_type)
    if key in _whisper_model_cache:
        return _whisper_model_cache[key]

    from faster_whisper import WhisperModel  # type: ignore[import-untyped]

    model = WhisperModel(
        _WHISPER_MODEL_SIZE,
        device=device,
        compute_type=compute_type,
    )
    _whisper_model_cache[key] = model
    return model


def extract_audio(video_path: Path, output_wav: Path) -> bool:
    """Extract audio track as 16kHz mono 16-bit PCM WAV.

    Returns True if audio extracted successfully, False if no audio stream exists.
    """
    if not has_audio_stream(video_path):
        return False

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_wav),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        output_wav.unlink(missing_ok=True)
        raise MediaError(f"FFmpeg audio extraction failed: {result.stderr.strip()}")

    return output_wav.is_file() and output_wav.stat().st_size > 0


def _run_transcription(
    model: Any,
    audio_path: Path,
    total_duration: float,
    on_progress: Callable[[float], None] | None,
    should_stop: Callable[[], bool] | None,
) -> list[TranscriptSegment]:
    """Execute transcription with BatchedInferencePipeline and collect segments."""
    vad_params = {"min_silence_duration_ms": 500}
    segments_gen: Any = None
    info: Any = None

    try:
        from faster_whisper import (
            BatchedInferencePipeline,
        )

        batched_model = BatchedInferencePipeline(model=model)
        segments_gen, info = batched_model.transcribe(
            str(audio_path),
            batch_size=16,
            beam_size=1,
            initial_prompt=_HINGLISH_PROMPT,
            vad_filter=True,
            vad_parameters=vad_params,
        )
    except Exception as exc:
        _logger.warning(
            "Batched transcription failed: %s. Using standard transcription.",
            exc,
        )
        segments_gen, info = model.transcribe(
            str(audio_path),
            initial_prompt=_HINGLISH_PROMPT,
            beam_size=1,
            vad_filter=True,
            vad_parameters=vad_params,
        )

    results: list[TranscriptSegment] = []
    duration = total_duration or (info.duration if info else 0.0)

    for seg in segments_gen:
        if should_stop and should_stop():
            break

        text = seg.text.strip()
        if text:
            results.append(
                TranscriptSegment(
                    start=round(float(seg.start), 2),
                    end=round(float(seg.end), 2),
                    text=text,
                )
            )

        if on_progress and duration > 0:
            prog = min(1.0, max(0.0, float(seg.end) / duration))
            on_progress(prog)

    return results


def transcribe_audio(
    audio_path: Path,
    total_duration: float = 0.0,
    on_progress: Callable[[float], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[TranscriptSegment]:
    """Transcribe audio file into timestamped segments with GPU fallback and caching."""
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        return []

    use_cuda = torch.cuda.is_available()

    if use_cuda:
        try:
            _logger.info("Initializing faster-whisper on CUDA (int8_float16)...")
            gpu_model = load_whisper_model(device="cuda", compute_type="int8_float16")
            return _run_transcription(
                gpu_model,
                audio_path,
                total_duration,
                on_progress,
                should_stop,
            )
        except Exception as exc:
            _logger.warning(
                "CUDA transcription encountered error: %s. Falling back to CPU.",
                exc,
                exc_info=True,
            )
            _whisper_model_cache.pop(("cuda", "int8_float16"), None)
            gc.collect()
            with contextlib.suppress(Exception):
                torch.cuda.empty_cache()

    _logger.info("Running faster-whisper on CPU (int8)...")
    cpu_model = load_whisper_model(device="cpu", compute_type="int8")
    return _run_transcription(
        cpu_model,
        audio_path,
        total_duration,
        on_progress,
        should_stop,
    )
