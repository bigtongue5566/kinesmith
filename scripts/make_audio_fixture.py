"""Create an original deterministic click/tone fixture, never a synthetic vocal claim."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def make_audio_fixture(path: str | Path, duration_seconds: float = 12.0, bpm: float = 120.0) -> dict:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if duration_seconds <= 0 or bpm <= 0:
        raise ValueError("duration_seconds 與 bpm 必須大於零")
    sr = 48000
    t = np.arange(round(sr * duration_seconds)) / sr
    audio = np.zeros_like(t)
    beat_times = np.arange(0.25, max(0.25, duration_seconds - 0.5), 60 / bpm)
    for index, onset in enumerate(beat_times):
        start = round(onset * sr)
        count = min(round(0.32 * sr), len(audio) - start)
        local = np.arange(count) / sr
        freq = [130.8128, 164.8138, 195.9977, 261.6256][index % 4]
        tone = np.sin(2 * np.pi * freq * local) * np.exp(-local * 14)
        click = np.sin(2 * np.pi * (900 * local + 1300 * local**2)) * np.exp(-local * 100)
        audio[start:start + count] += 0.33 * tone + 0.18 * click
    # Small, deliberately measurable release tail after the last beat.
    if beat_times.size:
        last = float(beat_times[-1])
        tail_t = np.maximum(t - last, 0)
        audio += (t >= last) * 0.05 * np.sin(2 * np.pi * 261.6256 * tail_t) * np.exp(-tail_t * 3)
    wavfile.write(path, sr, np.round(np.clip(audio, -1, 1) * 32767).astype(np.int16))
    metadata = {
        "description": "Kinesmith 原創確定性電子音色／節拍測試音訊；不是人聲或真人樂器錄音。",
        "license": "CC0-1.0", "sample_rate": sr, "bpm": bpm,
        "duration_seconds": len(audio) / sr, "beat_times_seconds": beat_times.tolist(),
        "timing_precision": "authored", "musical_body_end_seconds": float(beat_times[-1]) if beat_times.size else 0,
    }
    path.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="產生原創 Audio-Reactive 測試音訊")
    parser.add_argument("output", type=Path)
    parser.add_argument("--duration", type=float, default=12)
    parser.add_argument("--bpm", type=float, default=120)
    args = parser.parse_args()
    print(json.dumps(make_audio_fixture(args.output, args.duration, args.bpm), ensure_ascii=False, indent=2))
