"""Standard MIDI import/export and bounded, preservation-first score edits."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import mido

from .model import Bend, Control, Note, Patch, Score, Section, Track


def write_midi(score: Score, path: Path):
    # SMF cannot identify independent same-pitch voices on one channel. Fail before
    # opening the file rather than exporting ambiguous note-offs or shortening notes.
    groups = [(track.id, track.notes) for track in score.tracks if not track.is_drum]
    groups += [("drum channel", [n for t in score.tracks if t.is_drum for n in t.notes])]
    for name, notes in groups:
        ends = {}
        for note in sorted(notes, key=lambda n: (n.start, n.pitch)):
            gate = note.duration * (0.55 if note.articulation == "staccato" else 1)
            if ends.get(note.pitch, -1) > note.start + 1e-7:
                raise ValueError(f"{name}: overlapping same-pitch MIDI voices; split or tie explicitly")
            ends[note.pitch] = note.start + gate
    midi = mido.MidiFile(type=1, ticks_per_beat=960, charset="utf-8")
    conductor = mido.MidiTrack()
    midi.tracks.append(conductor)
    conductor.append(mido.MetaMessage("track_name", name=score.title))
    conductor.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(score.bpm)))
    conductor.append(mido.MetaMessage("time_signature", numerator=score.meter[0],
                                     denominator=score.meter[1]))
    markers = sorted((round(s.start * 960), s.name) for s in score.sections)
    last = 0
    for tick, name in markers:
        conductor.append(mido.MetaMessage("marker", text=name, time=tick-last))
        last = tick
    conductor.append(mido.MetaMessage("end_of_track", time=round(score.length_beats*960)-last))
    channels = iter(c for c in range(16) if c != 9)
    for track in score.tracks:
        channel = 9 if track.is_drum else next(channels)
        out = mido.MidiTrack()
        midi.tracks.append(out)
        out.append(mido.MetaMessage("track_name", name=track.name))
        out.append(mido.Message("program_change", channel=channel, program=track.program))
        # Explicit two-semitone pitch bend range (RPN 0).
        for cc, value in [(101, 0), (100, 0), (6, 2), (38, 0), (101, 127), (100, 127)]:
            out.append(mido.Message("control_change", channel=channel, control=cc, value=value))
        events = []
        for n in track.notes:
            if n.lyric:
                events.append((round(n.start*960), 1, mido.MetaMessage("lyrics", text=n.lyric)))
            duration = n.duration * (0.55 if n.articulation == "staccato" else 1)
            velocity = min(127, n.velocity + (10 if n.articulation == "accent" else 0))
            events.append((round(n.start*960), 2,
                           mido.Message("note_on", channel=channel, note=n.pitch, velocity=velocity)))
            events.append((max(round((n.start+duration)*960), round(n.start*960)+1), 0,
                           mido.Message("note_off", channel=channel, note=n.pitch, velocity=0)))
        for c in track.controls:
            events.append((round(c.beat*960), 1, mido.Message("control_change", channel=channel,
                           control=c.number, value=c.value)))
        for b in track.bends:
            events.append((round(b.beat*960), 1, mido.Message("pitchwheel", channel=channel,
                                                           pitch=b.value)))
        last = 0
        for tick, _, msg in sorted(events, key=lambda e: (e[0], e[1])):
            out.append(msg.copy(time=tick-last))
            last = tick
        out.append(mido.MetaMessage("end_of_track", time=max(0, round(score.length_beats*960)-last)))
    midi.save(str(path))


def read_midi(path: Path) -> Score:
    """Import constant-tempo SMF without inventing instrumentation or musical analysis.

    Variable tempo/meter, SMPTE, sustain and overlapping same-pitch voices need an
    explicit conversion plan; reject unsupported semantics instead of silently losing them.
    """
    try:
        midi = mido.MidiFile(str(path), charset="utf-8")
    except UnicodeDecodeError:
        midi = mido.MidiFile(str(path), charset="latin-1")
    if midi.type == 2 or midi.ticks_per_beat <= 0:
        raise ValueError("requires synchronous, beat-timed SMF type 0/1")
    tempos, meters, tracks, length = set(), set(), [], 0.0
    first_tempo, first_meter = float("inf"), float("inf")
    for ti, source in enumerate(midi.tracks):
        tick, active, buckets, name = 0, {}, {}, f"MIDI {ti}"
        lyrics = {}
        for msg in source:
            tick += msg.time
            beat = tick / midi.ticks_per_beat
            length = max(length, beat)
            if msg.type == "set_tempo":
                tempos.add(msg.tempo)
                first_tempo = min(first_tempo, beat)
            elif msg.type == "time_signature":
                meters.add((msg.numerator, msg.denominator))
                first_meter = min(first_meter, beat)
            elif msg.type == "track_name":
                name = msg.name
            elif msg.type == "lyrics":
                lyrics[beat] = msg.text
            if not hasattr(msg, "channel"):
                continue
            ch = msg.channel
            if ch not in buckets:
                buckets[ch] = Track(id=f"midi-{ti}-{ch}", name=name, is_drum=ch == 9,
                                     patch=Patch(engine="fm"))
            t = buckets[ch]
            if msg.type == "program_change":
                if t.notes or any(k[0] == ch for k in active):
                    raise ValueError("mid-track program changes require splitting the track")
                t.program = msg.program
            elif msg.type == "note_on" and msg.velocity > 0:
                key = (ch, msg.note)
                if key in active:
                    raise ValueError("overlapping same-pitch notes require explicit voice separation")
                active[key] = (beat, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                start, vel = active.pop((ch, msg.note), (None, None))
                if start is not None and beat > start:
                    t.notes.append(Note(pitch=msg.note, start=start, duration=beat-start, velocity=vel,
                                        lyric=lyrics.get(start)))
            elif msg.type == "control_change":
                if msg.control == 64 and msg.value >= 64:
                    raise ValueError("sustain-pedal MIDI requires baking pedal into note lengths")
                t.controls.append(Control(beat=beat, number=msg.control, value=msg.value))
            elif msg.type == "pitchwheel":
                t.bends.append(Bend(beat=beat, value=msg.pitch))
        if active:
            raise ValueError("MIDI contains unterminated notes")
        tracks.extend(t for t in buckets.values() if t.notes)
    if tempos and first_tempo > 0:
        tempos.add(500000)
    if meters and first_meter > 0:
        meters.add((4, 4))
    if len(tempos) > 1 or len(meters) > 1:
        raise ValueError("tempo/meter changes need an explicit conversion; original MIDI preserved")
    if not tracks:
        raise ValueError("MIDI has no note content")
    return Score(title=Path(path).stem, bpm=mido.tempo2bpm(next(iter(tempos), 500000)),
                 meter=next(iter(meters), (4, 4)), length_beats=length,
                 sections=[Section(name="匯入", start=0, end=length)], tracks=tracks,
                 decisions=["匯入 MIDI；音色為預設 FM 試聽，未推定原音源。"])


def replace_region(score: Score, track_id: str, start: float, end: float,
                   notes: list[Note]) -> Score:
    """Replace only notes fully contained in a half-open beat interval.

    Boundary-crossing notes cause a failure: the caller must decide how to handle them.
    Every other track, note and expression lane is preserved byte-for-byte in model data.
    """
    if not 0 <= start < end <= score.length_beats:
        raise ValueError("invalid edit range")
    result = deepcopy(score)
    target = next((t for t in result.tracks if t.id == track_id), None)
    if target is None:
        raise ValueError("unknown track")
    for n in target.notes:
        if n.start < end and n.start + n.duration > start:
            if n.start < start or n.start + n.duration > end + 1e-7:
                raise ValueError("note crosses edit boundary; resolve explicitly")
    if any(n.start < start or n.start+n.duration > end+1e-7 for n in notes):
        raise ValueError("replacement note outside edit range")
    target.notes = sorted([n for n in target.notes if not start <= n.start < end] + notes,
                          key=lambda n: (n.start, n.pitch))
    return Score.model_validate(result.model_dump())


def humanize(notes: list[Note], *, seed: int, timing: float = 0.012,
             velocity: int = 5, start: float = 0, end: float | None = None) -> list[Note]:
    import numpy as np

    if timing < 0 or velocity < 0 or start < 0 or (end is not None and end <= start):
        raise ValueError("invalid humanization settings")
    rng = np.random.default_rng(seed)
    output = []
    for n in notes:
        lo = max(start, n.start-timing)
        hi = n.start+timing if end is None else min(end-n.duration, n.start+timing)
        if hi < lo:
            raise ValueError("humanization bounds exclude note")
        output.append(n.model_copy(update={"start": float(rng.uniform(lo, hi)),
                      "velocity": int(np.clip(n.velocity+rng.integers(-velocity, velocity+1), 1, 127))}))
    return output
