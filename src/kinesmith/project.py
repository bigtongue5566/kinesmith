from __future__ import annotations

import json
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from jsonschema import Draft202012Validator

from .tools import sha256, write_json

ROOT = Path(__file__).resolve().parents[2]


def load_project(path: str | Path) -> tuple[dict, Path]:
    path = Path(path).resolve()
    if path.is_dir():
        path /= 'project.json'
    project = json.loads(path.read_text(encoding='utf-8-sig'))
    schema_path = Path(__file__).parent / 'schemas/project-1.schema.json'
    if not schema_path.exists():
        schema_path = ROOT / 'schemas/project-1.schema.json'
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    Draft202012Validator(schema).validate(project)
    fps = Fraction(project['fps'])
    if not 0 < fps <= 240:
        raise ValueError('fps 必須介於 0 與 240（含）之間')
    if project['width'] % 2 or project['height'] % 2:
        raise ValueError('影片寬高必須為偶數，以支援 yuv420p')
    ids = [s['id'] for s in project['scenes']]
    if len(ids) != len(set(ids)):
        raise ValueError('scene id 不可重複')
    for scene in project['scenes']:
        if scene['start_frame'] + scene['duration_frames'] > project['duration_frames']:
            raise ValueError(f"場景 {scene['id']} 超過作品時間軸")
        resolve_asset(path.parent, scene['source'])
        for source in scene.get('dependencies', []):
            resolve_asset(path.parent, source)
        for name in ('transition_in', 'transition_out'):
            if scene.get(name, {}).get('duration_frames', 0) > scene['duration_frames']:
                raise ValueError(f'{name} 長度超過場景')
    for key in ('features', 'interchange', 'brief'):
        if project.get(key):
            resolve_asset(path.parent, project[key])
    if project.get('audio'):
        resolve_asset(path.parent, project['audio']['source'])
    for source in project.get('dependencies', []):
        resolve_asset(path.parent, source)
    return project, path


def resolve_asset(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'素材路徑必須位於作品內：{value}')
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def revise_project(path: str | Path, scene_id: str, prompt: str, source: str | None = None,
                   params: dict | None = None) -> dict:
    project, path = load_project(path)
    scene = next((s for s in project['scenes'] if s['id'] == scene_id), None)
    if scene is None:
        raise ValueError(f'找不到場景：{scene_id}')
    history = path.parent / 'history'
    history.mkdir(exist_ok=True)
    version = project['revision']
    snapshot = history / f'project-v{version}-{sha256(path)[:12]}.json'
    if not snapshot.exists():
        snapshot.write_bytes(path.read_bytes())
    old_source = resolve_asset(path.parent, scene['source'])
    old_hash = sha256(old_source)
    backup = history / f'{scene_id}-{old_hash[:12]}{old_source.suffix}'
    if not backup.exists():
        backup.write_bytes(old_source.read_bytes())
    if source:
        # A source may be shared by several scenes. Fork it for a scoped revision.
        replacement = Path(source).resolve()
        if not replacement.is_file():
            raise FileNotFoundError(replacement)
        new_hash = sha256(replacement)
        new_source = old_source.with_name(
            f'{old_source.stem}.{scene_id}.v{version + 1}.{new_hash[:12]}{old_source.suffix}')
        new_source.write_bytes(replacement.read_bytes())
        scene['source'] = new_source.relative_to(path.parent).as_posix()
    if params is not None:
        scene['params'] = {**scene.get('params', {}), **params}
    project['revision'] += 1
    project.setdefault('revisions', []).append({
        'revision': project['revision'], 'scene': scene_id, 'prompt': prompt,
        'timestamp': datetime.now(timezone.utc).isoformat(), 'previous_source_sha256': old_hash,
        'source_sha256': sha256(resolve_asset(path.parent, scene['source'])),
        'params': scene.get('params', {})})
    write_json(path, project)
    return project
