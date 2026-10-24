"""Real audio rendering, aligned lossless stems and measured technical checks."""

from __future__ import annotations

import hashlib
import importlib.metadata
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from pedalboard import Compressor, Delay, HighpassFilter, LowpassFilter, Pedalboard, Reverb
from scipy.signal import resample_poly

from .model import Score, json_write
from .synth import render_track


def db(amplitude: float) -> float:
    return float(20*np.log10(max(float(amplitude), 1e-12)))


def true_peak(data: np.ndarray) -> float:
    # Four-times oversampled estimate, not certified ITU-R BS.1770 true-peak metering.
    peak = 0.0
    for start in range(0, len(data), 262144):
        block = data[max(0, start-64):min(len(data), start+262144+64)]
        peak = max(peak, float(np.max(np.abs(resample_poly(block, 4, 1, axis=0)))))
    return peak


def analyze(data: np.ndarray, sr: int) -> dict:
    if data.ndim != 2 or data.shape[1] != 2 or len(data) < sr*.4:
        raise ValueError("analysis needs at least 0.4 seconds of stereo audio")
    finite = bool(np.isfinite(data).all())
    if not finite:
        raise ValueError("nonfinite audio")
    rms = float(np.sqrt(np.mean(data.astype(np.float64)**2)))
    peak = float(np.max(np.abs(data)))
    loudness = float(pyln.Meter(sr).integrated_loudness(data)) if rms > 1e-9 else None
    if loudness is not None and not np.isfinite(loudness):
        loudness = None
    corr = None
    if np.std(data[:, 0]) > 1e-9 and np.std(data[:, 1]) > 1e-9:
        corr = float(np.corrcoef(data.T)[0, 1])
    block = max(1, sr//10)
    levels = [float(np.sqrt(np.mean(data[i:i+block]**2))) for i in range(0, len(data), block)]
    mid = (data[:, 0]+data[:, 1])*.5
    side = (data[:, 0]-data[:, 1])*.5
    return {"duration_seconds": len(data)/sr, "sample_rate": sr, "channels": 2,
            "finite": finite, "non_silent": rms > 1e-6, "rms_dbfs": db(rms),
            "sample_peak_dbfs": db(peak), "estimated_true_peak_dbfs": db(true_peak(data)),
            "integrated_lufs": loudness, "clipped_samples": int(np.count_nonzero(np.abs(data)>=1)),
            "dc_offset": [float(x) for x in np.mean(data, axis=0)], "stereo_correlation": corr,
            "mid_rms_dbfs": db(np.sqrt(np.mean(mid**2))),
            "side_rms_dbfs": db(np.sqrt(np.mean(side**2))),
            "active_fraction": sum(x > 1e-5 for x in levels)/len(levels),
            "subjective_listening": "未進行；訊號分析不能代替聆聽。"}


def encode_mp3(wav: Path, mp3: Path):
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-v", "error", "-y",
                    "-i", str(wav), "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3)],
                   check=True, capture_output=True, timeout=300)


