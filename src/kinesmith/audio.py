"""Deterministic, local audio features. Onsets are estimates, never vocal alignment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import imageio_ffmpeg
import numpy as np
from scipy import signal


def _ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def decode_audio(path: str | Path, sample_rate: int = 22050) -> np.ndarray:
    """Decode the first audio stream with FFmpeg; no implicit loudness normalization."""
    path = Path(path).resolve(strict=True)
    if not 8000 <= sample_rate <= 192000:
        raise ValueError("sample_rate 必須介於 8000 與 192000")
    result = subprocess.run(
        [_ffmpeg(), "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0",
         "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "f32le", "pipe:1"],
        capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError(f"無法解碼音訊 {path.name}: {result.stderr.decode(errors='replace').strip()}")
    samples = np.frombuffer(result.stdout, dtype="<f4").copy()
    if not samples.size:
        raise ValueError(f"音訊沒有可分析的樣本: {path.name}")
    if not np.isfinite(samples).all():
        raise ValueError("音訊含有 NaN 或無限值")
    return samples


def _normalize(values: np.ndarray) -> np.ndarray:
    reference = float(np.percentile(values, 95)) if values.size else 0.0
    # Sparse click tracks need the maximum as reference, silence must stay zero.
    if reference <= 1e-10:
        reference = float(np.max(values, initial=0.0))
    return np.clip(values / reference, 0, 1) if reference > 1e-10 else np.zeros_like(values)


def analyze_audio(path: str | Path, output: str | Path | None = None) -> dict:
    """Return JSON-serializable RMS, band energy and estimated spectral-flux onsets.

    Timestamps refer to the decoded file, before any timeline offset. 22050 Hz /
    512 samples gives a 23.22 ms hop. Accuracy is additionally limited by the
    92.88 ms Hann analysis window; this is not a phoneme/beat transcription.
    """
    path = Path(path).resolve(strict=True)
    sample_rate, window, hop = 22050, 2048, 512
    samples = decode_audio(path, sample_rate)
    duration = len(samples) / sample_rate
    padded = np.pad(samples, (window // 2, window // 2))
    windows = np.lib.stride_tricks.sliding_window_view(padded, window)[::hop]
    # Process spectra in bounded batches rather than retaining a recording-sized
    # spectrogram. The editable output only needs the compact feature envelopes.
    rms = np.sqrt(np.einsum("ij,ij->i", windows, windows, dtype=np.float64) / window)
    frequencies = np.fft.rfftfreq(window, 1 / sample_rate)
    band_masks = {name: (frequencies >= lower) & (frequencies < upper)
                  for name, lower, upper in (("low", 20, 250), ("mid", 250, 4000), ("high", 4000, 11026))}
    band_values = {name: np.zeros(len(windows)) for name in band_masks}
    flux, previous_spectrum = np.zeros(len(windows)), None
    hann = signal.windows.hann(window, sym=False)
    for start in range(0, len(windows), 512):
        stop = min(start + 512, len(windows))
        spectrum = np.abs(np.fft.rfft(windows[start:stop] * hann, axis=1)) / (window / 2)
        for name, mask in band_masks.items():
            band_values[name][start:stop] = np.sqrt(np.sum(spectrum[:, mask] ** 2, axis=1))
        if previous_spectrum is not None:
            flux[start] = np.maximum(0, spectrum[0] - previous_spectrum).sum()
        flux[start + 1:stop] = np.maximum(0, np.diff(spectrum, axis=0)).sum(axis=1)
        previous_spectrum = spectrum[-1]
    bands = {name: _normalize(values) for name, values in band_values.items()}
    onset_strength = _normalize(flux)
    peaks, _ = signal.find_peaks(
        onset_strength, height=max(0.1, float(np.median(onset_strength)) * 2),
        prominence=0.08, distance=max(1, round(0.08 * sample_rate / hop)),
    )
    energy = _normalize(rms)
    frames = [
        {"time_seconds": round(i * hop / sample_rate, 7), "rms": round(float(rms[i]), 7),
         "energy": round(float(energy[i]), 7), "low": round(float(bands["low"][i]), 7),
         "mid": round(float(bands["mid"][i]), 7), "high": round(float(bands["high"][i]), 7),
         "onset": round(float(onset_strength[i]), 7)}
        for i in range(len(rms)) if i * hop / sample_rate < duration
    ]
    events = [
        {"kind": "onset", "time_seconds": round(int(i) * hop / sample_rate, 7),
         "strength": round(float(onset_strength[i]), 5), "timing_precision": "estimated"}
        for i in peaks if i * hop / sample_rate < duration
    ]
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    result = {
        "schema": "kinesmith.audio-features", "version": "1.0.0",
        "source": {"path": str(path), "sha256": digest},
        "duration_seconds": duration, "sample_rate": sample_rate, "hop_seconds": hop / sample_rate,
        "window_seconds": window / sample_rate, "channels_analyzed": 1,
        "method": "mono RMS + Hann FFT band energy + positive spectral flux peaks",
        "timing_precision": "estimated", "beat_grid": None, "phoneme_alignment": None,
        "notes": ["Onset 是分析估計，不能當成精確節拍、歌詞、音節或音素時間。",
                  "time_seconds 以音訊檔起點計算；合成時再套用時間軸偏移。",
                  "energy 與頻帶值各自以全檔第 95 百分位正規化；rms 保留線性振幅。"],
        "peak_amplitude": float(np.max(np.abs(samples))), "frames": frames, "events": events,
    }
    if output is not None:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def feature_at(features: dict, time_seconds: float, audio_offset_seconds: float = 0.0) -> dict:
    """Linearly sample features at a video timestamp; positive offset delays audio."""
    t = float(time_seconds) - float(audio_offset_seconds)
    keys = ("rms", "energy", "low", "mid", "high", "onset")
    frames = features.get("frames", [])
    if t < 0 or t >= float(features["duration_seconds"]) or not frames:
        return dict.fromkeys(keys, 0.0)
    index = t / float(features["hop_seconds"])
    left = min(int(index), len(frames) - 1)
    right = min(left + 1, len(frames) - 1)
    weight = min(1.0, max(0.0, index - left))
    return {key: float(frames[left][key]) * (1 - weight) + float(frames[right][key]) * weight for key in keys}
