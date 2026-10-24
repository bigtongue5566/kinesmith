"""Editable USTX and a small offline adapter to the real OpenUtau engine.

USTX remains authoritative for phonemes, pitch, vibrato and native expressions.
No custom singing model, phonemizer, resampler or agent runtime is implemented.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np
from ruamel.yaml import YAML
import soundfile as sf

from .model import Note, Score, VocalRender, inside, json_write


def digest(path: Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def tree_hash(root: Path) -> str:
    """Hash bank/model/config contents, excluding caches written by OpenUtau."""
    entries = []
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and not any(x.lower() in {"cache", ".cache"} for x in p.relative_to(root).parts):
            if p.suffix.lower() not in {".frq", ".tmp", ".bak"}:
                entries.append((p.relative_to(root).as_posix(), digest(p)))
    return hashlib.sha256(json.dumps(entries, ensure_ascii=False).encode()).hexdigest()


def load_ustx(path: Path):
    yaml = YAML()  # YAML 1.2, round trip unknown native fields and comments.
    yaml.preserve_quotes = True
    with Path(path).open(encoding="utf-8-sig") as handle:
        data = yaml.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("voice_parts"), list):
        raise ValueError("expected a USTX project with voice_parts")
    return data


def save_ustx(path: Path, project):
    yaml = YAML()
    yaml.allow_unicode = True
    stream = io.StringIO()
    yaml.dump(project, stream)
    Path(path).write_text(stream.getvalue(), encoding="utf-8", newline="\n")


def validate_ustx(project) -> list[dict]:
    """Check timing and references without imposing a genre or tuning strategy."""
    tracks = project.get("tracks", [])
    notes = []
    if not project.get("tempos") or project["tempos"][0]["position"] != 0:
        raise ValueError("USTX needs tempo at tick zero")
    for part in project["voice_parts"]:
        index = part.get("track_no", 0)
        if not 0 <= index < len(tracks) or part.get("position", 0) < 0:
            raise ValueError("invalid part reference/position")
        previous = -1
        for n in sorted(part.get("notes", []), key=lambda n: n["position"]):
            if (n["position"] < previous or n["duration"] <= 0 or not 0 <= n["tone"] <= 127
                    or not isinstance(n.get("lyric"), str) or not n["lyric"].strip()):
                raise ValueError("voice notes need nonoverlapping timing, pitch and lyrics")
            previous = n["position"] + n["duration"]
            if previous > part["duration"]:
                raise ValueError("note extends beyond voice part")
            pitch = n.get("pitch", {}).get("data", [])
            if len(pitch) < 2 or any(not np.isfinite([p["x"], p["y"]]).all() for p in pitch):
                raise ValueError("pitch needs at least two finite native points")
            notes.append({"track": index, "position": part.get("position", 0)+n["position"], **n})
            notes[-1]["position"] = part.get("position", 0)+n["position"]
    if not notes:
        raise ValueError("no vocal notes")
    return notes


def make_ustx(score: Score, track_id: str, *, singer: str, phonemizer: str,
              renderer: str = "WORLDLINE-R") -> dict:
    """Export lyrics/notes to native USTX; tuning can then be freely edited."""
    track = next(t for t in score.tracks if t.id == track_id)
    notes = []
    for n in sorted(track.notes, key=lambda n: n.start):
        if not n.lyric:
            raise ValueError("vocal MIDI notes require explicit syllables/lyrics")
        notes.append({"position": round(n.start*480), "duration": round(n.duration*480),
            "tone": n.pitch, "lyric": n.lyric,
            "pitch": {"data": [{"x": -40.0, "y": 0.0, "shape": "io"},
                               {"x": 40.0, "y": 0.0, "shape": "io"}], "snap_first": True},
            "vibrato": {"length": 0, "period": 180, "depth": 20, "in": 20, "out": 20,
                        "shift": 0, "drift": 0, "vol_link": 0},
            "phoneme_expressions": [{"index": 0, "abbr": "vol", "value": n.velocity/127*100}],
            "phoneme_overrides": []})
    result = {"name": score.title, "ustx_version": "0.10",
        "tempos": [{"position": 0, "bpm": score.bpm}],
        "time_signatures": [{"bar_position": 0, "beat_per_bar": score.meter[0],
                             "beat_unit": score.meter[1]}],
        "tracks": [{"track_name": track_id, "singer": singer, "phonemizer": phonemizer,
                    "renderer_settings": {"renderer": renderer}}],
        "voice_parts": [{"name": track.name, "track_no": 0, "position": 0,
                         "duration": round(score.length_beats*480), "notes": notes}],
        "wave_parts": []}
    validate_ustx(result)
    return result


def edit_notes(project, *, part: int, start_tick: int, end_tick: int, transform):
    """Copy-on-write local revision; no lossy intermediate singing format."""
    if not 0 <= start_tick < end_tick:
        raise ValueError("invalid edit range")
    result = deepcopy(project)
    selected = result["voice_parts"][part]
    for n in selected["notes"]:
        start = selected.get("position", 0)+n["position"]
        end = start+n["duration"]
        if start < end_tick and end > start_tick:
            if start < start_tick or end > end_tick:
                raise ValueError("edit boundary crosses a note; split it explicitly first")
            transform(n)
    validate_ustx(result)
    return result


def render_vocal(ustx: Path, destination: Path, *, engine: Path, dotnet: Path,
                 singers: Path, bank: Path, data: Path, license_record: dict,
                 timeout: int = 600, evaluation: bool = False, steps: int = 20) -> dict:
    """Render using a pinned local OpenUtau install; reject empty/error exports.

    No network calls. Immutable outputs include bank/dependency/engine identities.
    Evaluation permits an explicitly labelled unresolved commercial chain.
    """
    ustx, destination, engine, data = map(lambda p: Path(p).resolve(),
                                        (ustx, destination, engine, data))
    project = load_ustx(ustx)
    inventory = validate_ustx(project)
    if len(project["tracks"]) != 1 or project.get("wave_parts"):
        raise ValueError("isolate one vocal track; mix backing audio separately in Score")
    if license_record.get("commercial_output_verified") is not True and not evaluation:
        raise ValueError("commercial output chain unverified; evaluation=True is local evaluation only")
    if any(not isinstance(license_record.get(k), str) or not license_record[k].strip()
           for k in ("name", "terms_url", "credit", "evidence")):
        raise ValueError("voice license needs name, terms_url, credit and review evidence")
    if not 1 <= steps <= 100 or not 1 <= timeout <= 7200:
        raise ValueError("invalid render bounds")
    if destination.exists():
        raise FileExistsError(destination)
    if not Path(bank).resolve().is_relative_to(Path(singers).resolve()):
        raise ValueError("bank must be inside singers root")
    # Reject a different singer quietly substituted by a missing/incorrect ID.
    expected_id = Path(bank).resolve().relative_to(Path(singers).resolve()).as_posix()
    if any(t.get("singer") != expected_id for t in project["tracks"]):
        raise ValueError("USTX singer does not match the reviewed bank")
    identity = {"ustx_sha256": digest(ustx), "bank_sha256": tree_hash(bank),
                "engine_sha256": digest(engine/"OpenUtau.Core.dll"),
                "bridge_sha256": digest(engine/"Opusmith.OpenUtau.dll"),
                "dependencies_sha256": tree_hash(data/"Dependencies"), "steps": steps}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="opusmith-vocal-", dir=destination.parent) as temp:
        work = Path(temp)
        job = {"Project": str(ustx), "Output": str(work/"render"), "Data": str(data),
               "Singers": str(Path(singers).resolve()), "EngineDirectory": str(engine),
               "TimeoutSeconds": timeout, "Steps": steps}
        json_write(work/"job.json", job)
        env = os.environ.copy()
        env["PATH"] = str(engine)+os.pathsep+env.get("PATH", "")
        process = subprocess.run([str(Path(dotnet).resolve()), str(engine/"Opusmith.OpenUtau.dll"),
                                  str(work/"job.json")], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=timeout+15, env=env)
        if process.returncode:
            raise RuntimeError(f"OpenUtau failed ({process.returncode}): {process.stderr[-6000:]}")
        waves = sorted((work/"render").glob("*.wav"))
        if len(waves) != 1:
            raise ValueError("render one singer/track at a time; expected one WAV")
        audio, sr = sf.read(waves[0], dtype="float32", always_2d=True)
        if (len(audio) < sr*.2 or not np.isfinite(audio).all()
                or float(np.sqrt(np.mean(audio**2))) <= 1e-6):
            raise ValueError("silent/invalid vocal output")
        if float(np.max(np.abs(audio))) >= 1:
            raise ValueError("vocal output clips; lower USTX volume/expression")
        # All identities are checked again, so concurrent edits cannot be misattributed.
        if identity["ustx_sha256"] != digest(ustx) or identity["bank_sha256"] != tree_hash(bank):
            raise ValueError("source/bank changed during render")
        destination.mkdir()
        shutil.copyfile(waves[0], destination/"dry.wav")
        shutil.copyfile(ustx, destination/"project.ustx")
        shutil.copyfile(work/"render/phonemes.json", destination/"phonemes.json")
        record = {"format_version": 1, "renderer": "OpenUtau 0.1.576", **identity,
            "license": license_record, "evaluation_only": license_record.get("commercial_output_verified") is not True,
            "audio": {"sample_rate": sr, "channels": audio.shape[1], "frames": len(audio),
                      "duration_seconds": len(audio)/sr, "source_bit_depth": 16,
                      "peak": float(np.max(np.abs(audio))),
                      "rms": float(np.sqrt(np.mean(audio**2))), "non_silent": True},
            "notes": inventory, "audio_sha256": digest(destination/"dry.wav"),
            "phonemes_sha256": digest(destination/"phonemes.json"),
            "subjective_listening": "未進行聽覺評估", "engine_log": process.stdout[-4000:]}
        json_write(destination/"receipt.json", record)
        return record


def attach_vocal(score: Score, track_id: str, project_root: Path, rendered: Path):
    """Attach frozen singing to a track and synchronize editable MIDI lyrics/notes."""
    rendered = Path(rendered).resolve()
    root = Path(project_root).resolve()
    relative = rendered.relative_to(root).as_posix()
    source = load_ustx(rendered/"project.ustx")
    if len(source["tempos"]) != 1 or source["tempos"][0]["bpm"] != score.bpm:
        raise ValueError("audio attachment currently requires score's constant tempo")
    sig = source["time_signatures"]
    if len(sig) != 1 or (sig[0]["beat_per_bar"], sig[0]["beat_unit"]) != score.meter:
        raise ValueError("audio attachment meter mismatch")
    track = next(t for t in score.tracks if t.id == track_id)
    notes = validate_ustx(source)
    if len(source["tracks"]) != 1:
        raise ValueError("attach one rendered vocal track at a time")
    track.notes = [Note(pitch=n["tone"], start=n["position"]/480, duration=n["duration"]/480,
                        lyric=n["lyric"], velocity=100) for n in notes]
    track.vocal = VocalRender(file=relative+"/dry.wav", ustx=relative+"/project.ustx",
                              receipt=relative+"/receipt.json")


def render_revision(base: Path, revised: Path, destination: Path, *, start_tick: int,
                    end_tick: int, context_seconds: float = .5,
                    crossfade_seconds: float = .04, **render_options) -> dict:
    """Render a changed phrase, retaining exact original PCM outside its context.

    Upstream renderers may change untouched waveforms on another inference. Reuse
    recorded audio, not a promise of deterministic singing. All native settings
    outside selected notes must remain identical. Keep the original source/receipt.
    """
    base, revised, destination = Path(base), Path(revised), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    original = load_ustx(base/"project.ustx")
    changed = load_ustx(revised)
    if not 0 <= start_tick < end_tick or not 0 <= context_seconds <= 2 or not 0 < crossfade_seconds <= .2:
        raise ValueError("invalid revision bounds")
    if len(original["tempos"]) != 1 or original["tempos"] != changed["tempos"]:
        raise ValueError("phrase replacement currently requires unchanged constant tempo")

    def outside(project):
        project = deepcopy(project)
        for part in project["voice_parts"]:
            kept = []
            for n in part["notes"]:
                start = part.get("position", 0)+n["position"]
                end = start+n["duration"]
                if start < end_tick and end > start_tick:
                    if start < start_tick or end > end_tick:
                        raise ValueError("revision boundary crosses a note")
                else:
                    kept.append(n)
            part["notes"] = kept
        return project

    if outside(original) != outside(changed):
        raise ValueError("native content outside the revised notes changed")
    base_receipt = json.loads((base/"receipt.json").read_text(encoding="utf-8"))
    if digest(base/"dry.wav") != base_receipt["audio_sha256"]:
        raise ValueError("base dry vocal was modified")
    if digest(base/"project.ustx") != base_receipt["ustx_sha256"]:
        raise ValueError("base USTX was modified")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="opusmith-phrase-", dir=destination.parent) as temp:
        candidate = Path(temp)/"candidate"
        record = render_vocal(revised, candidate, **render_options)
        if (record["bank_sha256"] != base_receipt["bank_sha256"]
                or record["license"] != base_receipt["license"]):
            raise ValueError("phrase revision cannot silently change the bank/license chain")
        old, sr = sf.read(base/"dry.wav", dtype="float32", always_2d=True)
        new, new_sr = sf.read(candidate/"dry.wav", dtype="float32", always_2d=True)
        if sr != new_sr or old.shape != new.shape:
            raise ValueError("revision changed audio format/length; use an explicit arrangement edit")
        bpm = original["tempos"][0]["bpm"]
        first = max(0, round((start_tick/480*60/bpm-context_seconds)*sr))
        last = min(len(old), round((end_tick/480*60/bpm+context_seconds)*sr))
        fade = min(round(crossfade_seconds*sr), (last-first)//2)
        if fade < 1:
            raise ValueError("revision is too short")
        result = old.copy()
        weight = np.ones(last-first, dtype=np.float32)
        weight[:fade] = np.linspace(0, 1, fade)
        weight[-fade:] = np.linspace(1, 0, fade)
        result[first:last] = old[first:last]*(1-weight[:, None])+new[first:last]*weight[:, None]
        sf.write(candidate/"dry.wav", result, sr, subtype="PCM_16")
        actual, _ = sf.read(candidate/"dry.wav", dtype="float32", always_2d=True)
        if not np.array_equal(actual[:first], old[:first]) or not np.array_equal(actual[last:], old[last:]):
            raise ValueError("untouched dry PCM changed")
        support = {}
        for name in ["dry.wav", "project.ustx", "receipt.json", "phonemes.json",
                     *base_receipt.get("support_files", {})]:
            source = inside(base, name)
            if name in base_receipt.get("support_files", {}) and digest(source) != base_receipt["support_files"][name]:
                raise ValueError("base revision support was modified")
            target = inside(candidate, "base/"+name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            support[target.relative_to(candidate).as_posix()] = digest(target)
        record.update(audio_sha256=digest(candidate/"dry.wav"), support_files=support,
            revision={"method": "Retain original PCM; crossfade only the revised phrase context",
                "base_audio_sha256": base_receipt["audio_sha256"],
                "ticks": [start_tick, end_tick], "replaced_samples": [first, last],
                "context_seconds": context_seconds, "crossfade_seconds": crossfade_seconds,
                "untouched_dry_pcm_identical": True})
        record["audio"].update(peak=float(np.max(np.abs(actual))),
                               rms=float(np.sqrt(np.mean(actual**2))))
        json_write(candidate/"receipt.json", record)
        shutil.copytree(candidate, destination)
        return record


def verify_vocals(root: Path, score: Score, *, commercial: bool = True) -> list[dict]:
    records = []
    for track in score.tracks:
        if not track.vocal:
            continue
        source = track.vocal
        record = json.loads(inside(root, source.receipt).read_text(encoding="utf-8"))
        if commercial and (record.get("evaluation_only") or record["license"].get("commercial_output_verified") is not True):
            raise ValueError("unreviewed vocal cannot be published as a commercial-ready project")
        if digest(inside(root, source.file)) != record["audio_sha256"]:
            raise ValueError("vocal audio changed after render")
        if digest(inside(root, source.ustx)) != record["ustx_sha256"]:
            raise ValueError("USTX changed; render again before publishing")
        phonemes = inside(root, (Path(source.receipt).parent/"phonemes.json").as_posix())
        if digest(phonemes) != record["phonemes_sha256"]:
            raise ValueError("phoneme inventory changed after render")
        for name, expected_hash in record.get("support_files", {}).items():
            file = inside(root, (Path(source.receipt).parent/name).as_posix())
            if digest(file) != expected_hash:
                raise ValueError("vocal revision support file changed")
        native = validate_ustx(load_ustx(inside(root, source.ustx)))
        actual = [(n.start, n.duration, n.pitch, n.lyric) for n in track.notes]
        expected = [(n["position"]/480, n["duration"]/480, n["tone"], n["lyric"]) for n in native]
        if actual != expected:
            raise ValueError("MIDI notes/lyrics disagree with rendered USTX")
        records.append({"track_id": track.id, "source": source.model_dump(), **record})
    return records
