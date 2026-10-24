"""Measured video QA and review artifacts; heuristics never replace human inspection."""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
import re
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw


def _metadata(path: Path) -> dict:
    reader = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgb24")
    try:
        meta = next(reader)
    finally:
        reader.close()
    # imageio's stream parser rounds FPS to two decimal places. showinfo exposes
    # the decoder's rational rate (e.g. 24000/1001), preserving frame arithmetic.
    rate_probe = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "info", "-nostdin", "-i", str(path),
         "-map", "0:v:0", "-vf", "showinfo", "-frames:v", "1", "-an", "-f", "null", "-"],
        capture_output=True, check=False,
    )
    match = re.search(r"frame_rate:\s*(\d+)/(\d+)", rate_probe.stderr.decode(errors="replace"))
    if match and int(match[2]):
        meta["fps"] = int(match[1]) / int(match[2])
        meta["fps_rational"] = f"{match[1]}/{match[2]}"
    return meta


def _ranges(indices: list[int], fps: float, minimum_seconds: float = 0) -> list[dict]:
    if not indices:
        return []
    runs, start, end = [], indices[0], indices[0]
    for index in indices[1:] + [indices[-1] + 2]:
        if index != end + 1:
            if (end - start + 1) / fps >= minimum_seconds:
                runs.append({"start_seconds": round(start / fps, 6),
                             "end_seconds": round((end + 1) / fps, 6),
                             "start_frame": start, "end_frame_inclusive": end})
            start = index
        end = index
    return runs


