"""Prepare, render, verify and package the authored Opusmith introduction only.

Uses the existing introduction QA functions; does not rerender the other films.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import soundfile as sf

from kinesmith.interchange import write_contract
from kinesmith.opusmith import load_opusmith
from kinesmith.project import load_project
from kinesmith.render import encode, render_scene
from kinesmith.tools import sha256, write_json
import verify as qa

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = REPO/'outputs/opusmith-introduction'
qa.OUT, qa.NAMES = OUT, {'opusmith': 'opusmith-introduction'}
TITLES = ['Opusmith：把想法，寫成音樂。', '一句想法，拆成音樂決定。',
          '音符、力度、段落，都能編輯。', '音色，也是一份可調的設計。',
          '從旋律，到完整分軌。', '歌詞與人聲，留在可調的工程。',
          '修改一小段，保留其他聲部。', '音樂與畫面，一起完成。']


def prepare(upstream: Path):
    """Generate this film only; never overwrite the earlier two project files."""
    music = ROOT/'music-opusmith'
    current = json.loads((music/'CURRENT.json').read_text(encoding='utf-8'))
    version = music/current['path']
    score = json.loads((version/'score.json').read_text(encoding='utf-8'))
    original = json.loads((music/'versions/v001/score.json').read_text(encoding='utf-8'))
    for source, dest in ((version/'audio/master.wav', ROOT/'audio/opusmith-score.wav'),
                         (version/'audio/master.mp3', ROOT/'audio/opusmith-score.mp3'),
                         (version/'multitrack.mid', ROOT/'audio/opusmith-score.mid')):
        shutil.copy2(source, dest)
    events = [dict(instrument=t['id'], onset_seconds=n['start']*60/score['bpm'],
                   duration_seconds=n['duration']*60/score['bpm'], midi_note=n['pitch'],
                   velocity=n['velocity']) for t in score['tracks'] for n in t['notes']]
    write_json(ROOT/'audio/opusmith-score.json', dict(original_composition=True, license='CC0-1.0',
        style='original melodic broken beat / liquid electronic', bpm=160, key='D minor',
        instrument_source='Real Opusmith 0.2.0 native oscillators, noise and Pedalboard; no samples or vocals',
        duration_seconds=48, musical_body_seconds=46.5, release_end_seconds=48,
        opusmith_version=current['version'], master_sha256=sha256(ROOT/'audio/opusmith-score.wav'), events=events))
    tracks = []
    for track in score['tracks']:
        samples, sr = sf.read(version/f'audio/stems/{track["id"]}.flac', always_2d=True)
        assert sr == 48000 and len(samples) == 48*sr
        energy = np.sqrt(np.mean(samples.reshape(960,2400,2)**2, axis=(1,2)))
        tracks.append(dict(id=track['id'], name=track['name'], notes=track['notes'],
                           patch=track['patch'], energy=np.round(energy,7).tolist()))
    write_json(ROOT/'data/opusmith-music.json', dict(bpm=160, tracks=tracks,
               original_pluck=next(t['notes'] for t in original['tracks'] if t['id']=='pluck')))
    # The adapter reads the actual native project and verifies its file checksums.
    contract = load_opusmith(music, fps='30')
    write_contract(ROOT/'opusmith-music.av.json', contract)
    project = dict(schema_version='1.0', id='opusmith-introduction', title=TITLES[0], revision=1,
        prompt='再一個介紹 opusmith 這個專案', brief='brief-opusmith.md', fps='30', width=1920, height=1080,
        duration_frames=1440, seed=251025, dependencies=['assets/NotoSansTC-VF.ttf','data/opusmith-music.json'],
        interchange='opusmith-music.av.json', audio=dict(source='audio/opusmith-score.wav',offset_seconds=0,gain=1),
        licenses=[dict(asset='Original animation and source',license='MIT',source='This repository'),
                  dict(asset='Original composition, MIDI and audio',license='CC0-1.0',source='compose-opusmith.py; no samples'),
                  dict(asset='NotoSansTC-VF.ttf',license='OFL-1.1',source='assets/OFL-NotoSansTC.txt'),
                  dict(asset='Opusmith runtime snapshot',license='MIT',source='music-opusmith/rebuild/LICENSE'),
                  dict(asset='DSP, renderer and codecs',license='See THIRD_PARTY_NOTICES.md',source='No tool binaries redistributed')],
        revisions=[dict(revision=1,date='2026-10-25',prompt='新增完整 Opusmith 專案介紹，配樂真正使用 Opusmith 製作。')],
        scenes=[dict(id=f'opusmith-{i+1:02}',engine='canvas',source='scenes/opusmith.html',start_frame=i*180,
                     duration_frames=180,params=dict(chapter=i),dependencies=['scenes/drawing.js']) for i in range(8)])
    write_json(ROOT/'project-opusmith.json', project)
    cues = [dict(frame=i*180,time_seconds=i*6,title=title,sound_event='Authored FM note at chapter start',
                 visual_event=f'chapter {i+1} begins',tolerance_frames=1) for i,title in enumerate(TITLES)]
    cues.append(dict(frame=1350,time_seconds=45,sound_event='D minor final chord',
                     visual_event='Final card settles; hold with release to 48s',tolerance_frames=1))
    write_json(ROOT/'cues-opusmith.json',cues)
    (ROOT/'opusmith.srt').write_text('\n'.join(f'{i+1}\n00:00:{i*6:02},000 --> 00:00:{(i+1)*6:02},000\n{t}\n'
                                             for i,t in enumerate(TITLES)),encoding='utf-8')
    research = ROOT/'research/opusmith-v0.2.0'
    research.mkdir(parents=True,exist_ok=True)
    sources = {}
    for name in ('README.md','docs/VOCALS.md','docs/VALIDATION.md','LICENSE'):
        dest = research/name.replace('/','-')
        shutil.copy2(upstream/name,dest)
        sources[name] = sha256(dest)
    write_json(research/'PROVENANCE.json',dict(repository='https://github.com/bigtongue5566/opusmith',
        commit='328e630f33af4b8b0ebe178895d1f87120532875',release='v0.2.0',
        release_published_at='2026-10-24T19:54:21Z',checked_at='2026-10-25',license='MIT',files=sources))
    print(json.dumps(dict(music_version=current['version'],capabilities=contract['capabilities'],
                          warnings=contract['warnings']),ensure_ascii=False,indent=2),flush=True)


def motion_study():
    project, _ = load_project(ROOT/'project-opusmith.json')
    short = deepcopy(project)
    short.update(width=1280,height=720,duration_frames=90)
    short.pop('audio')
    scene = deepcopy(project['scenes'][1])
    scene.update(id='opusmith-study',start_frame=0,duration_frames=90)
    short['scenes'] = [scene]
    rendered = render_scene(scene,short,ROOT)
    encode(short,ROOT,[rendered],OUT/'opusmith-motion-study.mp4','mp4')


def package():
    evidence = json.loads((OUT/'verification.json').read_text(encoding='utf-8'))['opusmith']
    if not (evidence['technical_checks_passed'] and evidence['encoded_audio']['passed']
            and evidence['audio']['passed'] and not evidence['text_bounds_diagnostics']
            and evidence['visual_review']=='representative_and_cut_frames_inspected'):
        raise RuntimeError('Complete technical and visual review before packaging')
    selected = ['README.md','ORIGINAL_PROMPT-opusmith.txt','release-opusmith.md','compose-opusmith.py','opusmith_film.py','verify.py','brief-opusmith.md','sources-opusmith.md',
                'project-opusmith.json','cues-opusmith.json','opusmith.srt','opusmith-music.av.json',
                'scenes/opusmith.html','scenes/drawing.js','assets/NotoSansTC-VF.ttf','assets/OFL-NotoSansTC.txt',
                'audio/opusmith-score.wav','audio/opusmith-score.mp3','audio/opusmith-score.mid','audio/opusmith-score.json']
    files = {p.relative_to(REPO).as_posix():p for p in [ROOT/name for name in selected]}
    for folder in ('music-opusmith','data','research/opusmith-v0.2.0'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                files[p.relative_to(REPO).as_posix()] = p
    for p in OUT.rglob('*'):
        if p.is_file() and p.name not in ('decoded-audio.wav',) and (p.suffix in ('.json','.md','.mp4','.jpg')):
            files[p.relative_to(REPO).as_posix()] = p
    for name in ('LICENSE','THIRD_PARTY_NOTICES.md','README.md'):
        files[name] = REPO/name
    files['docs/opusmith-introduction.md'] = REPO/'docs/opusmith-introduction.md'
    manifest = {name:dict(bytes=p.stat().st_size,sha256=sha256(p)) for name,p in sorted(files.items())}
    dist = REPO/'dist/opusmith-introduction'
    dist.mkdir(parents=True,exist_ok=True)
    archive = dist/'kinesmith-opusmith-introduction-v1.zip'
    with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=6) as stream:
        for name,path in sorted(files.items()):
            stream.writestr('kinesmith/'+name,path.read_bytes())
        stream.writestr('kinesmith/manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    import hashlib
    with ZipFile(archive) as stream:
        assert stream.testzip() is None
        for name,entry in manifest.items():
            assert hashlib.sha256(stream.read('kinesmith/'+name)).hexdigest()==entry['sha256'],name
    for source,dest in ((OUT/'opusmith-introduction.mp4',dist/'opusmith-introduction.mp4'),
                         (ROOT/'audio/opusmith-score.mp3',dist/'opusmith-score.mp3'),
                         (OUT/'motion-report.md',dist/'motion-report.md')):
        shutil.copy2(source,dest)
    write_json(dist/'manifest.json',manifest)
    (dist/'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in sorted(dist.iterdir())
        if p.is_file() and p.name!='SHA256SUMS'),encoding='utf-8')
    print(json.dumps(dict(archive=str(archive),bytes=archive.stat().st_size,entries=len(manifest),
                          sha256=sha256(archive)),indent=2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',type=Path,metavar='PINNED_OPUSMITH_SOURCE')
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--package',action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.prepare:
        prepare(args.prepare)
    if args.preflight:
        asyncio.run(qa.preflight_frames())
        motion_study()
    if args.render:
        qa.render_all('opusmith')
        qa.mux_checks_and_review_frames()
    if args.package:
        package()
