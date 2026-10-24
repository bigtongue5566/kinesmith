"""Frame-based orchestration and compositing, without an animation object API."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image

from .browser import render_browser
from .project import ROOT, load_project, resolve_asset
from .tools import ffmpeg_path, frame_seconds, probe_video, run, sha256, write_json


def versions() -> dict:
    result = {'python': platform.python_version(), 'platform': platform.platform()}
    for name in ('kinesmith', 'playwright', 'pillow', 'numpy', 'manim', 'bpy', 'imageio-ffmpeg'):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    result['ffmpeg'] = subprocess.check_output([ffmpeg_path(), '-version']).decode().splitlines()[0]
    return result


def fingerprint(scene: dict, project: dict, root: Path) -> str:
    sources = [scene['source'], *scene.get('dependencies', []), *project.get('dependencies', [])]
    sources += [project[k] for k in ('features', 'interchange') if project.get(k)]
    data = {'scene': scene, 'settings': {k: project.get(k) for k in ('fps', 'width', 'height', 'seed')},
            'sources': {s: sha256(resolve_asset(root, s)) for s in sources}, 'tools': versions(),
            'renderer': {p.name: sha256(p) for p in
                         (Path(__file__), ROOT / 'src/kinesmith/browser.py',
                          ROOT / 'src/kinesmith/engine_worker.py')}}
    vendor_manifest = ROOT / 'vendor/manifest.json'
    if vendor_manifest.exists():
        data['vendor'] = {'manifest': sha256(vendor_manifest), 'files': {}}
        for package in json.loads(vendor_manifest.read_text(encoding='utf-8')):
            for relative in package['files']:
                data['vendor']['files'][relative] = sha256(ROOT / 'vendor' / relative)
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def context_for(scene: dict, project: dict, root: Path) -> dict:
    context = {k: project[k] for k in ('width', 'height', 'fps')}
    context.update({'fps_number': float(Fraction(project['fps'])),
                    'duration': frame_seconds(scene['duration_frames'], project['fps']),
                    'duration_frames': scene['duration_frames'], 'seed': project.get('seed', 42),
                    'params': scene.get('params', {}), 'engine': scene['engine'],
                    'class_name': scene.get('class_name', 'MotionScene'),
                    'start_frame': scene['start_frame'], 'project_root': str(root)})
    for key in ('features', 'interchange'):
        context[key] = json.loads(resolve_asset(root, project[key]).read_text(encoding='utf-8')) \
            if project.get(key) else None
    return context


def render_scene(scene: dict, project: dict, root: Path, force=False) -> dict:
    digest = fingerprint(scene, project, root)
    cache = root / '.render-cache' / scene['id'] / digest
    frames = cache / 'frames'
    manifest = cache / 'render.json'
    if not force and manifest.exists():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        # Detect truncated or changed cached frames, rather than trusting directory existence.
        expected_names = {f'{i:06d}.png' for i in range(scene['duration_frames'])}
        if set(data.get('frame_hashes', {})) == expected_names and all((frames / name).exists() and sha256(frames / name) == value
               for name, value in data['frame_hashes'].items()):
            return {**data, 'cache_hit': True, 'frames_path': str(frames)}
    frames.mkdir(parents=True, exist_ok=True)
    # Keep the exact editable source and declared dependencies consumed by this render.
    for relative in [scene['source'], *scene.get('dependencies', []), *project.get('dependencies', [])]:
        saved = cache / 'sources' / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(resolve_asset(root, relative).read_bytes())
    ctx = context_for(scene, project, root)
    source = resolve_asset(root, scene['source'])
    ctx.update({'source_path': str(source), 'frames_path': str(frames)})
    details = {}
    print(f"render {scene['id']} ({scene['engine']}): {scene['duration_frames']} frames", flush=True)
    if scene['engine'] in ('canvas', 'rough', 'p5', 'three'):
        details = render_browser(scene, ctx, root, frames)
    elif scene['engine'] in ('manim', 'blender'):
        context_path = write_json(cache / 'context.json', ctx)
        run([sys.executable, '-m', 'kinesmith.engine_worker', str(context_path)],
            log=cache / 'native-render.log', cwd=str(root),
            timeout=float(os.environ.get('KINESMITH_NATIVE_TIMEOUT', '3600')))
    elif scene['engine'] == 'image':
        with Image.open(source) as im:
            im = im.convert('RGBA').resize((project['width'], project['height']), Image.Resampling.LANCZOS)
            for i in range(scene['duration_frames']):
                im.save(frames / f'{i:06d}.png')
    elif scene['engine'] == 'video':
        start = frame_seconds(scene.get('source_start_frame', 0), project['fps'])
        run([ffmpeg_path(), '-y', '-v', 'error', '-ss', str(start), '-i', str(source),
             '-vf', f"fps={project['fps']},scale={project['width']}:{project['height']}:force_original_aspect_ratio=decrease,"
                    f"pad={project['width']}:{project['height']}:(ow-iw)/2:(oh-ih)/2:color=black@0",
             '-frames:v', str(scene['duration_frames']), '-start_number', '0', str(frames / '%06d.png')])
    expected = [frames / f'{i:06d}.png' for i in range(scene['duration_frames'])]
    for path in expected:
        with Image.open(path) as im:
            if im.size != (project['width'], project['height']):
                raise ValueError(f'Unexpected native render dimensions: {path}: {im.size}')
    if fingerprint(scene, project, root) != digest:
        raise RuntimeError(f"{scene['id']} 的來源／依賴／工具在渲染中途改變，拒絕保存不一致的快取；請重新渲染")
    data = {'id': scene['id'], 'engine': scene['engine'], 'fingerprint': digest,
            'source_sha256': sha256(source), 'frame_count': len(expected), 'details': details,
            'frame_hashes': {p.name: sha256(p) for p in expected}}
    write_json(manifest, data)
    return {**data, 'cache_hit': False, 'frames_path': str(frames)}


def apply_transition(image: Image.Image, scene: dict, frame: int) -> Image.Image:
    alpha = np.asarray(image.getchannel('A'), dtype=np.float32) * scene.get('opacity', 1)
    for key, age in (('transition_in', frame), ('transition_out', scene['duration_frames'] - 1 - frame)):
        transition = scene.get(key)
        if not transition:
            continue
        duration = transition['duration_frames']
        progress = min(1.0, age / max(1, duration - 1))
        if transition['type'] == 'fade':
            alpha *= progress
        else:
            boundary = int(round(image.width * progress))
            if transition['type'] == 'wipe-left':
                alpha[:, boundary:] = 0
            else:
                alpha[:, :image.width - boundary] = 0
    image.putalpha(Image.fromarray(np.uint8(np.clip(alpha, 0, 255))))
    return image


def compose_frames(project: dict, rendered: list[dict]):
    scene_data = sorted(zip(project['scenes'], rendered), key=lambda pair: pair[0].get('layer', 0))
    for frame in range(project['duration_frames']):
        canvas = Image.new('RGBA', (project['width'], project['height']), '#0c1020')
        for scene, data in scene_data:
            local = frame - scene['start_frame']
            if 0 <= local < scene['duration_frames']:
                with Image.open(Path(data['frames_path']) / f'{local:06d}.png') as im:
                    canvas = Image.alpha_composite(canvas, apply_transition(im.convert('RGBA'), scene, local))
        yield canvas.convert('RGB')


def encode(project: dict, root: Path, rendered: list[dict], output: Path, fmt: str):
    output.parent.mkdir(parents=True, exist_ok=True)
    if fmt == 'png':
        output.mkdir(exist_ok=True)
        for stale in output.glob('[0-9][0-9][0-9][0-9][0-9][0-9].png'):
            if int(stale.stem) >= project['duration_frames']:
                stale.unlink()
        for frame, image in enumerate(compose_frames(project, rendered)):
            image.save(output / f'{frame:06d}.png')
        return
    args = [ffmpeg_path(), '-y', '-v', 'warning', '-f', 'rawvideo', '-pixel_format', 'rgb24',
            '-video_size', f"{project['width']}x{project['height']}", '-framerate', project['fps'], '-i', 'pipe:0']
    duration = frame_seconds(project['duration_frames'], project['fps'])
    if project.get('audio') and fmt != 'gif':
        audio = project['audio']
        args += ['-i', str(resolve_asset(root, audio['source']))]
        offset = audio.get('offset_seconds', 0)
        filters = ['aresample=48000']
        if offset < 0:
            filters += [f'atrim=start={-offset}', 'asetpts=PTS-STARTPTS']
        elif offset > 0:
            filters += [f'adelay={round(offset * 48000)}S:all=1']
        filters += [f"volume={audio.get('gain', 1)}", 'apad', f'atrim=duration={duration}']
        args += ['-filter_complex', '[1:a]' + ','.join(filters) + '[audio]',
                 '-map', '0:v', '-map', '[audio]']
    if fmt == 'webm':
        args += ['-c:v', 'libvpx-vp9', '-crf', '28', '-b:v', '0', '-row-mt', '1', '-pix_fmt', 'yuv420p',
                 '-c:a', 'libopus', '-b:a', '160k']
    elif fmt == 'mp4':
        args += ['-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                 '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart']
    elif fmt == 'gif':
        args += ['-filter_complex', '[0:v]split[a][b];[a]palettegen[p];[b][p]paletteuse', '-loop', '0']
    else:
        raise ValueError(fmt)
    args += ['-t', str(duration), str(output)]
    log_path = output.with_suffix(output.suffix + '.ffmpeg.log')
    with log_path.open('wb') as log:
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=log, stderr=log)
        try:
            for image in compose_frames(project, rendered):
                proc.stdin.write(image.tobytes())
            proc.stdin.close()
            code = proc.wait()
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        if code:
            raise RuntimeError(log_path.read_text(encoding='utf-8', errors='replace'))


def render_project(path: str | Path, *, output=None, fmt='webm', scene_id=None, force=False) -> dict:
    project, path = load_project(path)
    if scene_id and scene_id not in {s['id'] for s in project['scenes']}:
        raise ValueError(f'找不到場景：{scene_id}')
    root = path.parent
    rendered = [render_scene(s, project, root, force=force and (not scene_id or s['id'] == scene_id))
                for s in project['scenes']]
    output = Path(output).resolve() if output else root / 'renders' / f"v{project['revision']}.{fmt}"
    encode(project, root, rendered, output, fmt)
    report = {'schema_version': '1.0', 'project': project['id'], 'revision': project['revision'],
              'project_sha256': sha256(path), 'timestamp': datetime.now(timezone.utc).isoformat(),
              'fps': project['fps'], 'duration_frames': project['duration_frames'],
              'duration_seconds': frame_seconds(project['duration_frames'], project['fps']),
              'width': project['width'], 'height': project['height'], 'output': str(output),
              'output_sha256': sha256(output) if output.is_file() else None, 'tools': versions(),
              'scenes': rendered, 'licenses': project.get('licenses', []),
              'audio': project.get('audio'), 'visual_review': 'pending-human-or-agent-frame-inspection'}
    if fmt in ('webm', 'mp4'):
        report['measured'] = probe_video(output)
    report_path = output.parent / (output.stem + '-render.json')
    write_json(report_path, report)
    lines = [f"# Motion Report — {project['title']}", '',
             f"版本 {project['revision']}；{project['width']}×{project['height']}；FPS {project['fps']}；"
             f"{project['duration_frames']} 影格／{report['duration_seconds']:.6f} 秒。", '',
             '## 實際技術與場景', '']
    lines += [f"- {s['id']}：{s['engine']}；來源 SHA256 {r['source_sha256']}；"
              f"快取 {'重用' if r['cache_hit'] else '重新渲染'}。" for s, r in zip(project['scenes'], rendered)]
    lines += ['', '## 同步與驗證', '', '時間軸以整數影格及有理數 FPS 換算。音訊明確套用偏移、補靜音或裁切至畫面長度。',
              '影片編碼與解碼不等於主觀品質通過；請執行 qa 並檢視代表影格、轉場、文字及音畫。', '',
              '## 授權', '', json.dumps(project.get('licenses', []), ensure_ascii=False, indent=2)]
    report_path.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report