def render(score: Score, project: Path, output: Path, *, sample_rate: int = 44100,
           mp3: bool = True) -> dict:
    """Render into a new version directory; never overwrite an earlier render."""
    if sample_rate not in (22050, 32000, 44100, 48000):
        raise ValueError("unsupported sample rate")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    stems = output / "stems"
    stems.mkdir()
    frames = int(np.ceil((score.seconds+score.tail_seconds)*sample_rate))
    mix = np.zeros((frames, 2), dtype=np.float32)
    track_stats = []
    for track in score.tracks:
        signal = render_track(track, score, sample_rate, project)
        fx = track.effects
        chain = Pedalboard()
        if fx.highpass_hz:
            chain.append(HighpassFilter(cutoff_frequency_hz=fx.highpass_hz))
        chain.append(LowpassFilter(cutoff_frequency_hz=min(fx.lowpass_hz, sample_rate*.45)))
        chain.append(Compressor(threshold_db=fx.compressor_db, ratio=fx.ratio,
                                attack_ms=8, release_ms=100))
        if fx.delay_mix:
            chain.append(Delay(delay_seconds=fx.delay_seconds, feedback=.25, mix=fx.delay_mix))
        if fx.reverb_mix:
            chain.append(Reverb(room_size=fx.reverb_size, damping=.55, wet_level=fx.reverb_mix,
                                dry_level=1-fx.reverb_mix, width=1))
        signal = chain(signal.T.copy(), sample_rate).T.copy()
        if fx.sidechain_from and fx.duck_db:
            source = next(t for t in score.tracks if t.id == fx.sidechain_from)
            envelope = np.ones(frames, dtype=np.float32)
            # Transparent event-triggered ducking, not an audio detector compressor.
            size = round(fx.duck_release*sample_rate*6)
            curve = 1-(1-10**(-fx.duck_db/20))*np.exp(-np.arange(size)/(sample_rate*fx.duck_release))
            for note in source.notes:
                start = round(note.start*60/score.bpm*sample_rate)
                stop = min(frames, start+size)
                envelope[start:stop] = np.minimum(envelope[start:stop], curve[:stop-start])
            signal *= envelope[:, None]
        # Remove truncated tail discontinuities. Common alignment is preserved for all stems.
        fade = min(round(.05*sample_rate), frames)
        signal[-fade:] *= np.linspace(1, 0, fade)[:, None]
        signal[:min(64, frames)] *= np.linspace(0, 1, min(64, frames))[:, None]
        if not np.isfinite(signal).all():
            raise ValueError(f"nonfinite stem: {track.id}")
        peak = float(np.max(np.abs(signal)))
        if peak >= 1:
            raise ValueError(f"stem clips: {track.id}; reduce track gain before rendering")
        # Mix exactly the quantized stems, so the saved premaster can be reconstructed.
        sf.write(stems/f"{track.id}.flac", signal, sample_rate, subtype="PCM_24")
        quantized, _ = sf.read(stems/f"{track.id}.flac", dtype="float32", always_2d=True)
        mix += quantized
        track_stats.append({"id": track.id, "notes": len(track.notes),
                            "peak_dbfs": db(peak), "rms_dbfs": db(np.sqrt(np.mean(signal**2))),
                            "frames": len(signal), "effects": fx.model_dump()})
    # Floating-point premaster preserves unclipped summation and is useful for further mastering.
    sf.write(output/"premaster.wav", mix, sample_rate, subtype="FLOAT")
    rms = float(np.sqrt(np.mean(mix**2)))
    if rms <= 1e-6:
        raise ValueError("silent render cannot be delivered")
    measured = float(pyln.Meter(sample_rate).integrated_loudness(mix))
    desired_gain = 10**((score.target_lufs-measured)/20)
    ceiling = 10**(score.ceiling_db/20)
    gain = min(desired_gain, ceiling/max(true_peak(mix), 1e-12))
    # Prefer preserved transients to pretending every mix attained a loudness target.
    master = mix*gain
    sf.write(output/"master.wav", master, sample_rate, subtype="PCM_24")
    actual, _ = sf.read(output/"master.wav", dtype="float32", always_2d=True)
    stats = analyze(actual, sample_rate)
    if mp3:
        encode_mp3(output/"master.wav", output/"master.mp3")
    versions = {name: importlib.metadata.version(name) for name in
                ["opusmith", "numpy", "scipy", "mido", "soundfile", "pedalboard", "pyloudnorm"]}
    hashes = {}
    for path in sorted(output.rglob("*")):
        if path.is_file():
            with path.open("rb") as handle:
                hashes[path.relative_to(output).as_posix()] = hashlib.file_digest(handle, "sha256").hexdigest()
    result = {"master": stats, "tracks": track_stats, "mastering": {
        "method": "LUFS 量測後施加固定增益，以 4 倍過取樣峰值限制增益，無動態 limiter。",
        "target_lufs": score.target_lufs, "ceiling_dbfs": score.ceiling_db,
        "gain_db": db(gain), "target_attained": abs(stats["integrated_lufs"]-score.target_lufs)<.5},
        "dependencies": versions, "sha256": hashes}
    json_write(output/"render.json", result)
    return result


def process_asset(source: Path, destination: Path, *, start: float = 0, duration: float = 10,
                  semitones: float = 0, tempo: float = 1, highpass: float = 30) -> dict:
    """FFmpeg trimming, pitch resampling and independent time stretching; logs exact filters."""
    if not (start >= 0 and 0 < duration <= 600 and -24 <= semitones <= 24
            and .5 <= tempo <= 2 and 0 <= highpass <= 10000):
        raise ValueError("invalid sample processing parameters")
    if destination.exists():
        raise FileExistsError(destination)
    ratio = 2**(semitones/12)
    factor = tempo/ratio
    atempo = []
    while factor < .5:
        atempo.append("atempo=0.5")
        factor /= .5
    while factor > 2:
        atempo.append("atempo=2")
        factor /= 2
    atempo.append(f"atempo={factor:.10f}")
    filters = ["aresample=44100", f"asetrate={44100*ratio:.5f}", "aresample=44100"]
    filters += atempo+[f"highpass=f={highpass}", "afade=t=in:d=0.02"]
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-v", "error", "-n", "-ss", str(start),
                    "-t", str(duration), "-i", str(source), "-af", ",".join(filters),
                    "-ac", "2", "-c:a", "pcm_s24le", str(destination)],
                   check=True, capture_output=True, timeout=120)
    info = sf.info(destination)
    return {"source": str(source), "output": str(destination), "filters": filters,
            "crop_seconds": [start, duration], "duration_seconds": info.duration}
