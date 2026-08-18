from unittest.mock import patch

from app.services.reference_video import _fps, _pacing, analyze_reference_video


def test_fps_parsing():
    assert _fps("30/1") == 30
    assert _fps("30000/1001") > 29
    assert _fps("0/0") == 0


def test_pacing_buckets():
    assert _pacing(1.0) == "very_fast"
    assert _pacing(2.0) == "fast"
    assert _pacing(4.0) == "medium"
    assert _pacing(6.0) == "slow"


def test_analysis_builds_structural_principles():
    metadata = {
        "format": {"duration": "20"},
        "streams": [
            {
                "codec_type": "video",
                "width": 1080,
                "height": 1920,
                "avg_frame_rate": "30/1",
            },
            {"codec_type": "audio"},
        ],
    }
    with patch("app.services.reference_video._run_ffprobe", return_value=metadata), patch(
        "app.services.reference_video._detect_cuts", return_value=[2.0, 5.0, 8.0, 12.0, 16.0]
    ):
        result = analyze_reference_video("/tmp/reference.mp4", "ref-1")

    assert result.reference_id == "ref-1"
    assert result.width == 1080
    assert result.height == 1920
    assert result.has_audio is True
    assert result.shot_count == 6
    assert result.pacing == "fast"
    assert result.hook_window_seconds == 3.0
    assert result.originality_rules
