"""Portable beat-based score; one beat is a quarter note, independent of meter."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class Note(Model):
    lyric: str | None = None
    pitch: int = Field(ge=0, le=127)
    start: float = Field(ge=0)
    duration: float = Field(gt=0)
    velocity: int = Field(default=96, ge=1, le=127)
    articulation: Literal["normal", "staccato", "tenuto", "accent"] = "normal"


class Control(Model):
    beat: float = Field(ge=0)
    number: int = Field(ge=0, le=127)
    value: int = Field(ge=0, le=127)


class Bend(Model):
    beat: float = Field(ge=0)
    value: int = Field(ge=-8192, le=8191)


class Automation(Model):
    parameter: Literal["gain_db", "pan", "cutoff_hz", "lfo_hz"]
    points: list[tuple[float, float]] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_points(self):
        times = [p[0] for p in self.points]
        if times != sorted(set(times)) or times[0] < 0:
            raise ValueError("automation beats must be nonnegative, unique and ordered")
        limits = {"gain_db": (-96, 24), "pan": (-1, 1),
                  "cutoff_hz": (20, 20000), "lfo_hz": (0.01, 40)}
        lo, hi = limits[self.parameter]
        if any(not math.isfinite(v) or not lo <= v <= hi for _, v in self.points):
            raise ValueError(f"{self.parameter} values must be in [{lo}, {hi}]")
        return self


class Patch(Model):
    engine: Literal["supersaw", "pluck", "acid", "wobble", "reese", "pad", "fm",
                    "additive", "wavetable", "kick", "snare", "hat", "noise", "sample"]
    attack: float = Field(default=0.008, ge=0.001, le=10)
    decay: float = Field(default=0.2, ge=0.001, le=10)
    sustain: float = Field(default=0.55, ge=0, le=1)
    release: float = Field(default=0.25, ge=0.005, le=10)
    cutoff_hz: float = Field(default=6000, ge=20, le=20000)
    resonance: float = Field(default=0.7, ge=0.1, le=15)
    detune_cents: float = Field(default=12, ge=0, le=60)
    voices: int = Field(default=5, ge=1, le=9)
    lfo_hz: float = Field(default=2, gt=0, le=40)
    fm_ratio: float = Field(default=2, gt=0, le=16)
    fm_index: float = Field(default=2, ge=0, le=20)
    drive: float = Field(default=1, ge=0.1, le=10)
    sample: str | None = None
    root_note: int = Field(default=60, ge=0, le=127)
    wavetable: list[float] = Field(default_factory=list, max_length=65536)
    partials: list[float] = Field(default_factory=lambda: [1, 0.4, 0.2, 0.1], max_length=64)

    @model_validator(mode="after")
    def source_required(self):
        if self.engine == "sample" and not self.sample:
            raise ValueError("sample engine needs a project-relative file")
        if self.engine == "wavetable" and len(self.wavetable) < 8:
            raise ValueError("wavetable needs at least 8 cycle samples")
        return self


class Effects(Model):
    highpass_hz: float = Field(default=25, ge=0, le=10000)
    lowpass_hz: float = Field(default=18000, ge=20, le=20000)
    compressor_db: float = Field(default=-18, ge=-60, le=0)
    ratio: float = Field(default=2, ge=1, le=20)
    delay_seconds: float = Field(default=0.375, ge=0.001, le=4)
    delay_mix: float = Field(default=0, ge=0, le=0.6)
    reverb_mix: float = Field(default=0, ge=0, le=0.7)
    reverb_size: float = Field(default=0.5, ge=0, le=1)
    sidechain_from: str | None = None
    duck_db: float = Field(default=0, ge=0, le=24)
    duck_release: float = Field(default=0.18, ge=0.01, le=2)


class VocalRender(Model):
    """Frozen, aligned OpenUtau audio plus editable source and provenance."""
    file: str
    ustx: str
    receipt: str


class Track(Model):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,47}$")
    name: str = Field(min_length=1)
    role: str = "instrument"
    program: int = Field(default=0, ge=0, le=127)
    is_drum: bool = False
    gain_db: float = Field(default=-12, ge=-96, le=12)
    pan: float = Field(default=0, ge=-1, le=1)
    patch: Patch
    vocal: VocalRender | None = None
    effects: Effects = Field(default_factory=Effects)
    notes: list[Note] = Field(default_factory=list)
    controls: list[Control] = Field(default_factory=list)
    bends: list[Bend] = Field(default_factory=list)
    automation: list[Automation] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_automation(self):
        names = [a.parameter for a in self.automation]
        if len(names) != len(set(names)):
            raise ValueError("one automation lane per parameter")
        return self


class Section(Model):
    name: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    intent: str = ""


class Score(Model):
    format_version: Literal[1] = 1
    title: str = Field(min_length=1)
    bpm: float = Field(gt=0, le=400)
    key: str = "unspecified"
    meter: tuple[int, int] = (4, 4)
    length_beats: float = Field(gt=0)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    genres: list[str] = Field(default_factory=list)
    sections: list[Section] = Field(min_length=1)
    tracks: list[Track] = Field(min_length=1)
    decisions: list[str] = Field(default_factory=list)
    target_lufs: float = Field(default=-14, ge=-30, le=-6)
    ceiling_db: float = Field(default=-1, ge=-6, le=-0.3)
    tail_seconds: float = Field(default=3, ge=0.1, le=20)

    @model_validator(mode="after")
    def coherent(self):
        num, den = self.meter
        if num < 1 or num > 32 or den not in (1, 2, 4, 8, 16, 32):
            raise ValueError("invalid time signature")
        ids = [t.id for t in self.tracks]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate track id")
        if len([t for t in self.tracks if not t.is_drum]) > 15:
            raise ValueError("SMF type 1 supports 15 independent melodic channels")
        previous = 0.0
        for s in self.sections:
            if s.start < previous or s.end <= s.start or s.end > self.length_beats:
                raise ValueError("sections must be ordered, nonoverlapping and within score")
            previous = s.end
        for t in self.tracks:
            if t.effects.sidechain_from is not None:
                if t.effects.sidechain_from not in ids or t.effects.sidechain_from == t.id:
                    raise ValueError("sidechain source must be another track")
            if any(n.start + n.duration > self.length_beats + 1e-7 for n in t.notes):
                raise ValueError(f"{t.id}: note outside score")
            times = [c.beat for c in t.controls] + [b.beat for b in t.bends]
            times += [p[0] for a in t.automation for p in a.points]
            if any(b > self.length_beats for b in times):
                raise ValueError(f"{t.id}: expression outside score")
        return self

    @property
    def seconds(self) -> float:
        return self.length_beats * 60 / self.bpm

    def save(self, path: Path):
        path = Path(path)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Score:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


def inside(root: Path, relative: str) -> Path:
    """Disallow absolute paths, drive/UNC paths, traversal and symlink escapes."""
    if not relative or Path(relative).is_absolute() or re.match(r"^[a-zA-Z]:", relative):
        raise ValueError("expected a project-relative path")
    normalized = relative.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized or ".." in normalized.split("/"):
        raise ValueError("path traversal")
    result = (root / normalized).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("path escapes project")
    return result


def json_write(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
