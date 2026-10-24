"""Author this film's original score through the real Opusmith v0.2 API.

Run in the pinned Opusmith environment, not Kinesmith's environment.
--output stores an independent editable song; --plugin snapshots its runtime.
--rerender publishes the existing score without replacing authored edits.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from opusmith import Note, Patch, Score, Section, Track
from opusmith.model import Effects, json_write
from opusmith.project import create_project, publish, sha, snapshot_runtime

BPM = 160
CHORDS = [(50, 53, 57), (46, 50, 53), (48, 53, 57), (48, 52, 55),
          (43, 46, 50), (46, 50, 53), (48, 52, 55), (50, 53, 57)]


def authored_score():
    tracks = [
        Track(id='keys', name='章節落點・柔和 FM', gain_db=-20, pan=.15,
              patch=Patch(engine='fm', fm_ratio=1, fm_index=.45, decay=.35,
                          sustain=.2, release=.65, cutoff_hz=3200),
              effects=Effects(reverb_mix=.11, reverb_size=.35)),
        Track(id='pluck', name='主題・濾波 Pluck', gain_db=-9, pan=-.35,
              patch=Patch(engine='pluck', attack=.006, decay=.18, sustain=.2,
                          release=.22, cutoff_hz=3200),
              effects=Effects(delay_seconds=.28125, delay_mix=.10, reverb_mix=.06)),
        Track(id='pad', name='和聲・柔暖長音', gain_db=-16,
              patch=Patch(engine='pad', attack=.22, decay=.3, sustain=.7,
                          release=.42, cutoff_hz=1250, voices=3, detune_cents=5),
              effects=Effects(highpass_hz=160, reverb_mix=.09)),
        Track(id='bass', name='低音・Additive', gain_db=-13,
              patch=Patch(engine='additive', partials=[1,.13,.04], attack=.009,
                          decay=.15, sustain=.7, release=.10, cutoff_hz=450),
              effects=Effects(highpass_hz=25, lowpass_hz=1300)),
        Track(id='kick', name='碎拍・Kick', is_drum=True, gain_db=-11,
              patch=Patch(engine='kick', attack=.001, decay=.13, sustain=0, release=.04)),
        Track(id='snare', name='碎拍・Snare', is_drum=True, gain_db=-11,
              patch=Patch(engine='snare', attack=.001, decay=.09, sustain=0, release=.04)),
        Track(id='hat', name='細分・Hi-hat', is_drum=True, gain_db=-15, pan=.25,
              patch=Patch(engine='hat', attack=.001, decay=.04, sustain=0, release=.025)),
    ]
    by_id = {t.id: t for t in tracks}

    def add(track, pitch, start, duration, velocity=88):
        by_id[track].notes.append(Note(pitch=pitch, start=start, duration=duration, velocity=velocity))

    for chapter, chord in enumerate(CHORDS):
        start = chapter*16
        stop = 120 if chapter == 7 else start+16
        add('keys', chord[0]+12, start, 1.1, 102)
        for pitch in chord:
            add('pad', pitch, start, stop-start-.3, 78)
        # A four-note idea changes register, spacing and its answer across chapters.
        motif = [0, 2, 1, 2, 0, 1, 2, 1]
        offsets = [0, 1.5, 3, 3.75, 6, 7.5, 10, 11.5, 12.75, 14.5]
        for i, offset in enumerate(offsets):
            if start+offset >= stop or (chapter in (0, 5) and i % 2):
                continue
            add('pluck', chord[motif[(i+chapter)%8]]+12, start+offset, .48 if i%3 else .9,
                88 if i%3 else 102)
        for bar in range(4):
            base = start+bar*4
            if base >= stop:
                break
            for off in (0, 1.75, 2.5):
                if base+off < stop:
                    add('bass', chord[0]-12, base+off, .65, 93 if off == 0 else 77)
            if chapter not in (0, 5, 7):
                # Original broken beat: syncopated kicks and ghost snares, not a house loop.
                for off in ((0, 1.5, 2.75) if bar%2 == 0 else (0, .75, 2.5)):
                    add('kick', 36, base+off, .35, 106 if off == 0 else 88)
                for off, vel in ((1, 102), (3, 100), (3.75, 43)):
                    add('snare', 38, base+off, .18, vel)
                for n in range(8):
                    add('hat', 42, base+n*.5, .08, 68 if n%2 == 0 else 43)
    # Last musical resolution at 45s, visual freeze at the same frame 1350.
    for pitch in CHORDS[-1]:
        add('keys', pitch+12, 120, 1.6, 76)
        add('pad', pitch, 120, 1.5, 72)
    add('bass', 38, 120, 1.6, 89)
    return Score(title='鍛造聲音 — Opusmith Film', bpm=BPM, key='D minor',
                 length_beats=124, tail_seconds=1.5, seed=251025, target_lufs=-16, ceiling_db=-1.5,
                 genres=['melodic broken beat', 'liquid electronic'],
                 sections=[Section(name=f'章節 {i+1}', start=i*16, end=min((i+1)*16,124)) for i in range(8)],
                 decisions=['160 BPM；每幕 16 拍；原創碎拍、濾波 pluck、長音及合成鼓。',
                            '音樂主體 46.5 秒，加 1.5 秒效果尾音，總長精確 48 秒。',
                            '45 秒終止起音，最後不接回鼓循環；無取樣、歌聲或外部生成模型。'],
                 tracks=tracks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plugin', type=Path)
    parser.add_argument('--rerender', action='store_true')
    args = parser.parse_args()
    work = args.output.resolve()
    if args.rerender:
        published = publish(work, Score.load(work/'score.json'), request='從現有可編輯 Score 重建。', sample_rate=48000)
        print(published, flush=True)
        return
    if args.plugin is None:
        parser.error('--plugin is required for the initial runtime snapshot')
    create_project(work, '再一個介紹 opusmith 這個專案',
                   '# Opusmith 介紹影片配樂\n\n48 秒原創旋律碎拍。160 BPM、D minor、七軌原生合成；'
                   '每 6 秒對應一幕，45 秒終止並保留釋音。無歌聲、取樣或外部生成模型。\n',
                   source=Path(__file__))
    snapshot_runtime(work, args.plugin.resolve())
    first = publish(work, authored_score(), request='為 48 秒專案介紹創作原創碎拍配樂。', sample_rate=48000)
    score = Score.load(work/'score.json')
    lead = next(t for t in score.tracks if t.id == 'pluck')
    for note in lead.notes:
        if 96 <= note.start < 100:
            note.pitch -= 12
    second = publish(work, score, request='只將 pluck 第 96–100 拍動機降八度，其餘音符與音軌不變。', sample_rate=48000)
    evidence = []
    for track in score.tracks:
        old, new = first/f'audio/stems/{track.id}.flac', second/f'audio/stems/{track.id}.flac'
        unchanged = sha(old) == sha(new)
        assert unchanged == (track.id != 'pluck'), track.id
        evidence.append(dict(track=track.id, unchanged=unchanged, before_sha256=sha(old), after_sha256=sha(new)))
    json_write(work/'LOCAL_REVISION.json', dict(from_version='v001', to_version='v002',
               changed_track='pluck', beat_range=[96,100], stems=evidence))
    print(second, flush=True)


if __name__ == '__main__':
    main()
