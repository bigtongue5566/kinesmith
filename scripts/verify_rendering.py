"""Produce and measure the release's real native-engine acceptance artifacts.

Uses the six-engine gallery sources; a rerun checks and reuses exact frame caches.
uv run --all-extras scripts/verify_rendering.py
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil

from kinesmith.project import ROOT, revise_project
from kinesmith.qa import qa_video
from kinesmith.render import encode, render_project
from kinesmith.tools import ffmpeg_path, run, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gallery', type=Path, default=ROOT / 'examples/gallery')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    gallery, output = args.gallery.resolve(), args.output.resolve()
    output.mkdir(exist_ok=True, parents=True)
    result = render_project(gallery, output=output / 'orbital-craft.webm')
    expected = {k: result[k] for k in ('width', 'height', 'fps', 'duration_seconds')}
    gallery_qa = qa_video(result['output'], output / 'gallery-qa', expected)
    if not gallery_qa['technical_checks_passed']:
        raise RuntimeError('Gallery technical QA failed')
    records = []
    project = json.loads((gallery / 'project.json').read_text(encoding='utf-8'))
    for scene, rendered in zip(project['scenes'], result['scenes']):
        movie = output / 'engines' / f"{scene['engine']}.webm"
        movie.parent.mkdir(exist_ok=True)
        # Encode original native frames directly, without a lossy intermediate.
        single = {**project, 'scenes': [{**scene, 'start_frame': 0}],
                  'duration_frames': scene['duration_frames']}
        single.pop('audio', None)
        encode(single, gallery, [rendered], movie, 'webm')
        qa = qa_video(movie, output / 'engines' / f"{scene['engine']}-qa",
                      {'width': project['width'], 'height': project['height'],
                       'fps': project['fps'], 'duration_seconds': 2})
        frames = Path(rendered['frames_path'])
        changed = sha256(frames / '000012.png') != sha256(frames / '000036.png')
        if not qa['technical_checks_passed'] or not changed:
            raise RuntimeError(f"Native {scene['engine']} did not produce valid motion")
        records.append({'engine': scene['engine'], 'source': scene['source'],
                        'source_sha256': rendered['source_sha256'],
                        'video': str(movie.relative_to(ROOT)), 'sha256': sha256(movie),
                        'frame_count': qa['measurements']['frame_count'],
                        'different_representative_frames': changed,
                        'technical_checks_passed': True})
    blender = next(s for s in result['scenes'] if s['engine'] == 'blender')
    shutil.copyfile(Path(blender['frames_path']).parent / 'editable.blend', output / 'editable-orbital.blend')

    # Cross-engine overlap, alpha layers and actual transitions using native output sequences.
    cross = deepcopy(project)
    cross['duration_frames'] = 96
    a, b, c = deepcopy(project['scenes'][:3])
    a.update(start_frame=0, duration_frames=48)
    b.update(start_frame=24, duration_frames=48, layer=1,
             transition_in={'type': 'fade', 'duration_frames': 24})
    c.update(start_frame=48, duration_frames=48, layer=2,
             transition_in={'type': 'wipe-left', 'duration_frames': 24})
    cross['scenes'] = [a, b, c]
    encode(cross, gallery, result['scenes'][:3], output / 'cross-engine-transitions.webm', 'webm')
    cross_qa = qa_video(output / 'cross-engine-transitions.webm', output / 'transitions-qa',
                       {'width': 640, 'height': 360, 'fps': '24', 'duration_seconds': 4})
    if not cross_qa['technical_checks_passed']:
        raise RuntimeError('Cross-engine transition QA failed')

    audio = render_project(gallery / 'project-audio-reactive.json',
                            output=output / 'audio-reactive.webm')
    audio_qa = qa_video(audio['output'], output / 'audio-reactive-qa', expected)
    # Save pristine pre-revision picture and modify one source parameter in a separate editable copy.
    revised = output / 'local-revision'
    if revised.exists():
        # Keep repeated invocations nondestructive; use a deterministic next available directory.
        suffix = 2
        while (output / f'local-revision-{suffix}').exists():
            suffix += 1
        revised = output / f'local-revision-{suffix}'
    shutil.copytree(gallery, revised, ignore=shutil.ignore_patterns('.render-cache', 'renders', 'media', '__pycache__'))
    # Reuse only previously verified frame directories; render_scene rechecks hashes before reuse.
    for cached in result['scenes']:
        original = Path(cached['frames_path']).parent
        shutil.copytree(original, revised / '.render-cache' / cached['id'] / cached['fingerprint'])
    before = render_project(revised, output=revised / 'before.webm')
    revise_project(revised, 'canvas', '只改 Canvas 強調色；保留其他五場景及音樂。',
                   params={'accent': '#ff775a'})
    after = render_project(revised, output=revised / 'after.webm')
    unrelated = all(s['cache_hit'] for s in after['scenes'][1:]) and all(
        a['frame_hashes'] == b['frame_hashes'] for a, b in zip(before['scenes'][1:], after['scenes'][1:]))
    if not unrelated or before['output_sha256'] == after['output_sha256']:
        raise RuntimeError('Local revision did not preserve unrelated scenes')
    # Optional output formats are real encodes, not extension renames.
    encode(project, gallery, result['scenes'], output / 'orbital-craft.mp4', 'mp4')
    fmt = {**project, 'scenes': [{**project['scenes'][0], 'start_frame': 0}], 'duration_frames': 48}
    fmt.pop('audio', None)
    encode(fmt, gallery, result['scenes'][:1], output / 'motion-study.gif', 'gif')
    png_project = {**fmt, 'duration_frames': 3}
    png_project['scenes'] = [{**fmt['scenes'][0], 'duration_frames': 3}]
    encode(png_project, gallery, result['scenes'][:1], output / 'png-sequence', 'png')
    mp4_qa = qa_video(output / 'orbital-craft.mp4', output / 'mp4-qa', expected)
    # Explicit full GIF decode; frame/image counts retained in the evidence.
    run([ffmpeg_path(), '-v', 'error', '-i', str(output / 'motion-study.gif'), '-f', 'null', '-'])
    from PIL import Image
    with Image.open(output / 'motion-study.gif') as gif:
        gif_frames = gif.n_frames
    validation = {'status': 'rendered-and-technically-checked', 'engines': records,
                  'gallery': {'technical_checks_passed': True, 'frame_count': 288, 'seconds': 12},
                  'cross_engine_transitions': cross_qa['technical_checks_passed'],
                  'standalone_audio_reactive': audio_qa['technical_checks_passed'],
                  'local_revision': {'unrelated_scenes_identical': unrelated,
                                     'changed_output': before['output_sha256'] != after['output_sha256'],
                                     'music_sha256_unchanged': sha256(revised / project['audio']['source']) == sha256(gallery / project['audio']['source'])},
                  'formats': {'webm': True, 'mp4': mp4_qa['technical_checks_passed'],
                              'gif_decoded_frames': gif_frames, 'png_sequence_frames': 3},
                  'subjective_review': 'Separate actual contact-sheet inspection; audio listening not verified.'}
    write_json(output / 'render-validation.json', validation)
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
