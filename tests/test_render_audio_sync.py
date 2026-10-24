"""Behavioral render regression tests using measured muxed audio and real cache files."""
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest
from scipy.io import wavfile

from kinesmith.audio import decode_audio
from kinesmith.project import load_project, revise_project
from kinesmith.render import compose_frames, render_project, render_scene
from kinesmith.tools import write_json


def make_project(tmp_path, *, offset=None, shared=False):
    Image.new("RGB", (64, 36), "red").save(tmp_path / "red.png")
    project = {"schema_version": "1.0", "id": "regression", "title": "behavioral regression",
               "revision": 1, "width": 64, "height": 36, "fps": "24", "duration_frames": 48,
               "scenes": [{"id": "a", "engine": "image", "source": "red.png", "start_frame": 0,
                           "duration_frames": 24 if shared else 48}]}
    if shared:
        project["scenes"].append({"id": "b", "engine": "image", "source": "red.png",
                                  "start_frame": 24, "duration_frames": 24})
    if offset is not None:
        sr = 48000
        audio = np.zeros(sr, np.float32)
        start, count = int(.4 * sr), int(.06 * sr)
        t = np.arange(count) / sr
        audio[start:start + count] = .6 * np.sin(2 * np.pi * 1000 * t) * np.hanning(count)
        wavfile.write(tmp_path / "pulse.wav", sr, audio)
        project["audio"] = {"source": "pulse.wav", "offset_seconds": offset}
    return project, write_json(tmp_path / "project.json", project)


@pytest.mark.parametrize("offset", [.25, -.25])
def test_muxed_audio_offset_is_measurable_and_tail_pads_to_picture(tmp_path, offset):
    _, path = make_project(tmp_path, offset=offset)
    result = render_project(path)
    audio = decode_audio(result["output"], sample_rate=48000)
    assert len(audio) / 48000 == pytest.approx(2, abs=.025)
    audible = np.where(np.abs(audio) > .05)[0]
    assert len(audible) > 100
    # Input pulse begins at .4s; Hann onset exceeds threshold slightly later.
    assert audible[0] / 48000 == pytest.approx(.4 + offset, abs=.015)
    assert np.max(np.abs(audio[int(1.5 * 48000):])) < .002
    assert result["measured"]["frame_count"] == 48


@pytest.mark.parametrize("offset", [-1.5, 3.0])
def test_audio_outside_picture_range_becomes_silence(tmp_path, offset):
    _, path = make_project(tmp_path, offset=offset)
    result = render_project(path)
    audio = decode_audio(result["output"], sample_rate=48000)
    assert len(audio) / 48000 == pytest.approx(2, abs=.025)
    assert np.max(np.abs(audio)) < .002


def test_cache_detects_changed_frame_and_restores_actual_pixels(tmp_path):
    project, _ = make_project(tmp_path)
    first = render_scene(project["scenes"][0], project, tmp_path)
    cached_frame = Path(first["frames_path"]) / "000003.png"
    Image.new("RGB", (64, 36), "blue").save(cached_frame)
    repaired = render_scene(project["scenes"][0], project, tmp_path)
    assert not repaired["cache_hit"]
    assert repaired["frame_hashes"] == first["frame_hashes"]
    assert next(compose_frames(project, [repaired])).getpixel((0, 0)) == (255, 0, 0)


def test_cache_rejects_incomplete_manifest_instead_of_missing_frames_later(tmp_path):
    project, _ = make_project(tmp_path)
    first = render_scene(project["scenes"][0], project, tmp_path)
    frames = Path(first["frames_path"])
    manifest = frames.parent / "render.json"
    receipt = json.loads(manifest.read_text(encoding="utf-8"))
    (frames / "000003.png").unlink()
    receipt["frame_hashes"].pop("000003.png")
    write_json(manifest, receipt)
    repaired = render_scene(project["scenes"][0], project, tmp_path)
    assert not repaired["cache_hit"]
    assert (frames / "000003.png").is_file()
    assert len(list(compose_frames(project, [repaired]))) == 48


def test_source_revision_of_shared_asset_changes_only_requested_scene(tmp_path):
    project, path = make_project(tmp_path, shared=True)
    original = render_project(path)
    Image.new("RGB", (64, 36), "blue").save(tmp_path / "replacement.png")
    revise_project(path, "a", "只修改第一個場景", source=str(tmp_path / "replacement.png"))
    revised, _ = load_project(path)
    rendered = render_project(path)
    images = list(compose_frames(revised, rendered["scenes"]))
    assert images[0].getpixel((0, 0)) == (0, 0, 255)
    assert images[24].getpixel((0, 0)) == (255, 0, 0)
    assert rendered["scenes"][1]["cache_hit"]
    assert rendered["scenes"][1]["frame_hashes"] == original["scenes"][1]["frame_hashes"]


def test_shorter_png_rerender_has_no_stale_tail_frames(tmp_path):
    project, path = make_project(tmp_path)
    output = tmp_path / "png-sequence"
    render_project(path, output=output, fmt="png")
    assert len(list(output.glob("*.png"))) == 48
    project["duration_frames"] = 24
    project["scenes"][0]["duration_frames"] = 24
    write_json(path, project)
    render_project(path, output=output, fmt="png")
    assert len(list(output.glob("*.png"))) == 24
    assert not (output / "000024.png").exists()
