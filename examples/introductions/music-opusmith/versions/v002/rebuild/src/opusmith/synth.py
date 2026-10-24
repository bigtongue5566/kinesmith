"""Deterministic offline synthesis; NumPy oscillators, SciPy resampling, JUCE filters.

No generative models or audio services. These patches are editable starting points,
not a composition engine. Users may replace this renderer with their own tools.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf
from pedalboard import LadderFilter
from scipy.signal import resample_poly

from .model import Note, Patch, Score, Track, inside


def _saw(phase: np.ndarray, delta: np.ndarray | float) -> np.ndarray:
    """PolyBLEP corrects a saw discontinuity (phase and delta in cycles)."""
    x = np.mod(phase, 1.0)
    d = np.maximum(delta, 1e-9)
    a = np.clip(x / d, 0, 1)
    b = np.clip((x - 1) / d, -1, 0)
    correction = np.where(x < d, 2*a - a*a - 1, 0)
    correction += np.where(x > 1-d, b*b + 2*b + 1, 0)
    return 2*x-1-correction


def _envelope(p: Patch, gate: float, sr: int, frames: int) -> np.ndarray:
    time = np.arange(frames) / sr
    attack = np.minimum(time / p.attack, 1)
    env = np.where(time < p.attack, attack,
                   p.sustain+(1-p.sustain)*np.exp(-5*np.maximum(time-p.attack, 0)/p.decay))
    gate_value = float(np.interp(gate, time, env))
    after = time >= gate
    env[after] = gate_value*np.maximum(0, 1-(time[after]-gate)/p.release)**2
    return env


def _step(beats: np.ndarray, points: list[tuple[float, float]], default: float) -> np.ndarray:
    if not points:
        return np.full(len(beats), default, dtype=np.float64)
    points = sorted(points)
    index = np.searchsorted([x[0] for x in points], beats, side="right")-1
    values = np.asarray([default] + [x[1] for x in points])
    return values[index+1]


def _voice(note: Note, track: Track, score: Score, sr: int, root: Path,
           rng: np.random.Generator, sample_data=None) -> np.ndarray:
    p = track.patch
    gate = note.duration*60/score.bpm*(0.55 if note.articulation == "staccato" else 1)
    # Oversampling suppresses FM/nonlinear aliases as well as oscillator residuals.
    osr = sr * 2
    count = int(np.ceil((gate+p.release)*osr))
    t = np.arange(count)/osr
    beats = note.start+t*score.bpm/60
    bend = _step(beats, [(b.beat, b.value/8192*2) for b in track.bends], 0)
    freq = 440*2**((note.pitch-69+bend)/12)
    phase = np.cumsum(freq)/osr
    env = _envelope(p, gate, osr, count)
    stereo = None
    if p.engine in ("supersaw", "pad", "reese"):
        stereo = np.zeros((count, 2))
        voices = p.voices if p.engine != "reese" else 2
        for i, cents in enumerate(np.linspace(-p.detune_cents, p.detune_cents, voices)):
            offset = rng.uniform(0, 1)
            detune = 2**(cents/1200)
            saw = _saw(phase*detune+offset, freq*detune/osr)
            if p.engine == "pad":
                saw = 0.6*saw+0.4*np.sin(2*np.pi*(phase*detune+offset))
            pan = 0 if voices == 1 else -0.75+1.5*i/(voices-1)
            stereo[:, 0] += saw*np.sqrt((1-pan)/2)/voices
            stereo[:, 1] += saw*np.sqrt((1+pan)/2)/voices
        stereo *= env[:, None]
    elif p.engine in ("pluck", "acid"):
        raw = _saw(phase, freq/osr)
        raw = (raw+0.3*np.sin(2*np.pi*phase))/1.3
    elif p.engine == "wobble":
        raw = np.sin(2*np.pi*phase + p.fm_index*np.sin(2*np.pi*phase*p.fm_ratio))
        raw = 0.65*raw+0.35*_saw(phase*1.003, freq*1.003/osr)
    elif p.engine == "fm":
        index = p.fm_index*np.exp(-t/max(p.decay, .001))
        raw = np.sin(2*np.pi*phase+index*np.sin(2*np.pi*phase*p.fm_ratio))
    elif p.engine == "additive":
        raw = np.zeros(count)
        for h, amplitude in enumerate(p.partials, 1):
            raw += amplitude*np.sin(2*np.pi*phase*h)*(freq*h < osr*.45)
        raw /= max(sum(abs(a) for a in p.partials), 1)
    elif p.engine == "wavetable":
        positions = np.mod(phase, 1)*len(p.wavetable)
        table = np.asarray(p.wavetable+[p.wavetable[0]])
        raw = np.interp(positions, np.arange(len(table)), table)
    elif p.engine == "kick":
        kick_freq = 45+130*np.exp(-t/.022)
        raw = np.sin(2*np.pi*np.cumsum(kick_freq)/osr)*np.exp(-t/.18)
        raw += rng.normal(0, .25, count)*np.exp(-t/.004)
    elif p.engine == "snare":
        noise = rng.normal(0, .6, count)
        noise = np.r_[0, np.diff(noise)]/1.4
        raw = noise*np.exp(-t/.075)+.55*np.sin(2*np.pi*185*t)*np.exp(-t/.04)
    elif p.engine == "hat":
        noise = rng.normal(0, .4, count)
        raw = np.r_[0, np.diff(noise)]*np.exp(-t/.045)
    elif p.engine == "noise":
        raw = rng.normal(0, .24, count)
    elif p.engine == "sample":
        if sample_data is None:
            sample_data = sf.read(inside(root, p.sample), dtype="float32", always_2d=True)
        data, source_sr = sample_data
        if np.any(bend != 0):
            raise ValueError("sample pitch bends need resampling in source.py")
        ratio = 2**((note.pitch-p.root_note)/12)
        source_positions = t*source_sr*ratio
        stereo = np.stack([np.interp(source_positions, np.arange(len(data)), data[:, c],
                                    left=0, right=0) for c in range(min(data.shape[1], 2))], axis=1)
        if stereo.shape[1] == 1:
            stereo = np.repeat(stereo, 2, axis=1)
        stereo *= env[:, None]
    else:
        raise ValueError(f"unsupported engine: {p.engine}")
    if stereo is None:
        if p.engine == "pluck":
            env *= np.exp(-t/max(.08, p.decay*2))
        raw = np.tanh(raw*p.drive)/max(1, p.drive*.6)
        stereo = np.repeat((raw*env)[:, None], 2, axis=1)
    stereo = resample_poly(stereo, 1, 2, axis=0).astype(np.float32)
    velocity = min(127, note.velocity+(10 if note.articulation == "accent" else 0))
    stereo *= (velocity/127)**1.5
    return stereo


def lane(track: Track, name: str, beats: np.ndarray, default: float) -> np.ndarray:
    automation = next((a for a in track.automation if a.parameter == name), None)
    if automation:
        return np.interp(beats, [p[0] for p in automation.points], [p[1] for p in automation.points])
    return np.full(len(beats), default)


def render_track(track: Track, score: Score, sr: int, root: Path) -> np.ndarray:
    frames = int(np.ceil((score.seconds+score.tail_seconds)*sr))
    out = np.zeros((frames, 2), dtype=np.float32)
    # Seed by track ID, not array order: untouched stems remain identical after an edit.
    seed = int.from_bytes(hashlib.sha256(track.id.encode()).digest()[:4], "little")
    rng = np.random.default_rng((score.seed+seed) % 2**32)
    sample_data = None
    if track.vocal:
        data, source_sr = sf.read(inside(root, track.vocal.file), dtype="float32", always_2d=True)
        if data.shape[1] not in (1, 2) or not np.isfinite(data).all():
            raise ValueError("vocal audio must be finite mono/stereo")
        if source_sr != sr:
            import math
            divisor = math.gcd(source_sr, sr)
            data = resample_poly(data, sr//divisor, source_sr//divisor, axis=0)
        if len(data) > frames:
            raise ValueError("vocal extends beyond score and tail")
        out[:len(data)] = data
    elif track.patch.engine == "sample":
        sample_data = sf.read(inside(root, track.patch.sample), dtype="float32", always_2d=True)
    for note in ([] if track.vocal else sorted(track.notes, key=lambda n: (n.start, n.pitch))):
        voice = _voice(note, track, score, sr, root, rng, sample_data)
        start = round(note.start*60/score.bpm*sr)
        count = min(len(voice), frames-start)
        out[start:start+count] += voice[:count]
    p = track.patch
    if not track.vocal and p.engine not in ("kick", "snare", "hat", "sample"):
        filt = LadderFilter(mode=LadderFilter.LPF24, cutoff_hz=min(p.cutoff_hz, sr*.45),
                            resonance=min(.95, p.resonance/15), drive=p.drive)
        dynamic = p.engine in ("wobble", "acid") or any(
            a.parameter in ("cutoff_hz", "lfo_hz") for a in track.automation)
        if dynamic:
            lfo_phase = 0.0
            onsets = np.array(sorted(n.start*60/score.bpm for n in track.notes))
            for start in range(0, frames, 1024):
                stop = min(frames, start+1024)
                beat = (start+stop)/2/sr*score.bpm/60
                cutoff = lane(track, "cutoff_hz", np.array([beat]), p.cutoff_hz)[0]
                lfo = lane(track, "lfo_hz", np.array([beat]), p.lfo_hz)[0]
                block_seconds = (stop-start)/sr
                modulation = .5+.5*np.sin(2*np.pi*(lfo_phase+lfo*block_seconds/2))
                lfo_phase += lfo*block_seconds
                if p.engine == "wobble":
                    cutoff *= .15+.85*modulation
                elif p.engine == "acid":
                    seconds = (start+stop)/2/sr
                    index = np.searchsorted(onsets, seconds, side="right")-1
                    elapsed = seconds-onsets[index] if index >= 0 else 1000
                    filter_env = np.exp(-elapsed/max(p.decay, .001))
                    cutoff *= (.12+.88*filter_env)*(.85+.15*modulation)
                filt.cutoff_hz = float(np.clip(cutoff, 30, sr*.45))
                out[start:stop] = filt(out[start:stop].T, sr, reset=start == 0).T
        else:
            out = filt(out.T, sr).T.copy()
    # CC11 = expression; CC1 = amplitude modulation depth; CC7 = channel volume.
    # Other CCs are preserved in SMF but intentionally do not invent acoustic behavior.
    for start in range(0, frames, 65536):
        stop = min(frames, start+65536)
        beats = np.arange(start, stop)/sr*score.bpm/60
        expression = _step(beats, [(c.beat, c.value/127) for c in track.controls
                                   if c.number == 11], 1)
        expression *= _step(beats, [(c.beat, c.value/127) for c in track.controls
                                   if c.number == 7], 1)
        modulation = _step(beats, [(c.beat, c.value/127) for c in track.controls
                                  if c.number == 1], 0)
        expression *= 1-modulation*.12*(1+np.sin(2*np.pi*5*np.arange(start, stop)/sr))
        gain = 10**(lane(track, "gain_db", beats, track.gain_db)/20)*expression
        pan = lane(track, "pan", beats, track.pan)
        out[start:stop, 0] *= gain*np.sqrt(1-pan)
        out[start:stop, 1] *= gain*np.sqrt(1+pan)
    return out
