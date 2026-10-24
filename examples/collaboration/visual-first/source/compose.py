"""Agent-authored response to the actual visual-first cue request.
No extra model, sample library or vocal engine. Run through the installed Opusmith
Python environment: uv run --no-project --python <opusmith-venv-python> python compose.py <output>
"""
import json
from pathlib import Path
import sys
from opusmith import Note, Patch, Score, Section, Track
from opusmith.model import Effects
from opusmith.audio import render
from opusmith.midi import write_midi
from opusmith.project import create_project, publish

out = Path(sys.argv[1]).resolve()
request = json.loads((out.parent / "visual-request.av.json").read_text(encoding="utf-8"))
assert request["mode"] == "visual-first"
assert [(cue["start_seconds"], cue["end_seconds"]) for cue in request["events"]] == [(0, 3), (3, 6)]
score = Score(title="Form becomes motion / visual cue response", bpm=120, length_beats=12,
    key="D minor", tail_seconds=0.4, seed=73,
    sections=[Section(name="form", start=0, end=6, intent="形狀展開，留白"),
              Section(name="motion", start=6, end=12, intent="動作擴張，增加密度")],
    tracks=[
      Track(id="pluck", name="Form motif", gain_db=-21,
        patch=Patch(engine="pluck", attack=0.004, decay=0.3, sustain=0.1, release=0.28, cutoff_hz=3500),
        notes=[Note(pitch=p, start=b, duration=0.65, velocity=v)
               for b,p,v in [(0,62,92),(1.5,65,80),(3,69,85),(4.5,65,76),(6,74,100),(7,72,85),(8,69,90),(9,65,80),(10,69,90),(11,62,82)]],
        effects=Effects(reverb_mix=0.08, reverb_size=0.35)),
      Track(id="pulse", name="Motion accents", role="drums", is_drum=True, gain_db=-20,
        patch=Patch(engine="kick", attack=0.003, decay=0.12, sustain=0, release=0.06),
        notes=[Note(pitch=36, start=b, duration=0.15, velocity=92) for b in [0,3,6,7,8,9,10,11]]),
      Track(id="foundation", name="Low anchor", gain_db=-27,
        patch=Patch(engine="fm", attack=0.02, decay=0.2, sustain=0.25, release=0.15,
                    fm_ratio=1, fm_index=0.2, cutoff_hz=900),
        notes=[Note(pitch=38, start=0, duration=5.5, velocity=80),
               Note(pitch=38, start=6, duration=5.5, velocity=88)])],
    decisions=["Responds to two 3-second picture cues at quarter-note beats 0 and 6.",
               "Six-second body plus 0.4-second effects tail, intentionally trimmed by picture edit.",
               "Original local synthesis only, no third-party samples or generative model."])
create_project(out, "依實際 visual-request.av.json 的兩個三秒場景創作配樂。",
               "# Motion Brief response\n\n120 BPM、D minor；前三秒疏、後三秒密，於 3 秒交接。", source=Path(__file__))
publish(out, score, request="Visual-first cue response", sample_rate=44100, mp3=False)
print(json.dumps({"project": str(out), "notes": sum(len(t.notes) for t in score.tracks)}, ensure_ascii=False))
