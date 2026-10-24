"""Opt-in native render tests; these encode real video and verify observable output."""
import os
from pathlib import Path
import shutil

import pytest

from kinesmith.project import ROOT, load_project
from kinesmith.qa import qa_video
from kinesmith.render import render_project


pytestmark = pytest.mark.skipif(os.environ.get("KINESMITH_RUN_RENDER_TESTS") != "1",
                               reason="Set KINESMITH_RUN_RENDER_TESTS=1 for real six-engine renders")


@pytest.mark.parametrize("engine", ["canvas", "rough", "p5", "three", "manim", "blender"])
def test_native_engine_real_animation(engine, tmp_path):
    destination = tmp_path / "gallery"
    shutil.copytree(ROOT / "examples/gallery", destination,
                    ignore=shutil.ignore_patterns(".render-cache", "renders", "__pycache__", "media"))
    project = destination / f"project-{engine}.json"
    report = render_project(project, output=destination / f"{engine}.webm")
    qa = qa_video(report["output"], destination / f"qa-{engine}",
                  {"width": 640, "height": 360, "fps": 24, "duration_seconds": 2})
    assert qa["technical_checks_passed"]
    assert qa["measurements"]["frame_count"] == 48
    assert not qa["heuristic_flags"]["possible_black_ranges"]
    frames = Path(report["scenes"][0]["frames_path"])
    assert (frames / "000012.png").read_bytes() != (frames / "000036.png").read_bytes()


def test_cross_engine_composite_and_local_revision_cache(tmp_path):
    from kinesmith.project import revise_project

    destination = tmp_path / "gallery"
    shutil.copytree(ROOT / "examples/gallery", destination,
                    ignore=shutil.ignore_patterns(".render-cache", "renders", "__pycache__", "media"))
    project, path = load_project(destination)
    before = render_project(path)
    revise_project(path, "canvas", "只將 Canvas 強調色改為珊瑚色", params={"accent": "#ff775a"})
    after = render_project(path)
    assert not after["scenes"][0]["cache_hit"]
    assert all(scene["cache_hit"] for scene in after["scenes"][1:])
    assert before["output_sha256"] != after["output_sha256"]
    assert before["scenes"][1:][0]["source_sha256"] == after["scenes"][1:][0]["source_sha256"]
    assert project["revision"] == 1
