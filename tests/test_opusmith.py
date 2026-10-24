import json
from pathlib import Path

import mido
import pytest
import soundfile as sf
import numpy as np

from kinesmith.interchange import sha256
from kinesmith.opusmith import inside, load_midi, load_opusmith, load_ustx


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "opusmith-v0.2.0" / "score.json"


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def score_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8-sig"))


def test_real_v020_score_and_lyrics_are_read_without_source_mutation():
    before = sha256(FIXTURE)
    result = load_opusmith(FIXTURE, fps="30000/1001", offset_seconds="0.25")
    assert sha256(FIXTURE) == before
    assert len(result["lyrics"]) == 165
    assert len([e for e in result["events"] if e["kind"] == "note"]) == 1989
    assert all(lyric["timing_precision"] == "score-note" for lyric in result["lyrics"])
    assert result["duration"]["musical_seconds"] == pytest.approx(320 * 60 / 124)
    assert result["duration"]["timeline_seconds"] == pytest.approx(320 * 60 / 124 + 4.25)
    assert result["duration"]["audio_measured"] is False


def test_real_older_v010_schema_profile_still_reads():
    result = load_opusmith(ROOT / "examples" / "opusmith-v0.1.0")
    assert "score" in result["capabilities"]
    assert "v0.1.schema" in result["sources"][0]["schema_profile"]
    assert result["lyrics"] == []


def test_audio_duration_includes_real_tail_not_score_length(tmp_path):
    write_json(tmp_path / "score.json", score_fixture())
    sf.write(tmp_path / "master.wav", np.zeros((22050, 2)), 44100)
    result = load_opusmith(tmp_path, audio=tmp_path / "master.wav", offset_seconds=-0.1)
    assert result["duration"]["audio_seconds"] == 0.5
    assert result["duration"]["audio_measured"] is True
    assert result["audio"][0]["samples"] == 22050
    # Short supplied audio does not truncate explicitly scheduled score events.
    assert result["duration"]["timeline_seconds"] > 150


@pytest.mark.parametrize("change", [lambda s: s.update(format_version=19),
                                    lambda s: s.update(tempo_map=[{"beat": 0, "bpm": 80}]),
                                    lambda s: s["tracks"][0].update(new_semantics=True)])
def test_unknown_schema_degrades_to_audio_without_interpreting_events(tmp_path, change):
    score = score_fixture()
    change(score)
    write_json(tmp_path / "score.json", score)
    sf.write(tmp_path / "master.wav", np.zeros(800), 8000)
    result = load_opusmith(tmp_path, audio=tmp_path / "master.wav")
    assert result["capabilities"] == ["master-audio"]
    assert not result["events"] and not result["lyrics"]
    assert any("Schema" in w for w in result["warnings"])


def test_unknown_project_format_does_not_follow_current(tmp_path):
    write_json(tmp_path / "project.json", {"format_version": 99})
    write_json(tmp_path / "CURRENT.json", {"path": "../../escape", "version": "v001"})
    write_json(tmp_path / "score.json", score_fixture())
    result = load_opusmith(tmp_path)
    assert not result["events"]
    assert any("project format_version" in w for w in result["warnings"])


def test_current_snapshot_hash_and_incomplete_status(tmp_path):
    write_json(tmp_path / "project.json", {"format_version": 1})
    write_json(tmp_path / "CURRENT.json", {"path": "versions/v002", "version": "v002"})
    snap = tmp_path / "versions" / "v002"
    write_json(snap / "score.json", score_fixture())
    write_json(snap / "version.json", {"status": "complete", "sha256": {"score.json": sha256(snap / "score.json")}})
    result = load_opusmith(tmp_path)
    assert next(s for s in result["sources"] if s["path"].endswith("score.json"))["project_version"] == "v002"
    (snap / "score.json").write_text((snap / "score.json").read_text() + " ")
    with pytest.raises(ValueError, match="checksum"):
        load_opusmith(tmp_path)
    write_json(snap / "version.json", {"status": "failed"})
    with pytest.raises(ValueError, match="incomplete"):
        load_opusmith(tmp_path)


