import json
import subprocess
from pathlib import Path

import pytest

from app.services.render_qa import RenderQAError, validate_render


def _fake_probe(monkeypatch, metadata):
    def run(*args, **kwargs):
        class Result:
            returncode = 0
            stderr = ""
            stdout = json.dumps(metadata)
        return Result()

    monkeypatch.setattr(subprocess, "run", run)


def test_render_qa_accepts_valid_vertical_mp4(monkeypatch, tmp_path: Path):
    output = tmp_path / "final.mp4"
    output.write_bytes(b"mp4")
    _fake_probe(
        monkeypatch,
        {
            "format": {"duration": "20.0"},
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920, "duration": "20.0", "avg_frame_rate": "30/1", "codec_name": "h264"},
                {"codec_type": "audio", "duration": "20.0", "codec_name": "aac"},
            ],
        },
    )
    report = validate_render(str(output), expected_duration=20)
    assert report["passed"] is True
    assert report["aspect_ratio"] == "9:16"
    assert report["width"] == 1080


def test_render_qa_rejects_wrong_resolution(monkeypatch, tmp_path: Path):
    output = tmp_path / "final.mp4"
    output.write_bytes(b"mp4")
    _fake_probe(
        monkeypatch,
        {
            "format": {"duration": "20.0"},
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080, "duration": "20.0", "avg_frame_rate": "30/1"},
                {"codec_type": "audio", "duration": "20.0"},
            ],
        },
    )
    with pytest.raises(RenderQAError, match="1080x1920"):
        validate_render(str(output), expected_duration=20)


def test_render_qa_rejects_missing_audio(monkeypatch, tmp_path: Path):
    output = tmp_path / "final.mp4"
    output.write_bytes(b"mp4")
    _fake_probe(
        monkeypatch,
        {
            "format": {"duration": "20.0"},
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920, "duration": "20.0", "avg_frame_rate": "30/1"},
            ],
        },
    )
    with pytest.raises(RenderQAError, match="audio stream"):
        validate_render(str(output), expected_duration=20)
