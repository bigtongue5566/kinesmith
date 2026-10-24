"""Real, local Music-First / Visual-First / Joint Creation acceptance workflow.

uv run python scripts/verify_collaboration.py --opusmith ../opusmith
Uses only installed runtimes; source Opusmith files are read-only. All generated
music/visual sources, source relations and technical evidence remain in --output.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import subprocess

from kinesmith.interchange import sha256, write_contract
from kinesmith.tools import ffmpeg_path


ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def run(args: list[str], *, cwd=ROOT, log: Path | None = None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def cli(*args, log=None):
    return run(["uv", "run", "--offline", "--no-sync", "--project", str(ROOT), "kinesmith", *map(str, args)], log=log)


def project(name, *, source="scenes/canvas.html", audio=None, contract=None):
    result = {"schema_version": "1.0", "id": name, "title": name, "revision": 1,
              "fps": "24", "width": 640, "height": 360, "duration_frames": 144, "seed": 73,
              "prompt": "Kinesmith 與 Opusmith 雙向協作驗收；不宣稱為使用者指定完整創作。",
              "scenes": [{"id": "form", "engine": "canvas", "source": source,
                          "start_frame": 0, "duration_frames": 72, "params": {"accent": "#65d4cf"}},
                         {"id": "motion", "engine": "canvas", "source": source,
                          "start_frame": 72, "duration_frames": 72, "params": {"accent": "#ff775a"}}]}
    if audio:
        result["audio"] = {"source": audio, "offset_seconds": 0}
    if contract:
        result["interchange"] = contract
    return result


COMPOSE = '''"""Agent-authored response to the actual visual-first cue request.
No extra model, sample library or vocal engine. Run through the installed Opusmith
Python environment: uv run --no-project --python <opusmith-venv-python> python compose.py <output>
"""
import json
from pathlib import Path
import sys
from opusmith import Note, Patch, Score, Section, Track
from opusmith.model import Effects
from opusmith.project import create_project, publish

out = Path(sys.argv[1]).resolve()
request = json.loads((out.parent / "visual-request.av.json").read_text(encoding="utf-8"))
assert request["mode"] == "visual-first"
assert [(cue["start_seconds"], cue["end_seconds"]) for cue in request["events"]] == [(0, 3), (3, 6)]
score = Score(title="Form becomes motion / visual cue response", bpm=120, length_beats=12,
    key="D minor", tail_seconds=0.4, seed=73,
    sections=[Section(name="form", start=0, end=6, intent="形狀展開，留白"),
              Section(name="motion", start=6, end=12, intent="動作擴張，增加密度")],
    tracks=[
      Track(id="pluck", name="Form motif", gain_db=-21,
        patch=Patch(engine="pluck", attack=0.004, decay=0.3, sustain=0.1, release=0.28, cutoff_hz=3500),
        notes=[Note(pitch=p, start=b, duration=0.65, velocity=v)
               for b,p,v in [(0,62,92),(1.5,65,80),(3,69,85),(4.5,65,76),(6,74,100),(7,72,85),(8,69,90),(9,65,80),(10,69,90),(11,62,82)]],
        effects=Effects(reverb_mix=0.08, reverb_size=0.35)),
      Track(id="pulse", name="Motion accents", role="drums", is_drum=True, gain_db=-20,
        patch=Patch(engine="kick", attack=0.003, decay=0.12, sustain=0, release=0.06),
        notes=[Note(pitch=36, start=b, duration=0.15, velocity=92) for b in [0,3,6,7,8,9,10,11]]),
      Track(id="foundation", name="Low anchor", gain_db=-27,
        patch=Patch(engine="fm", attack=0.02, decay=0.2, sustain=0.25, release=0.15,
                    fm_ratio=1, fm_index=0.2, cutoff_hz=900),
        notes=[Note(pitch=38, start=0, duration=5.5, velocity=80),
               Note(pitch=38, start=6, duration=5.5, velocity=88)])],
    decisions=["Responds to two 3-second picture cues at quarter-note beats 0 and 6.",
               "Six-second body plus 0.4-second effects tail, intentionally trimmed by picture edit.",
               "Original local synthesis only, no third-party samples or generative model."])
create_project(out, "依實際 visual-request.av.json 的兩個三秒場景創作配樂。",
               "# Motion Brief response\\n\\n120 BPM、D minor；前三秒疏、後三秒密，於 3 秒交接。", source=Path(__file__))
publish(out, score, request="Visual-first cue response", sample_rate=44100, mp3=False)
print(json.dumps({"project": str(out), "notes": sum(len(t.notes) for t in score.tracks)}, ensure_ascii=False))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opusmith", type=Path, default=ROOT.parent / "opusmith")
    parser.add_argument("--output", type=Path, default=ROOT / "examples" / "collaboration")
    parser.add_argument("--skip-render", action="store_true", help="只重建資料；不把此執行宣稱為影片驗收")
    args = parser.parse_args()
    upstream, output = args.opusmith.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("UV_CACHE_DIR", str(ROOT / ".cache" / "uv"))
    os.environ.setdefault("UV_PYTHON_INSTALL_DIR", str(ROOT / ".cache" / "python"))
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    source_project = upstream / "examples" / "projects" / "seams-of-dawn"
    current = json.loads((source_project / "CURRENT.json").read_text(encoding="utf-8"))
    snapshot = source_project / current["path"]
    original = {str(p.relative_to(source_project)): sha256(p) for p in source_project.rglob("*")
                if p.is_file() and p.suffix.lower() in (".json", ".wav", ".flac", ".py", ".ustx", ".md")}
    logs = output / "logs"
    logs.mkdir(exist_ok=True)

    # Music-first: import the actual complete upstream immutable project first.
    imported = output / "upstream-import.av.json"
    cli("import-opusmith", source_project, "--output", imported, "--fps", "24",
        "--offset", str(-float(Fraction(480, 31))), log=logs / "music-first-import.log")
    contract = json.loads(imported.read_text(encoding="utf-8"))
    mf = output / "music-first"
    (mf / "scenes").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "examples/gallery/scenes/lyrics.html", mf / "scenes/lyrics.html")
    shutil.copyfile(snapshot / "score.json", mf / "source-score.json")
    shutil.copyfile(snapshot / "vocals/lead-v3/receipt.json", mf / "vocal-receipt.json")
    source_audio = snapshot / "audio/master.wav"
    run([ffmpeg_path(), "-y", "-v", "error", "-ss", str(float(Fraction(480, 31))),
         "-i", str(source_audio), "-t", "6", "-c:a", "pcm_s24le", str(mf / "excerpt.wav")])
    import soundfile as sf
    info = sf.info(str(mf / "excerpt.wav"))
    clip = deepcopy(contract)
    clip["audio"] = [{"path": str(mf / "excerpt.wav"), "relative_path": "excerpt.wav",
        "sha256": sha256(mf / "excerpt.wav"), "role": "master", "offset_seconds": 0,
        "measured": True, "duration_seconds": info.duration,
        "sample_rate": info.samplerate, "samples": info.frames, "channels": info.channels}]
    clip["sources"] = [{"tool": "opusmith", "path": str(mf / "source-score.json"),
                        "relative_path": "source-score.json", "sha256": sha256(mf / "source-score.json"),
                        "format_version": 1, "project_version": current["version"], "software_version": "0.2.0"},
                       {"tool": "opusmith", "path": str(mf / "vocal-receipt.json"),
                        "relative_path": "vocal-receipt.json", "sha256": sha256(mf / "vocal-receipt.json"),
                        "format_version": 1}]
    clip["duration"].update(audio_seconds=info.duration, timeline_seconds=6, audio_measured=True)
    clip["warnings"].append("明確剪輯上游 master [480/31, 480/31+6) 秒；音訊 excerpt 已移至零點，音符保留負 offset。六秒片段不含整曲效果尾音。")
    write_contract(mf / "music.av.json", clip)
    picture = project("music-first-lyric-excerpt", source="scenes/lyrics.html", audio="excerpt.wav", contract="music.av.json")
    picture["scenes"] = [{"id": "lyric", "engine": "canvas", "source": "scenes/lyrics.html",
                          "start_frame": 0, "duration_frames": 144}]
    picture["licenses"] = [{"file": "excerpt.wav", "kind": "upstream-original-music-and-vocal",
        "source": "https://github.com/bigtongue5566/opusmith/releases/tag/v0.2.0",
        "review": "保留原人聲收據；聲庫與角色圖像權利另計，不含角色圖像。", "receipt": "vocal-receipt.json"}]
    write(mf / "project.json", picture)
    write(mf / "PROVENANCE.json", {"upstream": "https://github.com/bigtongue5566/opusmith",
        "release": "v0.2.0", "snapshot": current["version"], "master_sha256": sha256(source_audio),
        "excerpt_start_rational_seconds": "480/31", "excerpt_duration_seconds": 6,
        "score_sha256": sha256(snapshot / "score.json"), "timing_precision": "score-note",
        "audio_excerpt_sha256": sha256(mf / "excerpt.wav"), "listening_review": "未完成主觀聆聽"})

    # Visual-first: hand off a real editable two-scene picture, then render music
    # through the genuine installed Opusmith package. No source project writes.
    vf = output / "visual-first"
    (vf / "scenes").mkdir(parents=True, exist_ok=True)
    (vf / "source").mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "examples/gallery/scenes/canvas.html", vf / "scenes/canvas.html")
    write(vf / "project.json", project("visual-first-cue-response"))
    shutil.copyfile(vf / "project.json", vf / "picture-v1-request.json")
    cli("handoff", vf / "picture-v1-request.json", "--output", vf / "visual-request.av.json",
        "--request", "兩個三秒場景，前三秒留白展開，第三秒增加節奏密度；原創合成音樂，保留 6 秒畫面時長。",
        log=logs / "visual-first-handoff.log")
    compose = vf / "source/compose.py"
    compose.write_text(COMPOSE, encoding="utf-8")
    music = vf / "music"
    if music.exists():
        # Preserve all versions; a rerun creates a new sibling rather than overwriting.
        music = vf / f"music-rerun-{len(list(vf.glob('music*')))}"
    interpreter = upstream / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not interpreter.is_file():
        raise FileNotFoundError("先依 Opusmith 官方說明 uv sync；驗收使用已安裝的實際 Opusmith 環境。")
    run(["uv", "run", "--no-project", "--python", str(interpreter), "python", str(compose), str(music)],
        log=logs / "visual-first-opusmith-render.log")
    cli("import-opusmith", music, "--output", vf / "music-return.av.json", "--fps", "24",
        log=logs / "visual-first-return.log")
    returned = json.loads((vf / "music-return.av.json").read_text(encoding="utf-8"))
    returned["links"].append({"relation": "score-for-picture", "visual_sha256": sha256(vf / "project.json"),
                               "music_sha256": next(s["sha256"] for s in returned["sources"] if s["path"].endswith("score.json")),
                               "request_sha256": sha256(vf / "visual-request.av.json")})
    write_contract(vf / "music-return.av.json", returned)
    master = next(a for a in returned["audio"] if a["role"] == "master")
    picture = json.loads((vf / "project.json").read_text(encoding="utf-8"))
    picture["audio"] = {"source": Path(master["path"]).relative_to(vf).as_posix(), "offset_seconds": 0}
    picture["interchange"] = "music-return.av.json"
    write(vf / "project.json", picture)

    results = {}
    for label, folder in (("music-first", mf), ("visual-first", vf)):
        cli("validate", folder / "project.json", log=logs / f"{label}-validate.log")
        if not args.skip_render:
            cli("render", folder / "project.json", "--output", folder / "preview.webm", log=logs / f"{label}-render.log")
            cli("qa", folder / "preview.webm", "--output", folder / "qa", "--project", folder / "project.json",
                log=logs / f"{label}-qa.log")
            results[label] = {"video_sha256": sha256(folder / "preview.webm"), "qa": str(folder / "qa")}

    # Joint: issue an actual bounded request, preserve pre-revision project,
    # use native Kinesmith revision, and prove the audio/unrelated scene stays fixed.
    before_picture = json.loads((vf / "project.json").read_text(encoding="utf-8"))
    before_audio, before_source = sha256(master["path"]), sha256(vf / "scenes/canvas.html")
    cli("joint-request", vf / "music-return.av.json", "--output", vf / "joint-request.av.json",
        "--id", "visual-accent-002", "--target", "visual", "--scope", "visual",
        "--request", "只把 motion 場景 accent 改為紫色；保留 form 場景與音樂。", log=logs / "joint-request.log")
    cli("revise", vf / "project.json", "--scene", "motion", "--prompt", "只改第二場景為紫色；音樂與其他場景保持原樣。",
        "--params", '{"accent":"#b8a0ff"}', log=logs / "joint-revise.log")
    after_picture = json.loads((vf / "project.json").read_text(encoding="utf-8"))
    assert before_picture["scenes"][0] == after_picture["scenes"][0]
    assert before_audio == sha256(master["path"])
    assert before_source == sha256(vf / "scenes/canvas.html")
    if not args.skip_render:
        cli("render", vf / "project.json", "--output", vf / "joint-revised.webm", log=logs / "joint-render.log")
        cli("qa", vf / "joint-revised.webm", "--output", vf / "joint-qa", "--project", vf / "project.json",
            log=logs / "joint-qa.log")
        results["joint"] = {"video_sha256": sha256(vf / "joint-revised.webm"), "qa": str(vf / "joint-qa")}
        first = json.loads((vf / "preview-render.json").read_text(encoding="utf-8"))
        revised = json.loads((vf / "joint-revised-render.json").read_text(encoding="utf-8"))
        assert first["scenes"][0]["frame_hashes"] == revised["scenes"][0]["frame_hashes"]
        assert revised["scenes"][0]["cache_hit"] is True
        results["joint"]["unrelated_scene_raw_frames_identical"] = True
        results["joint"]["unrelated_scene_cache_reused"] = True
    after = {relative: sha256(source_project / relative) for relative in original}
    assert original == after, "Upstream source files were modified"
    active = [lyric for lyric in clip["lyrics"] if lyric["start_seconds"] < 6 and lyric["end_seconds"] > 0]
    evidence = {"status": "rendered-and-technically-checked" if not args.skip_render else "data-only",
        "upstream_files_checked_unchanged": len(original), "upstream_snapshot": current["version"],
        "imported_notes": sum(e["kind"] == "note" for e in contract["events"]),
        "imported_lyrics": len(contract["lyrics"]), "excerpt_lyric_events": len(active),
        "vocal_timing_precision": "score-note; no phoneme timings supplied by upstream",
        "visual_request_cues": len(before_picture["scenes"]), "returned_music_notes": sum(e["kind"] == "note" for e in returned["events"]),
        "music_audio_unchanged_by_visual_revision": before_audio == sha256(master["path"]),
        "unrelated_scene_unchanged": before_picture["scenes"][0] == after_picture["scenes"][0],
        "original_editable_source_unchanged": before_source == sha256(vf / "scenes/canvas.html"),
        "results": results, "subjective_audio_visual_review": "尚待人工聆聽／視覺評審；技術量測不是藝術品質驗收"}
    write(output / "validation.json", evidence)
    (output / "REPORT.md").write_text("# 雙向影音協作驗收\n\n"
        "已透過真實 Opusmith 專案與實際 Plugin CLI 執行三種模式，數據見 validation.json。\n\n"
        "Music-first：從《Seams of Dawn》v003 擷取第一個歌詞段六秒，使用真實 master（含合成人聲），"
        "保留原 score、授權 receipt、來源 SHA256 及剪輯位置。字幕是 score-note，沒有音素時間。\n\n"
        "Visual-first：先產生兩個三秒場景的實際交接需求，再由當前 Agent 撰寫可編輯 compose.py，"
        "透過本機真正 Opusmith v0.2.0 合成新配樂、MIDI、stems、版本與報告，回傳並同步到六秒畫面。\n\n"
        "Joint：建立只改畫面的需求，用 native revise 修改第二場景 accent，重渲染；"
        "音樂 master、第一場景設定與原始 HTML SHA256 保持不變。\n\n"
        "影片為 640×360、24 FPS 的功能驗收片段；每段皆提供全片解碼、Contact Sheet 與客觀 QA。"
        "未宣稱已完成主觀聆聽或專業藝術品質審定，也未以這次本機工具流程冒充兩平台模型自主委派驗收。\n",
        encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