def test_semantic_score_error_safely_removes_music_events(tmp_path):
    score = score_fixture()
    score["sections"][1]["start"] = 0
    write_json(tmp_path / "score.json", score)
    result = load_opusmith(tmp_path)
    assert result["events"] == []
    assert any("語意" in w for w in result["warnings"])


@pytest.mark.parametrize("path", ["../private", "C:/private", "//server/private", "..\\private", "/private"])
def test_input_path_containment(tmp_path, path):
    with pytest.raises(ValueError):
        inside(tmp_path, path)


def test_midi_tempo_map_exact_note_times_and_lyrics(tmp_path):
    midi = mido.MidiFile(ticks_per_beat=480, charset="utf-8")
    track = mido.MidiTrack([
        mido.MetaMessage("set_tempo", tempo=500000),
        mido.MetaMessage("lyrics", text="光"),
        mido.Message("note_on", note=60, velocity=100),
        mido.MetaMessage("set_tempo", tempo=1000000, time=480),
        mido.Message("note_off", note=60, time=480),
        mido.MetaMessage("end_of_track")])
    midi.tracks.append(track)
    midi.save(tmp_path / "tempo.mid")
    result = load_midi(tmp_path / "tempo.mid", fps="24", offset_seconds="0.125")
    note = result["events"][0]
    assert (note["start_seconds"], note["end_seconds"]) == (0.125, 1.625)
    assert (note["start_frame"], note["end_frame"]) == (3, 39)
    assert result["lyrics"][0]["text"] == "光"
    assert result["lyrics"][0]["timing_precision"] == "midi-note"
    assert len(result["tempo_map"]) == 2


def test_midi_conflicting_tempo_fails(tmp_path):
    midi = mido.MidiFile()
    midi.tracks.append(mido.MidiTrack([mido.MetaMessage("set_tempo", tempo=500000)]))
    midi.tracks.append(mido.MidiTrack([mido.MetaMessage("set_tempo", tempo=600000)]))
    midi.save(tmp_path / "conflict.mid")
    with pytest.raises(ValueError, match="conflicting"):
        load_midi(tmp_path / "conflict.mid")


def test_real_ustx_provides_note_precision_not_phoneme_measurement():
    result = load_ustx(ROOT / "examples" / "opusmith-v0.2.0" / "lead.ustx")
    assert len(result["lyrics"]) == 149
    assert result["lyrics"][0]["start_seconds"] == pytest.approx(32 * 60 / 124)
    assert result["lyrics"][0]["timing_precision"] == "ustx-note"
    assert "phoneme-measured" not in str(result)


def test_vocal_alias_inventory_does_not_become_phoneme_timing(tmp_path):
    score = score_fixture()
    voice = tmp_path / "vocals" / "lead-v3"
    voice.mkdir(parents=True)
    sf.write(voice / "dry.wav", np.zeros(800), 8000)
    (voice / "project.ustx").write_text("ustx_version: '0.10'", encoding="utf-8")
    write_json(voice / "phonemes.json", [{"phonemes": [{"alias": "a", "error": False}]}])
    write_json(voice / "receipt.json", {"format_version": 1,
        "audio_sha256": sha256(voice / "dry.wav"), "ustx_sha256": sha256(voice / "project.ustx"),
        "phonemes_sha256": sha256(voice / "phonemes.json"),
        "license": {"commercial_output_verified": False}, "evaluation_only": True})
    write_json(tmp_path / "score.json", score)
    result = load_opusmith(tmp_path)
    assert "phoneme-inventory" in result["capabilities"]
    assert any("沒有音素起訖時間" in w for w in result["warnings"])
    assert any("商用" in w for w in result["warnings"])
    assert all(lyric["timing_precision"] == "score-note" for lyric in result["lyrics"])
