from fractions import Fraction
import json
import shutil

import pytest

from kinesmith.interchange import (TempoMap, frame_at, make_visual_request, new_contract,
    rational, rebase_contract, revise_contract, sha256, validate_contract, verify_sources, write_contract)


def test_piecewise_tempo_integrates_changes_and_stays_rational():
    tempo = TempoMap([{"beat": 0, "bpm": 120}, {"beat": 4, "bpm": 90}, {"beat": 10, "bpm": 180}])
    assert tempo.seconds(4) == 2
    assert tempo.seconds(10) == 6
    assert tempo.seconds(11) == Fraction(19, 3)
    assert frame_at("1.001", "30000/1001") == 30
    assert frame_at("1.0010001", "30000/1001") == 31
    assert frame_at("-0.01", 30) == 0
    assert frame_at("-0.01", 30, rounding="floor") == -1


@pytest.mark.parametrize("points", [[], [{"beat": 1, "bpm": 120}], [{"beat": 0, "bpm": 0}],
                                     [{"beat": 0, "bpm": 120}, {"beat": 0, "bpm": 90}]])
def test_tempo_map_rejects_ambiguous_timelines(points):
    with pytest.raises(ValueError):
        TempoMap(points)


def test_visual_first_and_joint_are_portable_and_do_not_mutate_projects(tmp_path):
    project = {"schema_version": "1.0", "revision": 3, "fps": "30000/1001",
               "scenes": [{"id": "opening", "start_frame": 0, "duration_frames": 60,
                           "intent": "沉靜到明亮"},
                          {"id": "drop", "start_frame": 60, "duration_frames": 90}]}
    path = tmp_path / "project.json"
    path.write_text(json.dumps(project), encoding="utf-8")
    original = sha256(path)
    request = make_visual_request(path)
    assert request["mode"] == "visual-first"
    assert request["events"][1]["start_seconds"] == 2.002
    assert request["sources"][0]["format_version"] == "1.0"
    assert request["sources"][0]["project_version"] == "3"
    out = write_contract(tmp_path / "handoff.json", request)
    joint = revise_contract(request, request_id="picture-001", target="visual", scope="visual",
                            text="只延長結尾畫面 12 frames。", parent_sha256=sha256(out))
    assert joint["mode"] == "joint" and request["mode"] == "visual-first"
    assert joint["requests"][-1]["scope"] == "visual"
    assert sha256(path) == original
    assert verify_sources(joint)[0]["status"] == "unchanged"
    path.write_text(path.read_text() + " ")
    assert verify_sources(joint)[0]["status"] == "changed"


def test_single_scope_revision_cannot_touch_other_plugin():
    contract = new_contract(mode="joint")
    with pytest.raises(ValueError, match="scope"):
        revise_contract(contract, request_id="x", target="music", scope="visual", text="bad")


def test_unknown_contract_version_and_duplicate_request_ids_fail():
    contract = new_contract(mode="music-first")
    contract["contract_version"] = "2.0"
    with pytest.raises(ValueError, match="unsupported"):
        validate_contract(contract)
    contract = new_contract(mode="joint")
    contract = revise_contract(contract, request_id="x", target="music", scope="music", text="change")
    with pytest.raises(ValueError, match="duplicate"):
        revise_contract(contract, request_id="x", target="music", scope="music", text="again")


def test_nonfinite_times_and_invalid_frame_rate_rejected():
    with pytest.raises(ValueError):
        rational(float("nan"))
    with pytest.raises(ValueError):
        frame_at(1, 0)
    contract = new_contract(mode="music-first")
    contract["duration"]["timeline_seconds"] = float("inf")
    with pytest.raises(ValueError):
        validate_contract(contract)


def test_handoff_refuses_to_overwrite_original_source(tmp_path):
    path = tmp_path / "project.json"
    path.write_text('{"fps":"24","scenes":[]}', encoding="utf-8")
    contract = make_visual_request(path)
    original = sha256(path)
    with pytest.raises(ValueError, match="must not overwrite"):
        write_contract(path, contract)
    assert sha256(path) == original


def test_portable_contract_moves_only_after_declared_path_and_hash_match(tmp_path):
    original, moved = tmp_path / "original", tmp_path / "moved"
    original.mkdir()
    project = original / "project.json"
    project.write_text('{"fps":"24","scenes":[]}', encoding="utf-8")
    contract = make_visual_request(project)
    write_contract(original / "request.av.json", contract)
    saved = json.loads((original / "request.av.json").read_text(encoding="utf-8"))
    assert saved["sources"][0]["relative_path"] == "project.json"
    assert "relative_path" not in contract["sources"][0], "export must not mutate caller data"
    shutil.copytree(original, moved)
    # The original may remain accessible; relocation must still choose ONLY base.
    assert verify_sources(saved, base=moved)[0]["resolved_path"] == str(moved / "project.json")
    relocated = rebase_contract(saved, moved)
    assert relocated["sources"][0]["path"] == str(moved / "project.json")
    assert saved["sources"][0]["path"] == str(project)
    assert verify_sources(relocated)[0]["status"] == "unchanged"
    (moved / "project.json").write_text("changed", encoding="utf-8")
    assert verify_sources(saved, base=moved)[0]["status"] == "changed"
    with pytest.raises(ValueError, match="checksum"):
        rebase_contract(saved, moved)


@pytest.mark.parametrize("relative", ["../project.json", "C:/project.json", "/project.json", "..\\project.json"])
def test_rebase_rejects_traversal_even_if_original_is_available(tmp_path, relative):
    source = tmp_path / "project.json"
    source.write_text('{"fps":"24","scenes":[]}', encoding="utf-8")
    contract = make_visual_request(source)
    contract["sources"][0]["relative_path"] = relative
    with pytest.raises(ValueError, match="unsafe"):
        rebase_contract(contract, tmp_path)


def test_export_removes_ambiguous_external_source_root_relative_paths(tmp_path):
    original, target = tmp_path / "external", tmp_path / "package"
    original.mkdir()
    target.mkdir()
    path = original / "project.json"
    path.write_text('{"fps":"24","scenes":[]}', encoding="utf-8")
    contract = make_visual_request(path)
    contract["sources"][0]["relative_path"] = "project.json"
    write_contract(target / "contract.json", contract)
    saved = json.loads((target / "contract.json").read_text(encoding="utf-8"))
    assert "relative_path" not in saved["sources"][0]
    with pytest.raises(ValueError, match="external source"):
        rebase_contract(saved, target)


def test_rebase_verifies_audio_too_and_never_changes_sources(tmp_path):
    path = tmp_path / "audio.wav"
    path.write_bytes(b"fixture-audio-bytes")
    contract = new_contract(mode="music-first")
    contract["audio"] = [{"path": "old-location/audio.wav", "relative_path": "audio.wav",
                          "sha256": sha256(path), "role": "master", "offset_seconds": 0,
                          "measured": True, "duration_seconds": 1}]
    relocated = rebase_contract(contract, tmp_path)
    assert relocated["audio"][0]["path"] == str(path)
    assert verify_sources(relocated)[0]["status"] == "unchanged"
    assert path.read_bytes() == b"fixture-audio-bytes"
