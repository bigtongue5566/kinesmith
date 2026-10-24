"""Read-only, capability-aware Opusmith adapter.

Profiles are upstream JSON Schema snapshots, not a dependency on its Python internals.
Unknown score formats degrade to explicitly selected or documented master audio.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib
from typing import Any

from jsonschema import Draft202012Validator
import mido
import soundfile as sf
import yaml

from .interchange import (TempoMap, event, load_schema, new_contract, rational,
                          sha256, validate_contract)


PROFILES = ("opusmith-score-v1-v0.1.schema.json", "opusmith-score-v1-v0.2.schema.json")


def read_json(path: Path) -> Any:
    def invalid(value):
        raise ValueError(f"non-finite JSON value: {value}")
    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=invalid)


def inside(root: Path, relative: str) -> Path:
    """Portable containment check, including Windows paths when running on POSIX."""
    if not isinstance(relative, str) or not relative:
        raise ValueError("expected project-relative path")
    portable = relative.replace("\\", "/")
    if portable.startswith("/") or ":" in portable or ".." in portable.split("/"):
        raise ValueError(f"project path escapes root: {relative}")
    result = (root / portable).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f"project symlink escapes root: {relative}")
    return result


def _source(path: Path, *, root: Path | None = None, **metadata) -> dict:
    result = {"tool": "opusmith", "path": str(path.resolve()), "sha256": sha256(path), **metadata}
    if root and path.resolve().is_relative_to(root.resolve()):
        result["relative_path"] = path.resolve().relative_to(root.resolve()).as_posix()
    return result


def _audio(path: Path, *, role: str, offset: Any, root: Path | None = None,
           track_id: str | None = None) -> dict:
    info = sf.info(str(path))
    record = {"path": str(path.resolve()), "sha256": sha256(path), "role": role,
              "offset_seconds": float(rational(offset)), "measured": True,
              "duration_seconds": float(rational(info.frames) / info.samplerate),
              "sample_rate": info.samplerate, "samples": info.frames, "channels": info.channels}
    if root and path.resolve().is_relative_to(root.resolve()):
        record["relative_path"] = path.resolve().relative_to(root.resolve()).as_posix()
    if track_id:
        record["track_id"] = track_id
    return record


def _profile(score: dict) -> tuple[str | None, str | None]:
    errors = []
    for name in PROFILES:
        validator = Draft202012Validator(load_schema(name))
        failures = sorted(validator.iter_errors(score), key=lambda e: str(e.absolute_path))
        if not failures:
            return name, None
        errors.append(f"{name}: {failures[0].message}")
    return None, "; ".join(errors)


def _semantic_score(score: dict):
    length = rational(score["length_beats"])
    meter = score.get("meter", [4, 4])
    if not 1 <= meter[0] <= 32 or meter[1] not in (1, 2, 4, 8, 16, 32):
        raise ValueError("invalid score meter")
    last = rational(0)
    for section in score["sections"]:
        start, end = rational(section["start"]), rational(section["end"])
        if start < last or end <= start or end > length:
            raise ValueError("score sections overlap or exceed music duration")
        last = end
    ids = [t["id"] for t in score["tracks"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate score track id")
    for track in score["tracks"]:
        for note in track.get("notes", []):
            if rational(note["start"]) + rational(note["duration"]) > length + rational("0.0000001"):
                raise ValueError(f"note outside score: {track['id']}")
        for automation in track.get("automation", []):
            beats = [p[0] for p in automation["points"]]
            if beats != sorted(set(beats)) or beats[0] < 0 or beats[-1] > float(length):
                raise ValueError("invalid score automation times")
        if any(rational(item["beat"]) > length for key in ("controls", "bends")
               for item in track.get(key, [])):
            raise ValueError("score expression outside music duration")


def _software_version(root: Path) -> str | None:
    candidate = root / "rebuild" / "pyproject.toml"
    if candidate.is_file():
        with candidate.open("rb") as handle:
            metadata = tomllib.load(handle).get("project", {})
        if metadata.get("name") == "opusmith" and isinstance(metadata.get("version"), str):
            return metadata["version"]
    return None


def _finish(value: dict, musical=None, tail=None, offset=0) -> dict:
    offset = rational(offset)
    master = next((a for a in value["audio"] if a["role"] == "master"), None)
    audio_seconds = master["duration_seconds"] if master else None
    end = max([0, *(e["end_seconds"] for e in value["events"])])
    if master:
        # Keep effects tails, even when no note/section remains active.
        end = max(end, float(offset + rational(master["samples"]) / master["sample_rate"]))
    elif musical is not None:
        end = max(end, float(offset + musical + (tail or 0)))
    value["duration"] = {"musical_seconds": float(musical) if musical is not None else None,
                         "audio_seconds": audio_seconds, "timeline_seconds": end,
                         "offset_seconds": float(offset),
                         "declared_tail_seconds": float(tail) if tail is not None else None,
                         "audio_measured": bool(master)}
    value["capabilities"] = sorted(set(value["capabilities"]))
    return validate_contract(value)


def _score_events(value: dict, score: dict, fps, offset):
    tempo = TempoMap([{"beat": 0, "bpm": score["bpm"]}])
    value["tempo_map"] = tempo.export()
    meter = score.get("meter", [4, 4])
    value["meter_map"] = [{"beat": 0, "numerator": meter[0], "denominator": meter[1]}]
    value["capabilities"] += ["score", "tempo", "meter", "sections", "notes", "velocity"]
    for i, section in enumerate(score["sections"]):
        value["events"].append(event("section", offset + tempo.seconds(section["start"]),
            offset + tempo.seconds(section["end"]), fps, id=f"section-{i}", name=section["name"],
            intent=section.get("intent", ""), start_beat=section["start"], end_beat=section["end"]))
    for track in score["tracks"]:
        for i, note in enumerate(track.get("notes", [])):
            start = rational(note["start"])
            end = start + rational(note["duration"])
            fields = {"id": f"{track['id']}-note-{i}", "track_id": track["id"],
                      "track_name": track["name"], "pitch": note["pitch"],
                      "velocity": note.get("velocity", 96), "start_beat": float(start),
                      "end_beat": float(end)}
            item = event("note", offset + tempo.seconds(start), offset + tempo.seconds(end), fps, **fields)
            value["events"].append(item)
            if note.get("lyric"):
                value["lyrics"].append({**item, "kind": "lyric", "text": note["lyric"],
                                         "timing_precision": "score-note"})
                value["capabilities"].append("note-timed-lyrics")
        for lane in track.get("automation", []):
            value["capabilities"].append("automation")
            for beat, amount in lane["points"]:
                at = offset + tempo.seconds(beat)
                value["events"].append(event("automation", at, at, fps, track_id=track["id"],
                                               parameter=lane["parameter"], value=amount, start_beat=beat,
                                               end_beat=beat))
        for control in track.get("controls", []):
            at = offset + tempo.seconds(control["beat"])
            value["events"].append(event("control", at, at, fps, track_id=track["id"],
                                           number=control["number"], value=control["value"]))
        for bend in track.get("bends", []):
            at = offset + tempo.seconds(bend["beat"])
            value["events"].append(event("pitch-bend", at, at, fps, track_id=track["id"], value=bend["value"]))
    return tempo


def _vocal_records(value: dict, score: dict, root: Path, fps, offset, manifest: dict):
    for track in score["tracks"]:
        vocal = track.get("vocal")
        if not vocal:
            continue
        value["capabilities"].append("vocal-references")
        receipt_path = inside(root, vocal["receipt"])
        audio_path, ustx_path = inside(root, vocal["file"]), inside(root, vocal["ustx"])
        if not receipt_path.is_file():
            value["warnings"].append(f"{track['id']}：人聲收據不存在；只使用 Score 音符時間。")
            continue
        receipt = read_json(receipt_path)
        _check_hash(receipt_path, root, manifest)
        value["sources"].append(_source(receipt_path, root=root, format_version=receipt.get("format_version")))
        if receipt.get("format_version") != 1:
            value["warnings"].append(f"{track['id']}：未知人聲收據格式；未讀取其授權／時序欄位。")
            continue
        license_record = receipt.get("license", {})
        value["licenses"].append({"kind": "vocal", "status": "upstream-record-requires-review",
                                  "track_id": track["id"], "record": license_record,
                                  "evaluation_only": receipt.get("evaluation_only", True),
                                  "receipt_sha256": sha256(receipt_path)})
        if license_record.get("commercial_output_verified") is not True or receipt.get("evaluation_only"):
            value["warnings"].append(f"{track['id']}：上游人聲鏈尚未確認商用，需保留評估用途標示。")
        if audio_path.is_file():
            expected = receipt.get("audio_sha256")
            if expected and sha256(audio_path) != expected:
                raise ValueError(f"vocal audio checksum mismatch: {audio_path}")
            _check_hash(audio_path, root, manifest)
            value["audio"].append(_audio(audio_path, role="vocal", offset=offset, root=root, track_id=track["id"]))
            value["capabilities"].append("vocal-audio")
        if ustx_path.is_file():
            expected = receipt.get("ustx_sha256")
            if expected and sha256(ustx_path) != expected:
                raise ValueError(f"vocal USTX checksum mismatch: {ustx_path}")
            _check_hash(ustx_path, root, manifest)
            value["sources"].append(_source(ustx_path, root=root))
            value["capabilities"].append("ustx")
        phonemes = receipt_path.parent / "phonemes.json"
        if phonemes.is_file():
            expected = receipt.get("phonemes_sha256")
            if expected and sha256(phonemes) != expected:
                raise ValueError("phoneme inventory checksum mismatch")
            value["sources"].append(_source(phonemes, root=root))
            value["capabilities"].append("phoneme-inventory")
            # v0.2.0's inventory contains alias/error flags, not onset/offset timings.
            value["warnings"].append(f"{track['id']}：phonemes.json 僅有音素名稱清單，沒有音素起訖時間；字幕採音符時間。")


def _check_hash(path: Path, root: Path, manifest: dict):
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    expected = manifest.get("sha256", {}).get(relative)
    if expected and sha256(path) != expected:
        raise ValueError(f"snapshot checksum mismatch: {relative}")


def load_opusmith(path: str | Path, *, fps: Any = "30", offset_seconds: Any = 0,
                  audio: str | Path | None = None, version: str | None = None) -> dict:
    """Read an Opusmith project, immutable version, Score JSON, MIDI, or USTX.

    version selects versions/vNNN; None follows the documented CURRENT.json.
    Unknown JSON schemas produce an explicit audio-only result with warnings.
    No Opusmith module is imported and no input/source file is modified.
    """
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_file() and path.suffix.lower() in (".mid", ".midi"):
        return load_midi(path, fps=fps, offset_seconds=offset_seconds, audio=audio)
    if path.is_file() and path.suffix.lower() == ".ustx":
        return load_ustx(path, fps=fps, offset_seconds=offset_seconds, audio=audio)
    offset, fps = rational(offset_seconds), rational(fps)
    value = new_contract(mode="music-first", fps=fps)
    root = path if path.is_dir() else path.parent
    project_version, software_version, metadata, manifest = None, None, {}, {}
    trusted_project = True
    if path.is_dir():
        if (path / "project.json").is_file():
            metadata = read_json(path / "project.json")
            value["sources"].append(_source(path / "project.json", root=path,
                                           format_version=metadata.get("format_version")))
            trusted_project = type(metadata.get("format_version")) is int and metadata["format_version"] == 1
            if not trusted_project:
                value["warnings"].append(f"未知 Opusmith project format_version={metadata.get('format_version')!r}；不解讀 CURRENT 或音樂欄位。")
        if trusted_project:
            if version:
                if not re.fullmatch(r"v[0-9]+", version):
                    raise ValueError("version must be a documented vNNN snapshot id")
                root, project_version = inside(path, f"versions/{version}"), version
            elif (path / "CURRENT.json").is_file():
                current = read_json(path / "CURRENT.json")
                if not re.fullmatch(r"v[0-9]+", str(current.get("version", ""))):
                    raise ValueError("invalid CURRENT version id")
                expected = f"versions/{current['version']}"
                if current.get("path") != expected:
                    raise ValueError("CURRENT path does not match its documented version")
                root, project_version = inside(path, expected), current["version"]
                value["sources"].append(_source(path / "CURRENT.json", root=path))
            if not root.is_dir():
                raise FileNotFoundError(f"Opusmith version directory missing: {root}")
            software_version = _software_version(root)
        score_path = root / "score.json"
    else:
        score_path = path
    if trusted_project and (root / "version.json").is_file():
        manifest = read_json(root / "version.json")
        if manifest.get("status") != "complete":
            raise ValueError("cannot synchronize an incomplete or failed Opusmith snapshot")
        value["sources"].append(_source(root / "version.json", root=root,
                                       project_version=project_version))
    master = Path(audio).resolve() if audio else None
    if master is None and trusted_project:
        # These are documented v1 render outputs, not arbitrary future field guesses.
        for name in ("audio/master.wav", "audio/master.flac", "audio/master.mp3"):
            candidate = inside(root, name)
            if candidate.is_file():
                master = candidate
                break
    if master:
        if master.is_relative_to(root):
            _check_hash(master, root, manifest)
        value["audio"].append(_audio(master, role="master", offset=offset, root=root))
        value["capabilities"].append("master-audio")
    score, profile = None, None
    if trusted_project and score_path.is_file():
        score = read_json(score_path)
        if not isinstance(score, dict):
            raise ValueError("Opusmith Score must be a JSON object")
        profile, failure = _profile(score)
        value["sources"].append(_source(score_path, root=root,
            format_version=score.get("format_version"), project_version=project_version,
            software_version=software_version, schema_profile=profile))
        _check_hash(score_path, root, manifest)
        if profile is None:
            value["warnings"].append(f"Score Schema 不相容；安全降級為音訊。{failure}")
            score = None
    elif trusted_project:
        value["warnings"].append("沒有可讀取的 score.json；僅使用可用音訊。")
    if score is None:
        if not master:
            value["warnings"].append("沒有可驗證的同步事件或音訊；請明確提供音訊／MIDI／已支援 Schema。")
        return _finish(value, offset=offset)
    try:
        _semantic_score(score)
    except ValueError as exc:
        value["warnings"].append(f"Score 語意驗證失敗；安全降級為音訊：{exc}")
        return _finish(value, offset=offset)
    tempo = _score_events(value, score, fps, offset)
    _vocal_records(value, score, root, fps, offset, manifest)
    midi = inside(root, "multitrack.mid")
    if midi.is_file():
        _check_hash(midi, root, manifest)
        value["sources"].append(_source(midi, root=root))
        value["capabilities"].append("midi-reference")
    stems = inside(root, "audio/stems")
    if stems.is_dir():
        for stem in sorted(stems.iterdir()):
            if stem.suffix.lower() in (".wav", ".flac", ".mp3") and stem.is_file():
                if not stem.resolve().is_relative_to(root.resolve()):
                    raise ValueError("stem symlink escapes project")
                _check_hash(stem, root, manifest)
                value["audio"].append(_audio(stem, role="stem", offset=offset, root=root, track_id=stem.stem))
        value["capabilities"].append("stems")
    asset_file = inside(root, "assets.json")
    if asset_file.is_file():
        _check_hash(asset_file, root, manifest)
        value["sources"].append(_source(asset_file, root=root))
        value["licenses"].append({"kind": "asset-ledger", "status": "upstream-record-requires-review",
                                  "records": read_json(asset_file), "sha256": sha256(asset_file)})
    value["warnings"].append("音符／歌詞時間來自樂譜，並非實際演唱 onset 或音素的量測；授權帳本仍需依用途核對。")
    return _finish(value, musical=tempo.seconds(score["length_beats"]),
                   tail=rational(score.get("tail_seconds", 3)), offset=offset)


def load_midi(path: str | Path, *, fps="30", offset_seconds=0, audio=None) -> dict:
    """Read standard synchronous MIDI including tempo changes, notes and lyric events."""
    path, fps, offset = Path(path).resolve(), rational(fps), rational(offset_seconds)
    try:
        midi = mido.MidiFile(str(path), charset="utf-8")
    except UnicodeDecodeError:
        midi = mido.MidiFile(str(path), charset="latin-1")
    if midi.type == 2 or midi.ticks_per_beat <= 0:
        raise ValueError("MIDI needs synchronous type 0/1 and positive PPQ; SMPTE/type 2 is unsupported")
    value = new_contract(mode="music-first", fps=fps, source=_source(path))
    # The Standard MIDI defaults are 120 BPM and 4/4 until explicit messages.
    tempos, meters, records, length = {0: 500000}, {0: (4, 4)}, [], 0
    explicit_tempos = set()
    for ti, track in enumerate(midi.tracks):
        tick, name = 0, f"track-{ti}"
        for msg in track:
            tick += msg.time
            length = max(length, tick)
            if msg.type == "set_tempo":
                if msg.tempo <= 0:
                    raise ValueError("MIDI tempo must be positive")
                if tick in explicit_tempos and tempos[tick] != msg.tempo:
                    raise ValueError("conflicting simultaneous MIDI tempo messages")
                tempos[tick] = msg.tempo
                explicit_tempos.add(tick)
            elif msg.type == "time_signature":
                meters[tick] = (msg.numerator, msg.denominator)
            elif msg.type == "track_name":
                name = msg.name
            records.append((tick, ti, name, msg))
    tempo = TempoMap([{"beat": str(rational(t) / midi.ticks_per_beat),
                       "bpm": str(rational(60000000) / micro)} for t, micro in sorted(tempos.items())])
    value["tempo_map"] = tempo.export()
    value["meter_map"] = [{"beat": float(rational(t) / midi.ticks_per_beat),
                           "numerator": sig[0], "denominator": sig[1]} for t, sig in sorted(meters.items())]
    active, lyrics = {}, []
    for tick, ti, name, msg in sorted(records, key=lambda x: (x[0], x[1])):
        beat = rational(tick) / midi.ticks_per_beat
        at = offset + tempo.seconds(beat)
        track_id = f"midi-{ti}"
        if msg.type == "note_on" and msg.velocity > 0:
            key = (ti, msg.channel, msg.note)
            if key in active:
                raise ValueError("overlapping same-pitch MIDI voices are ambiguous")
            active[key] = (beat, msg.velocity)
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            key = (ti, msg.channel, msg.note)
            if key not in active:
                continue
            start, velocity = active.pop(key)
            value["events"].append(event("note", offset + tempo.seconds(start), at, fps,
                track_id=track_id, track_name=name, pitch=msg.note, velocity=velocity,
                start_beat=float(start), end_beat=float(beat)))
        elif msg.type == "lyrics":
            lyrics.append((track_id, msg.text, beat))
        elif msg.type in ("marker", "cue_marker"):
            value["events"].append(event("marker", at, at, fps, name=msg.text))
        elif msg.type == "control_change":
            value["events"].append(event("control", at, at, fps, track_id=track_id,
                number=msg.control, value=msg.value))
    if active:
        value["warnings"].append("MIDI 有未結束音符；未推測其時長。")
    for track_id, text, beat in lyrics:
        matching = [e for e in value["events"] if e["kind"] == "note" and e.get("track_id") == track_id
                    and e["start_beat"] == float(beat)]
        if matching:
            note = min(matching, key=lambda e: e["end_seconds"])
            value["lyrics"].append({**note, "kind": "lyric", "text": text, "timing_precision": "midi-note"})
        else:
            value["warnings"].append(f"MIDI 歌詞 {text!r} 沒有同時開始的音符，未猜測字幕結束時間。")
    value["capabilities"] = ["midi", "tempo", "tempo-map", "meter", "notes", "velocity"]
    if value["lyrics"]:
        value["capabilities"].append("note-timed-lyrics")
    if audio:
        value["audio"].append(_audio(Path(audio).resolve(), role="master", offset=offset))
        value["capabilities"].append("master-audio")
    return _finish(value, musical=tempo.seconds(rational(length) / midi.ticks_per_beat), offset=offset)


def load_ustx(path: str | Path, *, fps="30", offset_seconds=0, audio=None) -> dict:
    """Read the documented OpenUtau 0.10 note and tempo structure without rendering vocals."""
    path, fps, offset = Path(path).resolve(), rational(fps), rational(offset_seconds)
    with path.open(encoding="utf-8-sig") as handle:
        project = yaml.safe_load(handle)
    value = new_contract(mode="music-first", fps=fps, source=_source(path))
    if str(project.get("ustx_version")) != "0.10":
        value["warnings"].append("未知 USTX 版本；只使用明確提供的音訊，不猜測 tick 與音符結構。")
        if audio:
            value["audio"].append(_audio(Path(audio).resolve(), role="master", offset=offset))
            value["capabilities"].append("master-audio")
        return _finish(value, offset=offset)
    ppq = rational(project.get("resolution", 480))
    if ppq <= 0:
        raise ValueError("USTX resolution must be positive")
    tempo = TempoMap([{"beat": str(rational(p["position"]) / ppq), "bpm": p["bpm"]}
                      for p in project["tempos"]])
    value["tempo_map"] = tempo.export()
    last, tracks = rational(0), project.get("tracks", [])
    for part in project.get("voice_parts", []):
        ti = part.get("track_no", 0)
        if not isinstance(ti, int) or not 0 <= ti < len(tracks):
            raise ValueError("USTX track reference outside tracks")
        part_start = rational(part.get("position", 0))
        last = max(last, part_start + rational(part["duration"]))
        for i, note in enumerate(part.get("notes", [])):
            start = (part_start + rational(note["position"])) / ppq
            end = start + rational(note["duration"]) / ppq
            if start < 0 or end <= start or not 0 <= note["tone"] <= 127:
                raise ValueError("invalid USTX note timing/pitch")
            item = event("note", offset + tempo.seconds(start), offset + tempo.seconds(end), fps,
                         id=f"ustx-{ti}-{len(value['events'])}-{i}", track_id=f"ustx-{ti}",
                         track_name=tracks[ti].get("track_name", f"track-{ti}"), pitch=note["tone"],
                         start_beat=float(start), end_beat=float(end))
            value["events"].append(item)
            if note.get("lyric"):
                value["lyrics"].append({**item, "kind": "lyric", "text": note["lyric"],
                                         "timing_precision": "ustx-note"})
    # OpenUtau meter positions are bar counts. Convert each with the PREVIOUS meter.
    previous_bar, previous_beat, previous_sig = 0, rational(0), (4, 4)
    for sig in project.get("time_signatures", []):
        bar = sig["bar_position"]
        if bar < previous_bar:
            raise ValueError("USTX meter changes must be ordered")
        beat = previous_beat + (bar - previous_bar) * previous_sig[0] * 4 / rational(previous_sig[1])
        numerator, denominator = sig["beat_per_bar"], sig["beat_unit"]
        if not isinstance(numerator, int) or numerator < 1 or denominator not in (1, 2, 4, 8, 16, 32, 64):
            raise ValueError("invalid USTX meter")
        value["meter_map"].append({"beat": float(beat), "numerator": numerator, "denominator": denominator})
        previous_bar, previous_beat, previous_sig = bar, beat, (numerator, denominator)
    value["capabilities"] = ["ustx", "notes", "tempo", "tempo-map", "note-timed-lyrics"]
    if value["meter_map"]:
        value["capabilities"].append("meter")
    value["warnings"].append("USTX 音符時間不是精確演唱或音素起訖；沒有執行聲庫或額外生成模型。")
    if audio:
        value["audio"].append(_audio(Path(audio).resolve(), role="master", offset=offset))
        value["capabilities"].append("master-audio")
    return _finish(value, musical=tempo.seconds(last / ppq), offset=offset)