def qa_video(path: str | Path, output_dir: str | Path, expected: dict | None = None) -> dict:
    """Decode every video frame, measure stream properties and create review images.

    ``expected`` accepts width, height, fps, duration_seconds. No content-related
    check is labelled passed just because a heuristic did not find a problem.
    """
    path = Path(path).resolve(strict=True)
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = expected or {}
    meta = _metadata(path)
    width, height = meta.get("source_size", meta["size"])
    fps = float(meta["fps"])
    if fps <= 0:
        raise ValueError("影片缺少有效影格率")
    # Full-stream decode below catches corrupt audio as well as corrupt video.
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    decoded = subprocess.run(
        [ffmpeg, "-v", "error", "-nostdin", "-xerror", "-i", str(path), "-f", "null", "-"],
        capture_output=True, check=False,
    )
    stderr = decoded.stderr.decode(errors="replace").strip()
    command = [ffmpeg, "-v", "error", "-nostdin", "-i", str(path), "-map", "0:v:0",
               "-vf", "scale=160:90", "-pix_fmt", "rgb24", "-vsync", "0", "-f", "rawvideo", "pipe:1"]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frame_size = 160 * 90 * 3
    black, frozen, flashes, luminances, differences = [], [], [], [], []
    frame_count, previous = 0, None
    try:
        while True:
            # BufferedReader.read(size) waits for a complete frame or EOF.
            raw = proc.stdout.read(frame_size)
            if not raw:
                break
            if len(raw) != frame_size:
                raise ValueError("FFmpeg 回傳不完整的影格")
            frame = np.frombuffer(raw, np.uint8).reshape(90, 160, 3).astype(np.float32)
            lum = frame @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            mean = float(lum.mean())
            luminances.append(mean)
            if float(np.mean(lum < 12)) > 0.98:
                black.append(frame_count)
            if previous is not None:
                diff = float(np.mean(np.abs(frame - previous)))
                differences.append(diff)
                if diff < 0.15:
                    frozen.append(frame_count)
                # A large single-frame brightness jump is a review flag, not a verdict.
                if abs(mean - luminances[-2]) > 75:
                    flashes.append(frame_count)
            previous = frame
            frame_count += 1
    finally:
        proc.stdout.close()
        raw_error = proc.stderr.read().decode(errors="replace")
        proc.stderr.close()
        proc.wait()
    if proc.returncode or not frame_count:
        raise ValueError(f"影片解碼失敗: {raw_error.strip() or '沒有影格'}")
    duration = frame_count / fps
    checks = {"full_decode": {"passed": decoded.returncode == 0, "diagnostic": stderr}}
    measurements = {"width": width, "height": height, "fps": fps, "frame_count": frame_count,
                    "duration_seconds": duration, "container_duration_seconds": meta.get("duration"),
                    "codec": meta.get("codec"), "pixel_format": meta.get("pix_fmt"),
                    "fps_rational": meta.get("fps_rational"),
                    "audio_codec": meta.get("audio_codec")}
    for key in ("width", "height", "fps", "duration_seconds"):
        if key not in expected:
            continue
        tolerance = 1 / fps + 0.002 if key == "duration_seconds" else (0.002 if key == "fps" else 0)
        actual, wanted = float(measurements[key]), float(Fraction(str(expected[key])))
        checks[key] = {"passed": abs(actual - wanted) <= tolerance, "actual": actual,
                       "expected": wanted, "tolerance": tolerance}
    representative_indices = sorted(set(round(i * (frame_count - 1) / 11) for i in range(12)))
    selected = "+".join(f"eq(n\\,{n})" for n in representative_indices)
    rep_pattern = output_dir / "frame-%03d.png"
    # Remove previous numbered frames only, to avoid a stale contact sheet after revision.
    for candidate in output_dir.glob("frame-*.png"):
        if re.fullmatch(r"frame-\d{3}\.png", candidate.name):
            candidate.unlink()
    subprocess.run(
        [ffmpeg, "-v", "error", "-nostdin", "-y", "-i", str(path), "-vf", f"select={selected}",
         "-vsync", "vfr", "-frames:v", str(len(representative_indices)), str(rep_pattern)],
        capture_output=True, check=True,
    )
    representative_files = sorted(output_dir.glob("frame-*.png"))
    if len(representative_files) != len(representative_indices):
        raise ValueError("代表影格數量與要求不符")
    tile_width, tile_height, columns = 320, round(320 * height / width) + 30, 4
    sheet = Image.new("RGB", (columns * tile_width, math.ceil(len(representative_files) / columns) * tile_height), "#17191f")
    draw = ImageDraw.Draw(sheet)
    reps = []
    for index, (file, frame_index) in enumerate(zip(representative_files, representative_indices)):
        x, y = (index % columns) * tile_width, (index // columns) * tile_height
        with Image.open(file) as source:
            thumb = source.convert("RGB")
            thumb.thumbnail((tile_width, tile_height - 30), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (x + (tile_width - thumb.width) // 2, y))
        draw.text((x + 8, y + tile_height - 23), f"#{frame_index:06d}  {frame_index / fps:.3f}s", fill="#e5e7ee")
        reps.append({"frame": frame_index, "time_seconds": frame_index / fps, "path": str(file)})
    contact_sheet = output_dir / "contact-sheet.jpg"
    sheet.save(contact_sheet, quality=92)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    flags = {
        "possible_black_ranges": _ranges(black, fps, 0.08),
        "possible_freeze_ranges": _ranges(frozen, fps, 0.5),
        "large_brightness_changes": [{"frame": n, "time_seconds": n / fps} for n in flashes],
    }
    result = {
        "schema": "kinesmith.video-qa", "version": "1.0.0", "source": str(path), "sha256": digest,
        "measurements": measurements, "checks": checks,
        "technical_checks_passed": all(check["passed"] for check in checks.values()),
        "heuristic_flags": flags, "visual_review": "required",
        "manual_checks": {key: "not_verified" for key in
                          ("text_clipping", "intentional_black_or_holds", "transitions", "audio_visual_sync",
                           "flicker_and_motion_continuity", "license_clearance")},
        "notes": ["黑畫面、定格、亮度跳變是低解析度啟發式提示；片頭黑、留白、定格與剪接可能是刻意設計。",
                  "完整解碼與格式檢查通過，不代表文字、同步、轉場或美感已通過人工檢查。",
                  "frame_count / fps 為 CFR 時間；VFR 影片需以逐幀 PTS 另行驗證同步。"],
        "representative_frames": reps, "contact_sheet": str(contact_sheet),
    }
    (output_dir / "qa.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Kinesmith 影片品質報告", "", f"影片：`{path.name}`", "",
             f"實測：{width}×{height}，{fps:g} FPS，{frame_count} 影格，{duration:.6f} 秒。", "",
             f"完整解碼與指定格式檢查：{'通過' if result['technical_checks_passed'] else '未通過'}。", "",
             f"黑畫面候選：{len(flags['possible_black_ranges'])} 段；定格候選：{len(flags['possible_freeze_ranges'])} 段；"
             f"亮度跳變候選：{len(flashes)}。", "", "![代表影格](contact-sheet.jpg)", "",
             "文字裁切、轉場、音畫同步、閃爍、動作連續性與授權仍需人工檢查；本報告不將這些項目宣稱為通過。", ""]
    (output_dir / "qa.md").write_text("\n".join(lines), encoding="utf-8")
    return result
