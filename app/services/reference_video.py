"""Local reference-video inspection without sending the source video anywhere."""

import json
import re
import subprocess
from pathlib import Path

from app.models.reference_video import ReferenceVideoAnalysis
from app.utils import utils

_SCENE_THRESHOLD = 0.35
_MAX_ANALYSIS_SECONDS = 180


def _run_ffprobe(video_path: str) -> dict:
    command = [
        utils.get_ffmpeg_binary().replace("ffmpeg", "ffprobe"),
        "-v", "error",
        "-show_entries", "format=duration:stream=index,codec_type,width,height,r_frame_rate,avg_frame_rate",
        "-of", "json",
        video_path,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise ValueError("Unable to inspect the reference video") from exc
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Reference video metadata is invalid") from exc


def _fps(value: str | None) -> float:
    if not value or value in {"0/0", "N/A"}:
        return 0.0
    try:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator) if float(denominator) else 0.0
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _detect_cuts(video_path: str, duration: float) -> list[float]:
    if duration <= 0:
        return []
    command = [
        utils.get_ffmpeg_binary(), "-hide_banner", "-i", video_path,
        "-vf", f"select='gt(scene,{_SCENE_THRESHOLD})',showinfo",
        "-an", "-f", "null", "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=90)
    except (OSError, subprocess.SubprocessError):
        return []
    values = []
    for match in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", result.stderr or ""):
        try:
            timestamp = float(match.group(1))
            if 0 < timestamp < duration and timestamp <= _MAX_ANALYSIS_SECONDS:
                values.append(timestamp)
        except ValueError:
            continue
    return sorted(set(values))


def _pacing(average_shot: float) -> str:
    if average_shot <= 1.5:
        return "very_fast"
    if average_shot <= 3.5:
        return "fast"
    if average_shot <= 5.0:
        return "medium"
    return "slow"


def analyze_reference_video(video_path: str, reference_id: str) -> ReferenceVideoAnalysis:
    metadata = _run_ffprobe(video_path)
    streams = metadata.get("streams") or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    try:
        duration = float((metadata.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0 or duration > _MAX_ANALYSIS_SECONDS:
        raise ValueError(f"Reference video duration must be between 0 and {_MAX_ANALYSIS_SECONDS} seconds")

    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    fps = _fps(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))
    cuts = _detect_cuts(video_path, duration)
    shot_count = max(1, len(cuts) + 1)
    average_shot = duration / shot_count

    if duration <= 3:
        hook_window = duration
    else:
        hook_window = min(3.0, duration * 0.2)

    pacing = _pacing(average_shot)
    structure = ["opening hook", "problem or desire", "product/value demonstration", "payoff", "CTA"]
    if duration < 10:
        structure = ["opening hook", "product/value demonstration", "payoff or CTA"]
    principles = [
        f"Use approximately {average_shot:.1f}s visual beats to match the reference pacing.",
        f"Make the first {hook_window:.1f}s visually decisive.",
        "Change visual information when the narrative point changes.",
        "Reserve the final beat for a clear payoff or CTA.",
    ]
    originality_rules = [
        "Do not copy the reference script, wording, shots, creator identity, or exact sequence.",
        "Reuse only high-level pacing, storytelling, and presentation principles.",
        "Rebuild every scene around the actual product facts and available assets.",
    ]
    return ReferenceVideoAnalysis(
        reference_id=reference_id,
        duration_seconds=round(duration, 3),
        width=width,
        height=height,
        fps=round(fps, 3),
        has_audio=has_audio,
        shot_count=shot_count,
        average_shot_seconds=round(average_shot, 3),
        pacing=pacing,
        hook_window_seconds=round(hook_window, 3),
        structure=structure,
        creative_principles=principles,
        originality_rules=originality_rules,
    )


def save_reference_upload(file_obj, filename: str, max_bytes: int = 100 * 1024 * 1024) -> tuple[str, str]:
    """Persist a validated upload under storage/reference_videos using an opaque ID."""
    safe_name = Path(filename or "reference.mp4").name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".mp4", ".mov", ".m4v", ".webm", ".mkv"}:
        raise ValueError("Unsupported reference video format")
    reference_id = utils.get_uuid()
    directory = Path(utils.storage_dir("reference_videos", create=True))
    output = directory / f"{reference_id}{suffix}"
    total = 0
    with output.open("wb") as destination:
        while True:
            chunk = file_obj.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                destination.close()
                output.unlink(missing_ok=True)
                raise ValueError("Reference video is larger than 100 MB")
            destination.write(chunk)
    return reference_id, str(output)
