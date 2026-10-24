"""Render and verify these authored films with the existing Kinesmith pipeline.

--preflight: real keyframes, deterministic seek checks and two short motion studies.
--render: render both complete films, full AV decode, measured QA and cue validation.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
from scipy import signal
import soundfile as sf

from kinesmith.browser import asset_route
from kinesmith.project import load_project
from kinesmith.qa import qa_video
from kinesmith.render import context_for, encode, render_project, render_scene
from kinesmith.tools import ffmpeg_path, sha256, write_json

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = REPO/'outputs/introductions'
NAMES = {'kinesmith': 'kinesmith-introduction', 'codex': 'codex-explained'}


async def preflight_frames():
    import base64
    folder = OUT/'preflight'
    folder.mkdir(parents=True, exist_ok=True)
    evidence = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        for name in NAMES:
            project, _ = load_project(ROOT/f'project-{name}.json')
            tiles = []
            diagnostics = []
            deterministic = []
            for index, scene in enumerate(project['scenes']):
                page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                await page.route('**/*', lambda route: asset_route(route, ROOT))
                await page.goto('http://kinesmith.local/'+scene['source'], wait_until='load')
                await page.evaluate('async()=>{await window.kinesmithReady;await document.fonts.ready}')
                hashes = []
                # Repeat a non-monotonic seek: animation must not depend on prior frames.
                for frame in (90, 177, 90):
                    ctx = context_for(scene, project, ROOT)
                    ctx.update(frame=frame, time=frame/30, globalFrame=scene['start_frame']+frame)
                    data = await page.evaluate('''async ([f,ctx])=>{await window.renderFrame(f,ctx);return {
                        png:document.querySelector('#stage').toDataURL().split(',')[1],
                        diagnostics:window.kinesmithDiagnostics||[]}}''', [frame, ctx])
                    raw = base64.b64decode(data['png'])
                    hashes.append(hashlib.sha256(raw).hexdigest())
                    diagnostics.extend(dict(scene=scene['id'], frame=frame, detail=d) for d in data['diagnostics'])
                    path = folder/f'{name}-{index+1:02}-{frame:03}.png'
                    path.write_bytes(raw)
                    if len(hashes) < 3:
                        tiles.append((path, f'{index+1:02} / {frame/30:.1f}s local'))
                deterministic.append(hashes[0] == hashes[2])
                await page.close()
                if errors:
                    raise RuntimeError(errors)
            sheet = Image.new('RGB', (1600, 1020), '#202c25')
            draw = ImageDraw.Draw(sheet)
            for i, (path, label) in enumerate(tiles):
                with Image.open(path) as source:
                    source = source.convert('RGB').resize((400, 225), Image.Resampling.LANCZOS)
                    x, y = i%4*400, i//4*255
                    sheet.paste(source, (x, y))
                    draw.text((x+10, y+232), label, fill='#f1efdf')
            sheet.save(folder/f'{name}-contact.jpg', quality=94)
            evidence[name] = dict(text_bounds=diagnostics, repeat_seek_identical=all(deterministic), keyframes=len(tiles))
        await browser.close()
    write_json(folder/'checks.json', evidence)
    print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)
    if any(v['text_bounds'] or not v['repeat_seek_identical'] for v in evidence.values()):
        raise RuntimeError('Preflight found text bounds or non-deterministic seek')


def motion_studies():
    for name, chapter in [('kinesmith', 2), ('codex', 2)]:
        project, _ = load_project(ROOT/f'project-{name}.json')
        short = deepcopy(project)
        short.update(width=1280, height=720, duration_frames=60)
        short.pop('audio')
        scene = deepcopy(short['scenes'][chapter])
        scene.update(id=f'{name}-study', duration_frames=60, start_frame=0)
        short['scenes'] = [scene]
        rendered = render_scene(scene, short, ROOT)
        encode(short, ROOT, [rendered], OUT/f'{name}-motion-study.mp4', 'mp4')


def audio_checks(name):
    path = ROOT/f'audio/{name}-score.wav'
    samples, sr = sf.read(path, always_2d=True)
    metadata = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    cues = json.loads((ROOT/f'cues-{name}.json').read_text(encoding='utf-8'))
    cue_checks = []
    for cue in cues:
        target = cue['time_seconds']
        nearest = min(abs(e['onset_seconds']-target) for e in metadata['events'] if e['instrument'] == 'keys')
        window = samples[round(target*sr):round((target+.12)*sr)]
        cue_checks.append(dict(frame=cue['frame'], time_seconds=target, event_error_frames=nearest*30,
                               measured_window_rms=float(np.sqrt(np.mean(window**2)))))
    result = subprocess.run([ffmpeg_path(), '-hide_banner', '-nostdin', '-i', str(path),
                             '-af', 'loudnorm=I=-16:TP=-1:LRA=9:print_format=json', '-f', 'null', '-'],
                            capture_output=True, check=True)
    loudness = json.loads(re.findall(r'\{[^{}]+\}', result.stderr.decode())[-1])
    mono = samples.mean(axis=1)
    result = dict(sample_rate=sr, channels=samples.shape[1], samples=len(samples), duration_seconds=len(samples)/sr,
                  peak_dbfs=float(20*np.log10(np.max(np.abs(samples)))),
                  integrated_lufs=float(loudness['input_i']), true_peak_dbtp=float(loudness['input_tp']),
                  mono_rms=float(np.sqrt(np.mean(mono**2))),
                  first_50ms_rms=float(np.sqrt(np.mean(samples[:2400]**2))),
                  final_50ms_rms=float(np.sqrt(np.mean(samples[-2400:]**2))),
                  cues=cue_checks, sha256=sha256(path), subjective_listening='not_performed')
    result['passed'] = (len(samples) == 48*48000 and sr == 48000 and samples.shape[1] == 2
                         and np.isfinite(samples).all() and result['true_peak_dbtp'] <= -.7
                         and all(c['event_error_frames'] <= 1 and c['measured_window_rms'] > .0001 for c in cue_checks))
    return result


def render_all(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    results = json.loads((OUT/'verification.json').read_text(encoding='utf-8')) if (OUT/'verification.json').exists() else {}
    for name, slug in NAMES.items():
        if only and name != only:
            continue
        path = ROOT/f'project-{name}.json'
        project, _ = load_project(path)
        movie = OUT/f'{slug}.mp4'
        rendered = render_project(path, output=movie, fmt='mp4')
        qa = qa_video(movie, OUT/f'{name}-qa', dict(width=1920, height=1080, fps='30', duration_seconds=48))
        diagnostics = []
        for scene in rendered['scenes']:
            diagnostic_path = Path(scene['frames_path']).parent/'diagnostics.json'
            diagnostics.extend(json.loads(diagnostic_path.read_text(encoding='utf-8')))
        audio = audio_checks(name)
        # The concrete code shown in the Codex film is executable Python.
        def total(items):
            return sum(items or [])
        assert total(None) == 0 and total([2, 3]) == 5
        results[name] = dict(video=str(movie.relative_to(REPO)), sha256=sha256(movie),
                             project_sha256=sha256(path), measurements=qa['measurements'],
                             technical_checks_passed=qa['technical_checks_passed'],
                             text_bounds_diagnostics=diagnostics, audio=audio,
                             visual_review='pending_contact_sheet_and_transition_frame_inspection',
                             full_motion_playback='not_performed', subjective_listening='not_performed')
        write_json(OUT/'verification.json', results)
        if not qa['technical_checks_passed'] or diagnostics or not audio['passed']:
            raise RuntimeError(f'{name}: verification failed; inspect outputs/introductions/verification.json')
        print(f'{name}: complete 48s film decoded and measured', flush=True)


def mux_checks_and_review_frames():
    """Measure the encoded soundtrack and extract actual consecutive cut frames."""
    results = json.loads((OUT/'verification.json').read_text(encoding='utf-8'))
    for name, slug in NAMES.items():
        movie = OUT/f'{slug}.mp4'
        decoded = subprocess.run([ffmpeg_path(), '-v', 'error', '-nostdin', '-i', str(movie),
                                  '-map', '0:a:0', '-ar', '48000', '-ac', '2', '-f', 'f32le', '-'],
                                 capture_output=True, check=True)
        samples = np.frombuffer(decoded.stdout, dtype='<f4').reshape(-1, 2)
        master, sr = sf.read(ROOT/f'audio/{name}-score.wav', always_2d=True)
        mono, reference = samples.mean(axis=1), master.mean(axis=1)
        cues = json.loads((ROOT/f'cues-{name}.json').read_text(encoding='utf-8'))
        alignments = []
        for cue in cues:
            onset = round(cue['time_seconds']*sr)
            a, b = max(0, onset-1920), min(len(mono), onset+12000)
            template = reference[onset:onset+8640]
            search = mono[a:b]
            correlation = signal.correlate(search, template, mode='valid', method='fft')
            energy = np.sqrt(np.maximum(signal.correlate(search**2, np.ones(len(template)), mode='valid', method='fft'), 1e-15))
            location = int(np.argmax(correlation/energy))
            alignments.append(dict(frame=cue['frame'], audio_offset_samples=a+location-onset,
                                   audio_offset_frames=(a+location-onset)/sr*30))
        measured = subprocess.run([ffmpeg_path(), '-hide_banner', '-nostdin', '-i', str(movie),
                                   '-vn', '-af', 'loudnorm=I=-16:TP=-1:LRA=9:print_format=json',
                                   '-f', 'null', '-'], capture_output=True, check=True)
        loudness = json.loads(re.findall(r'\{[^{}]+\}', measured.stderr.decode())[-1])
        mux = dict(decoded_audio_samples=len(samples), sample_rate=48000, channels=2,
                   integrated_lufs=float(loudness['input_i']), true_peak_dbtp=float(loudness['input_tp']),
                   cue_waveform_alignment=alignments, subjective_listening='not_performed')
        mux['passed'] = all(abs(c['audio_offset_frames']) <= 1 for c in alignments) and mux['true_peak_dbtp'] < 0
        results[name]['encoded_audio'] = mux
        folder = OUT/f'{name}-qa'
        indices = [n for cut in range(180, 1440, 180) for n in (cut-1, cut, cut+1)]
        selected = '+'.join(f'eq(n\\,{n})' for n in indices)
        subprocess.run([ffmpeg_path(), '-v', 'error', '-nostdin', '-y', '-i', str(movie),
                        '-vf', f'select={selected},scale=480:270', '-vsync', 'vfr',
                        '-frames:v', str(len(indices)), str(folder/'cut-%03d.png')], check=True)
        sheet = Image.new('RGB', (1440, 7*300), '#202c25')
        draw = ImageDraw.Draw(sheet)
        for i, frame in enumerate(indices):
            x, y = i%3*480, i//3*300
            with Image.open(folder/f'cut-{i+1:03}.png') as tile:
                sheet.paste(tile, (x, y))
            draw.text((x+10, y+279), f'{frame} / {frame/30:.3f}s', fill='white')
        sheet.save(folder/'cut-continuity.jpg', quality=93)
        if not mux['passed']:
            raise RuntimeError(f'{name}: encoded audio alignment/peak check failed: {mux}')
    write_json(OUT/'verification.json', results)
    print(json.dumps({name: result['encoded_audio'] for name, result in results.items()}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--mux-check', action='store_true')
    parser.add_argument('--only', choices=list(NAMES), help='Render only this film during a scoped revision')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.preflight:
        asyncio.run(preflight_frames())
        motion_studies()
    if args.render:
        render_all(args.only)
    if args.render or args.mux_check:
        mux_checks_and_review_frames()
