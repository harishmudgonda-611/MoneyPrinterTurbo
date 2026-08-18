"""Run the shared MPT task and gate Reel completion on deterministic render QA."""

from __future__ import annotations

from typing import Any

from app.models import const
from app.services import render_qa
from app.services import state as sm
from app.services import task as task_service


def start_reel_task(task_id: str, params: Any, stop_at: str = "video", **kwargs):
    """Execute the normal MPT task, then validate final Reel MP4s before success."""
    result = task_service.start(task_id, params, stop_at=stop_at, **kwargs)

    # Only complete video renders are gated. Script/audio/material preview tasks keep
    # the existing MPT behavior unchanged.
    if stop_at != "video" or not isinstance(result, dict):
        return result

    video_paths = result.get("videos") or []
    if not video_paths:
        return result

    # Prefer the narration duration already returned by the MPT task. If unavailable,
    # the validator still performs all structural checks except duration matching.
    expected_duration = result.get("audio_duration")
    try:
        expected_duration = float(expected_duration) if expected_duration else None
    except (TypeError, ValueError):
        expected_duration = None

    reports: list[dict] = []
    for index, video_path in enumerate(video_paths, start=1):
        try:
            report = render_qa.validate_render(
                video_path,
                expected_duration=expected_duration,
            )
        except render_qa.RenderQAError as exc:
            failure = {
                "task_id": task_id,
                "state": const.TASK_STATE_FAILED,
                "progress": int(result.get("progress", 100) or 100),
                "failed_stage": "validation",
                "error": f"render QA failed for video {index}: {exc}",
                "validation_video_index": index,
                "validation_path": video_path,
            }
            sm.state.update_task(task_id, **failure)
            return failure
        reports.append({"video_index": index, **report})

    sm.state.update_task(
        task_id,
        state=const.TASK_STATE_COMPLETE,
        progress=100,
        render_qa=reports,
    )
    result["render_qa"] = reports
    return result
