import json
import subprocess

import imageio_ffmpeg
from PIL import Image
import pytest

from kinesmith.qa import qa_video


def make_video(path, source, fps="12", duration="1"):
    separator = ":" if "=" in source else "="
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-f", "lavfi", "-i",
         f"{source}{separator}size=320x180:rate={fps}:duration={duration}", "-c:v", "libvpx-vp9", "-crf", "40", "-b:v", "0", str(path)],
        capture_output=True, check=True,
    )


def test_real_video_decode_properties_and_contact_sheet(tmp_path):
    video, out = tmp_path / "motion.webm", tmp_path / "qa"
    make_video(video, "testsrc2")
    result = qa_video(video, out, {"width": 320, "height": 180, "fps": 12, "duration_seconds": 1})
    assert result["technical_checks_passed"]
    assert result["measurements"]["frame_count"] == 12
    assert result["visual_review"] == "required"
    assert result["manual_checks"]["text_clipping"] == "not_verified"
    assert len(result["representative_frames"]) == 12
    with Image.open(result["contact_sheet"]) as sheet:
        assert sheet.width == 1280
        assert sheet.height > 500
    assert json.loads((out / "qa.json").read_text(encoding="utf-8")) == result


def test_black_and_freeze_flags_do_not_masquerade_as_visual_approval(tmp_path):
    video = tmp_path / "black.webm"
    make_video(video, "color=black")
    result = qa_video(video, tmp_path / "qa", {"duration_seconds": 2})
    assert not result["technical_checks_passed"]
    assert result["heuristic_flags"]["possible_black_ranges"][0]["start_seconds"] == 0
    assert result["heuristic_flags"]["possible_freeze_ranges"]
    assert result["visual_review"] == "required"


def test_fractional_fps_preserves_decoder_rational(tmp_path):
    video = tmp_path / "fractional.webm"
    make_video(video, "testsrc2", "24000/1001", "1")
    result = qa_video(video, tmp_path / "qa", {"fps": "24000/1001"})
    assert result["checks"]["fps"]["passed"]
    assert result["measurements"]["fps"] == pytest.approx(24000 / 1001)
