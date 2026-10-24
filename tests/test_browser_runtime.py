"""Actual browser isolation tests, with a separate process guarding runaway JS."""
import json
import os
import signal
import subprocess
import sys
import time

import pytest

from kinesmith.browser import render_browser


def context():
    return {"width": 64, "height": 36, "fps": "24", "fps_number": 24,
            "duration_frames": 2, "duration": 2 / 24, "seed": 73,
            "params": {}, "features": None, "interchange": None}


def render(root, source, frames):
    frames.mkdir(parents=True, exist_ok=True)
    return render_browser({"id": "runtime", "source": source, "start_frame": 0,
                           "duration_frames": 2}, context(), root, frames)


def test_sampled_clocks_seeded_random_and_native_frame_motion_are_reproducible(tmp_path):
    (tmp_path / "scene.html").write_text('''<canvas id="stage" width="64" height="36"></canvas><script>
      const g=document.querySelector('#stage').getContext('2d');
      window.renderFrame=(frame,ctx)=>{
        g.fillStyle=`rgb(${Math.floor(Math.random()*255)},${Math.floor(Date.now())%255},${Math.floor(performance.now())%255})`;
        g.fillRect(0,0,64,36);g.fillStyle='white';g.fillRect(frame*12,4,8,8);
      };</script>''', encoding="utf-8")
    render(tmp_path, "scene.html", tmp_path / "one")
    render(tmp_path, "scene.html", tmp_path / "two")
    assert (tmp_path / "one/000000.png").read_bytes() == (tmp_path / "two/000000.png").read_bytes()
    assert (tmp_path / "one/000001.png").read_bytes() == (tmp_path / "two/000001.png").read_bytes()
    assert (tmp_path / "one/000000.png").read_bytes() != (tmp_path / "one/000001.png").read_bytes()


def test_mismatched_native_canvas_dimensions_fail_before_success_manifest(tmp_path):
    (tmp_path / "scene.html").write_text('''<canvas id="stage" width="63" height="36"></canvas>
      <script>window.renderFrame=()=>{};</script>''', encoding="utf-8")
    with pytest.raises(Exception, match="stage canvas dimensions"):
        render(tmp_path, "scene.html", tmp_path / "frames")
    assert not list((tmp_path / "frames").glob("*.png"))


def test_infinite_native_loop_times_out_and_closes_browser(tmp_path):
    (tmp_path / "scene.html").write_text('''<canvas id="stage" width="64" height="36"></canvas>
      <script>window.renderFrame=()=>{while(true){}};</script>''', encoding="utf-8")
    frames = tmp_path / "frames"
    frames.mkdir()
    runner = tmp_path / "run.py"
    runner.write_text('''import json,sys,time
from pathlib import Path
from kinesmith.browser import render_browser
ctx=json.loads(sys.argv[1]);root=Path(sys.argv[2]);start=time.monotonic()
try:
 render_browser({'id':'infinite','source':'scene.html','start_frame':0,'duration_frames':2},ctx,root,root/'frames')
except RuntimeError as exc:
 print(json.dumps({'error':str(exc),'elapsed':time.monotonic()-start}),flush=True)
else:
 raise AssertionError('runaway JavaScript must fail')
''', encoding="utf-8")
    environment = {**os.environ, "KINESMITH_FRAME_TIMEOUT": "0.5"}
    options = {"start_new_session": True} if os.name != "nt" else {}
    start = time.monotonic()
    process = subprocess.Popen([sys.executable, str(runner), json.dumps(context()), str(tmp_path)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, **options)
    try:
        stdout, stderr = process.communicate(timeout=18)
    except subprocess.TimeoutExpired:
        # Always clean the browser process tree if the production cleanup regresses.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        pytest.fail("native loop timeout did not close browser process tree within 18s")
    assert process.returncode == 0, stderr.decode(errors="replace")
    result = json.loads(stdout.decode().strip().splitlines()[-1])
    assert "frame 0 exceeded 0.5s" in result["error"]
    assert time.monotonic() - start < 18
    assert not list(frames.glob("*.png"))
    # A fresh browser must remain usable after the failed JS run.
    (tmp_path / "good.html").write_text('''<canvas id="stage" width="64" height="36"></canvas>
      <script>window.renderFrame=()=>{};</script>''', encoding="utf-8")
    assert render(tmp_path, "good.html", tmp_path / "good-frames")["browser"]
