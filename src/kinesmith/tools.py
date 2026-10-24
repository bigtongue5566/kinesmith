"""Small subprocess utilities; never invoke a shell for project commands."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path

import imageio_ffmpeg


def ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args: list[str], *, log: Path | None = None, **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run([str(x) for x in args], capture_output=True, **kwargs)
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args[0]}\n"
                           + result.stderr.decode('utf-8', errors='replace')[-6000:])
    return result


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path: str | Path, data) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def probe_video(path: str | Path) -> dict:
    reader = imageio_ffmpeg.read_frames(str(path), pix_fmt='rgb24')
    try:
        metadata = next(reader)
    finally:
        reader.close()
    count, duration = imageio_ffmpeg.count_frames_and_secs(str(path))
    # read_frames rounds NTSC rates; parse ffmpeg's exact rational where available.
    result = subprocess.run([ffmpeg_path(), '-i', str(path)], capture_output=True)
    info = result.stderr.decode('utf-8', errors='replace')
    match = re.search(r'(\d+(?:\.\d+)?) fps', info)
    return {'width': metadata['size'][0], 'height': metadata['size'][1],
            'fps': metadata['fps'], 'frame_count': count, 'duration_seconds': duration,
            'codec': metadata.get('codec'), 'pixel_format': metadata.get('pix_fmt'),
            'fps_display': match.group(1) if match else None}


def frame_seconds(frame: int, fps: str | int | float) -> float:
    return float(Fraction(frame) / Fraction(str(fps)))
