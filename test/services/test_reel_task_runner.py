from unittest.mock import patch

from app.models import const
from app.services.reel_task_runner import start_reel_task


def test_reel_task_runner_records_render_qa():
    result = {
        "task_id": "task-1",
        "state": const.TASK_STATE_COMPLETE,
        "progress": 100,
        "videos": ["/tmp/final-1.mp4"],
        "audio_duration": 20,
    }
    report = {"passed": True, "width": 1080, "height": 1920, "aspect_ratio": "9:16"}

    with patch("app.services.reel_task_runner.task_service.start", return_value=result), patch(
        "app.services.reel_task_runner.render_qa.validate_render", return_value=report
    ), patch("app.services.reel_task_runner.sm.state.update_task") as update:
        output = start_reel_task("task-1", object(), stop_at="video")

    assert output["render_qa"][0]["video_index"] == 1
    assert output["render_qa"][0]["width"] == 1080
    update.assert_called_once()
    assert update.call_args.kwargs["state"] == const.TASK_STATE_COMPLETE


def test_reel_task_runner_converts_render_qa_failure_to_failed_task():
    result = {
        "task_id": "task-1",
        "state": const.TASK_STATE_COMPLETE,
        "progress": 100,
        "videos": ["/tmp/final-1.mp4"],
        "audio_duration": 20,
    }

    from app.services.render_qa import RenderQAError

    with patch("app.services.reel_task_runner.task_service.start", return_value=result), patch(
        "app.services.reel_task_runner.render_qa.validate_render",
        side_effect=RenderQAError("Expected 1080x1920, got 720x1280"),
    ), patch("app.services.reel_task_runner.sm.state.update_task") as update:
        output = start_reel_task("task-1", object(), stop_at="video")

    assert output["state"] == const.TASK_STATE_FAILED
    assert output["failed_stage"] == "validation"
    assert "1080x1920" in output["error"]
    update.assert_called_once()
    assert update.call_args.kwargs["state"] == const.TASK_STATE_FAILED
