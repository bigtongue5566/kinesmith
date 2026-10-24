"""Portable audio/visual handoffs, rational time conversion and bounded revisions.

The contract is data, not a plugin runtime. No operation writes to an Opusmith project.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


CONTRACT_VERSION = "1.0"


def rational(value: Any) -> Fraction:
    """Decimal numbers and frame rates stay rational until JSON serialization."""
    if isinstance(value, bool):
        raise ValueError("boolean is not a time value")
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"invalid finite rational: {value!r}") from exc


def frame_at(seconds: Any, fps: Any = "30", *, rounding: str = "ceil") -> int:
    """ceil is the first frame sample at/after an event; end frames are exclusive."""
    rate = rational(fps)
    if rate <= 0:
        raise ValueError("fps must be positive")
    value = rational(seconds) * rate
    if rounding == "ceil":
        return math.ceil(value)
    if rounding == "floor":
        return math.floor(value)
    if rounding == "nearest":
        return math.floor(value + Fraction(1, 2))
    raise ValueError("rounding must be ceil, floor, or nearest")


def sha256(path: str | Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def load_schema(name: str) -> dict:
    # Plugin source and installed wheels both carry the exact same schema snapshots.
    candidates = [Path(__file__).parent / "schemas" / name,
                  Path(__file__).resolve().parents[2] / "schemas" / name]
    for candidate in candidates:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8-sig"))
    raise FileNotFoundError(f"schema not packaged: {name}")


class TempoMap:
    """Quarter-note beat to seconds, with piecewise constant BPM.

    A tempo point has {'beat': decimal, 'bpm': decimal}. MIDI/USTX are converted
    to this explicit representation by their own adapters, never guessed fields.
    """
    def __init__(self, points: list[dict]):
        if not points:
            raise ValueError("tempo map needs a tempo at beat zero")
        self.points: list[tuple[Fraction, Fraction]] = []
        for point in points:
            beat, bpm = rational(point["beat"]), rational(point["bpm"])
            if beat < 0 or bpm <= 0:
                raise ValueError("tempo beat must be nonnegative and BPM positive")
            if self.points and beat <= self.points[-1][0]:
                raise ValueError("tempo points must be ordered and unique")
            self.points.append((beat, bpm))
        if self.points[0][0] != 0:
            raise ValueError("first tempo must be at beat zero")

    def seconds(self, beat: Any) -> Fraction:
        target = rational(beat)
        if target < 0:
            raise ValueError("beat must be nonnegative")
        elapsed = Fraction(0)
        for i, (start, bpm) in enumerate(self.points):
            end = self.points[i + 1][0] if i + 1 < len(self.points) else target
            elapsed += max(0, min(target, end) - start) * 60 / bpm
            if target <= end:
                break
        return elapsed

    def export(self) -> list[dict]:
        return [{"beat": float(beat), "bpm": float(bpm)} for beat, bpm in self.points]


def event(kind: str, start: Any, end: Any, fps: Any, **fields) -> dict:
    start, end = rational(start), rational(end)
    if end < start:
        raise ValueError("event end precedes start")
    return {"kind": kind, "start_seconds": float(start), "end_seconds": float(end),
            "start_frame": frame_at(start, fps), "end_frame": frame_at(end, fps), **fields}


def validate_contract(value: dict) -> dict:
    # JSON Schema number checks alone don't reject Python NaN/Infinity values.
    json.dumps(value, allow_nan=False)
    version = value.get("contract_version")
    if version != CONTRACT_VERSION:
        raise ValueError(f"unsupported AV contract version {version!r}; supported: {CONTRACT_VERSION}")
    Draft202012Validator(load_schema("av-contract-v1.schema.json")).validate(value)
    rate = rational(value["timebase"]["fps"])
    if rate <= 0:
        raise ValueError("fps must be positive")
    TempoMap(value["tempo_map"]) if value["tempo_map"] else None
    for item in value["events"] + value["lyrics"]:
        if item["end_seconds"] < item["start_seconds"]:
            raise ValueError("event has negative duration")
        if item["start_frame"] != frame_at(item["start_seconds"], rate):
            # Float serialization can shift an exactly integral boundary by epsilon.
            error = abs(item["start_frame"] / float(rate) - item["start_seconds"])
            if error > 1e-9:
                raise ValueError("event frame conversion mismatch")
        if item["end_frame"] < item["start_frame"]:
            raise ValueError("event has reversed frames")
        expected_end = frame_at(item["end_seconds"], rate)
        if item["end_frame"] != expected_end:
            error = abs(item["end_frame"] / float(rate) - item["end_seconds"])
            if error > 1e-9:
                raise ValueError("event end frame conversion mismatch")
    for item in value["lyrics"]:
        if item["end_seconds"] <= item["start_seconds"]:
            raise ValueError("lyric needs a positive explicit duration")
    ids = [r["id"] for r in value["requests"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate revision request id")
    return value


def new_contract(*, mode: str, fps: Any = "30", source: dict | None = None) -> dict:
    rate = rational(fps)
    if mode not in ("music-first", "visual-first", "joint") or rate <= 0:
        raise ValueError("invalid mode or fps")
    return {"contract_version": CONTRACT_VERSION, "mode": mode,
            "timebase": {"fps": str(rate), "beat_unit": "quarter-note",
                         "frame_rule": "ceil-start-ceil-end-exclusive"},
            "sources": [source] if source else [], "capabilities": [], "tempo_map": [],
            "meter_map": [], "events": [], "audio": [], "lyrics": [],
            "licenses": [], "requests": [], "links": [], "warnings": [],
            "duration": {"musical_seconds": None, "audio_seconds": None,
                         "timeline_seconds": 0, "offset_seconds": 0,
                         "declared_tail_seconds": None, "audio_measured": False}}


def write_contract(path: str | Path, value: dict) -> Path:
    validate_contract(value)
    path = Path(path)
    protected = [s["path"] for s in value["sources"]] + [a["path"] for a in value["audio"]]
    if any(path.resolve() == Path(source).resolve() for source in protected
           if not source.startswith("embedded:")):
        raise ValueError("handoff output must not overwrite an original source or audio file")
    stored = deepcopy(value)
    base = path.resolve().parent
    for source in stored["sources"] + stored["audio"]:
        # Relative references always mean relative to the containing contract.
        # External source trees stay explicit external references; an adapter's
        # earlier source-root-relative path must not masquerade as a package path.
        source.pop("relative_path", None)
        if source["path"].startswith("embedded:"):
            continue
        candidate = Path(source["path"]).resolve()
        if candidate.is_relative_to(base):
            source["relative_path"] = candidate.relative_to(base).as_posix()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never append to a music project via a handoff helper. Output is its own file.
    path.write_text(json.dumps(stored, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return path


def make_visual_request(project: str | Path | dict, *, fps: Any | None = None,
                        request: str = "請依場景情緒與指定 cue 創作配樂。",
                        music_source: dict | None = None) -> dict:
    """Turn a Kinesmith project timeline into a portable request for an installed skill.

    Scenes use start_frame/duration_frames, or explicit start/duration in seconds.
    Engine-specific editable source paths are carried as evidence, never executed here.
    """
    if isinstance(project, (str, Path)):
        path = Path(project).resolve()
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        source = {"tool": "kinesmith", "path": str(path), "sha256": sha256(path),
                  "format_version": obj.get("schema_version", obj.get("format_version")),
                  "project_version": str(obj.get("revision", obj.get("version", "working")))}
    else:
        obj = deepcopy(project)
        canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
        source = {"tool": "kinesmith", "path": "embedded:timeline",
                  "sha256": hashlib.sha256(canonical).hexdigest(),
                  "format_version": obj.get("schema_version", obj.get("format_version")),
                  "project_version": str(obj.get("revision", obj.get("version", "working")))}
    rate = rational(fps if fps is not None else obj.get("fps", 30))
    value = new_contract(mode="visual-first", fps=rate, source=source)
    for scene in obj.get("scenes", []):
        if "start_frame" in scene and "duration_frames" in scene:
            start = rational(scene["start_frame"]) / rate
            end = start + rational(scene["duration_frames"]) / rate
        elif "start" in scene and "duration" in scene:
            start, end = rational(scene["start"]), rational(scene["start"]) + rational(scene["duration"])
        else:
            raise ValueError("scene needs start_frame/duration_frames or explicit start/duration")
        value["events"].append(event("scene", start, end, rate, id=str(scene["id"]),
                                      name=scene.get("title", scene["id"]),
                                      intent=scene.get("intent", "")))
    value["capabilities"] = ["scene-cues", "revision-requests"]
    value["duration"]["timeline_seconds"] = max((e["end_seconds"] for e in value["events"]), default=0)
    value["requests"].append({"id": "music-001", "target": "music", "scope": "music",
                               "text": request, "status": "proposed"})
    if music_source:
        value["sources"].append(deepcopy(music_source))
        value["links"].append({"relation": "score-for-picture", "visual_sha256": source["sha256"],
                               "music_sha256": music_source["sha256"]})
    return validate_contract(value)


def revise_contract(value: dict, *, request_id: str, target: str, scope: str,
                    text: str, parent_sha256: str | None = None) -> dict:
    """Propose a bounded joint revision; applying music/visual changes is explicit."""
    validate_contract(value)
    if target not in ("music", "visual") or scope not in ("music", "visual", "both"):
        raise ValueError("invalid revision target/scope")
    if scope != "both" and target != scope:
        raise ValueError("revision target must be within the requested scope")
    out = deepcopy(value)
    out["mode"] = "joint"
    out["requests"].append({"id": request_id, "target": target, "scope": scope,
                            "text": text, "status": "proposed"})
    if parent_sha256:
        out["links"].append({"relation": "revision-of", "contract_sha256": parent_sha256})
    return validate_contract(out)


def _relative_source(base: Path, relative: str) -> Path:
    normalized = relative.replace("\\", "/")
    if not normalized or normalized.startswith("/") or ":" in normalized or ".." in normalized.split("/"):
        raise ValueError(f"unsafe contract-relative reference: {relative!r}")
    result = (base / normalized).resolve()
    if not result.is_relative_to(base.resolve()):
        raise ValueError(f"contract reference escapes base: {relative!r}")
    return result


def verify_sources(value: dict, *, base: str | Path | None = None) -> list[dict]:
    """Report changes without mutating, re-rendering or auto-accepting source files."""
    validate_contract(value)
    result = []
    for source in value["sources"] + value["audio"]:
        path = Path(source["path"])
        status = "embedded" if source["path"].startswith("embedded:") else "missing"
        if base is not None and source.get("relative_path") and status != "embedded":
            path = _relative_source(Path(base).resolve(), source["relative_path"])
        if path.is_file():
            status = "unchanged" if sha256(path) == source["sha256"] else "changed"
        result.append({"path": source["path"], "resolved_path": str(path), "status": status})
    return result


def rebase_contract(value: dict, base: str | Path) -> dict:
    """Explicitly relocate a portable contract after every local SHA256 matches.

    base is the directory containing the moved contract. Only declared
    relative_path references are used; no searching by filename, old absolute
    path fallback, source copying, or source mutation occurs. External refs must
    be acquired and explicitly packaged before relocation can succeed.
    """
    validate_contract(value)
    base = Path(base).resolve()
    if not base.is_dir():
        raise FileNotFoundError(base)
    out = deepcopy(value)
    for source in out["sources"] + out["audio"]:
        if source["path"].startswith("embedded:"):
            continue
        relative = source.get("relative_path")
        if not relative:
            raise ValueError(f"external source has no portable relative_path: {source['path']}")
        candidate = _relative_source(base, relative)
        if not candidate.is_file():
            raise FileNotFoundError(f"relocated source missing: {candidate}")
        if sha256(candidate) != source["sha256"]:
            raise ValueError(f"relocated source checksum mismatch: {relative}")
        source["path"] = str(candidate)
    return validate_contract(out)
