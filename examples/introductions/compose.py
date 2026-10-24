"""Compose two original, sample-free electronic scores; all note events stay editable.

uv run --all-extras examples/introductions/compose.py
Uses NumPy/SciPy, SoundFile, Mido and the installed FFmpeg; no generative model.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

import mido
import numpy as np
from scipy import signal
import soundfile as sf

from kinesmith.tools import ffmpeg_path, sha256

ROOT = Path(__file__).resolve().parent
SR, DURATION = 48000, 48


def compose(name: str):
    bright = name == 'kinesmith'
    bpm = 120 if bright else 80
    beat = 60 / bpm
    rng = np.random.default_rng(640 if bright else 214)
    mix = np.zeros((SR * DURATION, 2), dtype=np.float64)
    events = []
    # One triad per visual chapter. Voice leading remains inside each chord.
    chords = [(53, 57, 60), (48, 52, 55), (57, 60, 64), (55, 59, 62),
              (53, 57, 60), (48, 52, 55), (55, 59, 62), (48, 52, 55)] if bright else [
              (48, 52, 55), (55, 59, 62), (57, 60, 64), (53, 57, 60),
              (48, 52, 55), (53, 57, 60), (55, 59, 62), (48, 52, 55)]

    def add(kind, onset, duration, note=60, gain=.1, pan=0, chapter=0):
        if onset >= DURATION:
            return
        length = min(round((duration + (1.3 if kind in ('pad', 'keys', 'bell') else .12)) * SR),
                     len(mix) - round(onset * SR))
        t = np.arange(length) / SR
        f = 440 * 2**((note-69)/12)
        release = np.exp(-np.maximum(t-duration, 0) / (.32 if kind == 'pad' else .20))
        if kind == 'pad':
            wave = sum(np.sin(2*np.pi*f*k*t + .018*np.sin(t*2)*k) / k**2.6 for k in range(1, 5))
            envelope = np.minimum(t/.25, 1) * release
        elif kind == 'keys':
            wave = np.sin(2*np.pi*f*t + .6*np.exp(-t*3)*np.sin(2*np.pi*f*2*t))
            wave += .18*np.sin(2*np.pi*f*2*t)*np.exp(-t*5)
            envelope = (1-np.exp(-t*300))*np.exp(-t*2.1)*release
        elif kind == 'bell':
            wave = np.sin(2*np.pi*f*t + 1.2*np.exp(-t*9)*np.sin(2*np.pi*f*2*t))
            envelope = (1-np.exp(-t*700))*np.exp(-t*4.2)*release
        elif kind == 'bass':
            wave = np.sin(2*np.pi*f*t)+.16*np.sin(2*np.pi*f*2*t)
            envelope = (1-np.exp(-t*250))*np.exp(-t*2)*release
        elif kind == 'kick':
            wave = np.sin(2*np.pi*(49*t + 112*.022*(1-np.exp(-t/.022))))
            envelope = (1-np.exp(-t*1200))*np.exp(-t*13)
        elif kind == 'snare':
            noise = rng.normal(0, 1, length)
            wave = signal.sosfilt(signal.butter(2, [850, 6500], fs=SR, btype='bandpass', output='sos'), noise)
            wave += .35*np.sin(2*np.pi*183*t)*np.exp(-t*24)
            envelope = (1-np.exp(-t*1500))*np.exp(-t*26)
        else:
            noise = rng.normal(0, 1, length)
            wave = signal.sosfilt(signal.butter(2, [4500, 9500], fs=SR, btype='bandpass', output='sos'), noise)
            envelope = (1-np.exp(-t*2500))*np.exp(-t*(82 if kind == 'hat' else 11))
        mono = wave * envelope * gain
        start = round(onset * SR)
        weights = np.array([np.cos((pan+1)*np.pi/4), np.sin((pan+1)*np.pi/4)])
        mix[start:start+length] += mono[:, None]*weights
        # Quiet tempo-aware stereo echoes only on melodic transients.
        if kind in ('bell', 'keys'):
            delay = round(beat * (1.5 if bright else .75) * SR)
            size = min(length, len(mix)-start-delay)
            if size > 0:
                mix[start+delay:start+delay+size] += mono[:size, None]*weights[::-1]*.17
        events.append(dict(instrument=kind, onset_seconds=round(onset, 6),
                           duration_seconds=duration, midi_note=note,
                           gain=gain, pan=pan, chapter=chapter))

    for chapter, chord in enumerate(chords):
        start = chapter * 6
        body_end = 45 if chapter == 7 else start+6
        # Held triad plus a moving, chord-aware lead; no stock loops or samples.
        for i, note in enumerate(chord):
            add('pad', start+.035*i, body_end-start-.1, note, .043 if bright else .061, (i-1)*.65, chapter)
        if bright:
            motif = [0, 1, 2, 1, 2, 0, 1, 2]
            for j, offset in enumerate(np.arange(0, body_end-start, beat*.75)):
                if chapter == 0 and j % 2:
                    continue
                add('bell', start+float(offset), .28, chord[motif[j%8]]+12,
                    .095 if j%4 == 0 else .065, np.sin(j*.8)*.55, chapter)
        else:
            for j, offset in enumerate([0, 1.125, 2.25, 3.375, 4.5, 5.25]):
                if start+offset >= body_end or (chapter in (0, 5) and j % 2):
                    continue
                add('keys', start+offset, .62, chord[[2, 1, 0, 1, 2, 1][j]]+12,
                    .13 if j in (0, 3) else .095, -.35 if j%2 else .35, chapter)
        for bar in range(3 if bright else 2):
            base = start+bar*4*beat
            if base >= body_end:
                break
            for step in ([0, 1.5, 2.75] if bright else [0, 2.5]):
                onset = base+step*beat
                if onset < body_end:
                    add('bass', onset, beat*.68, chord[0]-12, .14 if bright else .15, 0, chapter)
            if chapter not in (0, 7):
                for step in ([0, 1.75, 2.5] if bright else [0, 2.5]):
                    if base+step*beat < body_end:
                        add('kick', base+step*beat, .3, 36, .29, 0, chapter)
                for step in [1, 3]:
                    if base+step*beat < body_end:
                        add('snare', base+step*beat, .18, 38, .095 if bright else .075, -.1, chapter)
                for j in range(8):
                    onset = base+(j*.5+(.085 if j%2 else 0))*beat
                    if onset < body_end:
                        add('hat', onset, .06, 42, .035 if j%2 else .05, .48 if j%2 else -.48, chapter)
        # Audible authored scene cue, paired with the visual chapter boundary.
        add('keys', start, .65, chord[0]+12, .17 if bright else .13, 0, chapter)
    # The final visual settle occurs at frame 1380 (46 s); leave a natural release.
    for note in chords[-1]:
        add('keys', 46, .8, note+12, .105, 0, 7)
    add('bass', 46, .9, 36, .17, 0, 7)
    # Anti-click boundary only, not a substitute for a musical ending.
    n = round(.04*SR)
    mix[:n] *= np.linspace(0, 1, n)[:, None]
    mix[-n:] *= np.linspace(1, 0, n)[:, None]
    mix *= .82 / max(.82, float(np.max(np.abs(mix))))
    folder = ROOT/'audio'
    folder.mkdir(exist_ok=True)
    premix = folder/f'{name}-premix.wav'
    master = folder/f'{name}-score.wav'
    sf.write(premix, mix, SR, subtype='PCM_24')
    first = subprocess.run([ffmpeg_path(), '-hide_banner', '-nostdin', '-i', str(premix),
                            '-af', 'loudnorm=I=-16:TP=-1:LRA=9:print_format=json',
                            '-f', 'null', '-'], capture_output=True, check=True)
    measured = json.loads(re.findall(r'\{[^{}]+\}', first.stderr.decode())[-1])
    filt = ('loudnorm=I=-16:TP=-1:LRA=9:linear=true:print_format=json:'
            f'measured_I={measured["input_i"]}:measured_TP={measured["input_tp"]}:'
            f'measured_LRA={measured["input_lra"]}:measured_thresh={measured["input_thresh"]}:'
            f'offset={measured["target_offset"]}')
    subprocess.run([ffmpeg_path(), '-v', 'error', '-nostdin', '-y', '-i', str(premix),
                    '-af', filt, '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s24le', str(master)], check=True)
    premix.unlink()
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
    messages = []
    for event in events:
        channel = 9 if event['instrument'] in ('kick', 'snare', 'hat') else 0
        start_tick = round(event['onset_seconds']/beat*480)
        end_tick = round((event['onset_seconds']+event['duration_seconds'])/beat*480)
        velocity = min(110, max(24, round(event['gain']*370)))
        messages.extend([(start_tick, mido.Message('note_on', note=event['midi_note'], velocity=velocity, channel=channel)),
                         (end_tick, mido.Message('note_off', note=event['midi_note'], velocity=0, channel=channel))])
    last = 0
    for tick, message in sorted(messages, key=lambda item: (item[0], item[1].type == 'note_on')):
        message.time = tick-last
        track.append(message)
        last = tick
    midi.save(folder/f'{name}-score.mid')
    metadata = dict(original_composition=True, license='CC0-1.0', bpm=bpm,
                    style='syncopated electronic / FM bell' if bright else 'downtempo / warm electric keys synthesis',
                    instrument_source='Original deterministic oscillator/noise synthesis, no samples or voicebank',
                    duration_seconds=DURATION, sample_rate=SR, channels=2,
                    timing_precision='authored events; no estimated vocal/phoneme timing',
                    musical_body_end_seconds=max(e['onset_seconds']+e['duration_seconds'] for e in events),
                    release_end_seconds=48,
                    master_sha256=sha256(master), premaster_measurements=measured, events=events)
    (folder/f'{name}-score.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'{name}: {len(events)} authored events → {master.name}', flush=True)


if __name__ == '__main__':
    for name in ('kinesmith', 'codex'):
        compose(name)
