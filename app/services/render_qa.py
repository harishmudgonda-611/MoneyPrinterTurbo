"""Deterministic post-render QA for generated vertical Reels."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


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


def validate_render(path: str, expected_duration: float | None = None) -> dict:
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
    }
