"""Actual delivered collaboration files must work after copying, not just synthetic data."""
import json
from pathlib import Path
import shutil

from kinesmith.interchange import rebase_contract, sha256, verify_sources
from kinesmith.project import load_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/collaboration"


def test_delivered_contracts_and_projects_use_only_copied_sources(tmp_path):
    moved = tmp_path / "moved-collaboration"
    shutil.copytree(SOURCE, moved, ignore=shutil.ignore_patterns(".render-cache", "__pycache__"))
    verified = 0
    for relative in ("music-first/music.portable.av.json", "visual-first/music-return.portable.av.json",
                     "visual-first/joint-request.portable.av.json", "visual-first/visual-request.portable.av.json"):
        path = moved / relative
        contract = json.loads(path.read_text(encoding="utf-8"))
        checks = verify_sources(contract, base=path.parent)
        assert checks and all(item["status"] in ("unchanged", "embedded") for item in checks)
        assert all(Path(item["resolved_path"]).is_relative_to(path.parent) for item in checks
                   if item["status"] != "embedded")
        relocated = rebase_contract(contract, path.parent)
        assert all(Path(item["path"]).is_relative_to(path.parent)
                   for item in relocated["sources"] + relocated["audio"]
                   if not item["path"].startswith("embedded:"))
        verified += len(checks)
    assert verified == 24
    for work in ("music-first", "visual-first"):
        project, _ = load_project(moved / work / "project-portable.json")
        assert project["interchange"].endswith(".portable.av.json")
        # Packing alternatives must not rewrite original project or music.
        assert sha256(moved / work / "project.json") == sha256(SOURCE / work / "project.json")
