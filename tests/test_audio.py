import json
import subprocess

import imageio_ffmpeg
import numpy as np
import pytest
from scipy.io import wavfile

from kinesmith.audio import analyze_audio, decode_audio, feature_at


def test_estimated_features_detect_authored_tone_bursts_and_offset(tmp_path):
    sr = 22050
    samples = np.zeros(3 * sr, dtype=np.float32)
    for start in (0.5, 1.5, 2.5):
        n = int(0.2 * sr)
        t = np.arange(n) / sr
        samples[int(start * sr):int(start * sr) + n] = 0.6 * np.sin(2 * np.pi * 120 * t) * np.exp(-20 * t)
    source, output = tmp_path / "bursts.wav", tmp_path / "features.json"
    wavfile.write(source, sr, samples)
    features = analyze_audio(source, output)
    assert features["duration_seconds"] == pytest.approx(3)
    assert features["beat_grid"] is None
    assert features["phoneme_alignment"] is None
    assert all(event["timing_precision"] == "estimated" for event in features["events"])
    onsets = [event["time_seconds"] for event in features["events"]]
    assert all(min(abs(onset - target) for onset in onsets) < 0.055 for target in (0.5, 1.5, 2.5))
    assert feature_at(features, 0.25)["rms"] == 0
    assert feature_at(features, 0.55)["rms"] > 0.1
    assert feature_at(features, 1.55, audio_offset_seconds=1)["rms"] == pytest.approx(feature_at(features, 0.55)["rms"])
    assert feature_at(features, 0.5, audio_offset_seconds=1)["energy"] == 0
    assert feature_at(features, 4)["energy"] == 0
    assert len(features["source"]["sha256"]) == 64
    assert json.loads(output.read_text(encoding="utf-8")) == features


def test_silence_and_short_audio_produce_finite_zero_features(tmp_path):
    source = tmp_path / "silence.wav"
    wavfile.write(source, 48000, np.zeros(500, dtype=np.int16))
    features = analyze_audio(source)
    assert features["events"] == []
    assert features["peak_amplitude"] == 0
    assert all(frame["energy"] == 0 for frame in features["frames"])


def test_general_compressed_audio_uses_ffmpeg_decoder(tmp_path):
    source, compressed = tmp_path / "input.wav", tmp_path / "input.webm"
    wavfile.write(source, 22050, np.sin(2 * np.pi * 440 * np.arange(22050) / 22050).astype(np.float32) * 0.2)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", str(source),
                    "-c:a", "libopus", str(compressed)], check=True, capture_output=True)
    decoded = decode_audio(compressed)
    assert len(decoded) == pytest.approx(22050, abs=100)
    features = analyze_audio(compressed)
    assert features["duration_seconds"] == pytest.approx(1, abs=0.01)
    assert features["peak_amplitude"] > 0.15


def test_decode_rejects_non_audio(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("this is not audio", encoding="utf-8")
    with pytest.raises(ValueError, match="無法解碼音訊"):
        decode_audio(bad)
