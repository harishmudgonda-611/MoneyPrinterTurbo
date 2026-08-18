"""Deterministic post-render QA for generated vertical Reels."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from app.utils import utils


class RenderQAError(RuntimeError):
    pass


def _probe(path: str) -> dict:
    command = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RenderQAError(result.stderr.strip() or "ffprobe failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RenderQAError("Invalid ffprobe response") from exc


def _visual_integrity(path: str, max_black_seconds: float, max_freeze_seconds: float) -> dict:
    """Detect long black/frozen stretches without decoding the entire video in Python."""
    command = [
        utils.get_ffmpeg_binary(),
        "-hide_banner",
        "-i", path,
        "-vf", "blackdetect=d=0.5:pix_th=0.10,freezedetect=n=-60dB:d=1.5",
        "-an",
        "-f", "null",
        "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode not in {0, 1}:
        raise RenderQAError(result.stderr.strip() or "Visual integrity check failed")

    black_durations = []
    freeze_durations = []
    for match in re.finditer(
        r"black_start:([0-9.]+).*?black_end:([0-9.]+).*?black_duration:([0-9.]+)",
        result.stderr or "",
        re.DOTALL,
    ):
        black_durations.append(float(match.group(3)))
    for match in re.finditer(
        r"freeze_start:([0-9.]+).*?freeze_end:([0-9.]+)",
        result.stderr or "",
        re.DOTALL,
    ):
        freeze_durations.append(max(0.0, float(match.group(2)) - float(match.group(1))))

    longest_black = max(black_durations, default=0.0)
    longest_freeze = max(freeze_durations, default=0.0)
    if longest_black > max_black_seconds:
        raise RenderQAError(f"Excessive black frame duration: {longest_black:.2f}s")
    if longest_freeze > max_freeze_seconds:
        raise RenderQAError(f"Excessive frozen frame duration: {longest_freeze:.2f}s")

    return {
        "longest_black_seconds": longest_black,
        "longest_freeze_seconds": longest_freeze,
    }


def validate_render(
    path: str,
    expected_duration: float | None = None,
    max_black_seconds: float = 1.0,
    max_freeze_seconds: float = 2.0,
) -> dict:
    """Validate a finished Reel before exposing it as a successful result."""
    file_path = Path(path)
    if not file_path.is_file() or file_path.stat().st_size == 0:
        raise RenderQAError("Rendered MP4 is missing or empty")

    metadata = _probe(str(file_path))
    streams = metadata.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video:
        raise RenderQAError("Rendered file has no video stream")
    if not audio:
        raise RenderQAError("Rendered file has no audio stream")

    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    if (width, height) != (1080, 1920):
        raise RenderQAError(f"Expected 1080x1920, got {width}x{height}")

    duration = float(metadata.get("format", {}).get("duration") or video.get("duration") or 0)
    if duration <= 0:
        raise RenderQAError("Rendered video has invalid duration")
    if expected_duration is not None and abs(duration - expected_duration) > 1.5:
        raise RenderQAError(
            f"Duration mismatch: expected about {expected_duration:.2f}s, got {duration:.2f}s"
        )

    audio_duration = float(audio.get("duration") or 0)
    if audio_duration and abs(audio_duration - duration) > 2.0:
        raise RenderQAError("Audio/video duration mismatch")

    fps = video.get("avg_frame_rate", "")
    if fps in {"0/0", ""}:
        raise RenderQAError("Invalid video frame rate")

    visual = _visual_integrity(str(file_path), max_black_seconds, max_freeze_seconds)
    return {
        "passed": True,
        "path": str(file_path),
        "size_bytes": file_path.stat().st_size,
        "width": width,
        "height": height,
        "aspect_ratio": "9:16",
        "duration_seconds": duration,
        "audio_duration_seconds": audio_duration,
        "fps": fps,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        **visual,
    }
