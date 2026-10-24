"""Build portable alternatives next to audited originals, then verify a moved copy.

uv run python scripts/verify_collaboration_portability.py
Original AV/project files and music/audio/source remain unchanged. Four
*.portable.av.json and two project-portable.json files reference the existing
editable work, without duplicating it. Evidence lives in examples/collaboration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from kinesmith.interchange import rebase_contract, sha256, verify_sources, write_contract
from kinesmith.project import load_project


ROOT = Path(__file__).resolve().parents[1]
WORKS = {"music-first": ["music.av.json"],
         "visual-first": ["music-return.av.json", "joint-request.av.json", "visual-request.av.json"]}


def portable_name(filename: str) -> str:
    return filename.removesuffix(".av.json") + ".portable.av.json"


def prepare_portable_examples(source: Path) -> tuple[list[dict], dict[Path, str]]:
    records, protected = [], {}
    for name, filenames in WORKS.items():
        folder = source / name
        for filename in filenames:
            path = folder / filename
            protected[path] = sha256(path)
            value = json.loads(path.read_text(encoding="utf-8"))
            for item in value["sources"] + value["audio"]:
                if item["path"].startswith("embedded:"):
                    continue
                original = Path(item["path"]).resolve()
                if not original.is_relative_to(folder):
                    raise ValueError(f"active contract still references external source: {original}")
                protected[original] = sha256(original)
                item["relative_path"] = original.relative_to(folder).as_posix()
            # Verify every source and audio hash before exporting an alternative.
            value = rebase_contract(value, folder)
            alternative = folder / portable_name(filename)
            write_contract(alternative, value)
            records.append({"original": f"{name}/{filename}",
                            "portable": f"{name}/{alternative.name}",
                            "original_sha256": protected[path], "portable_sha256": sha256(alternative)})
        picture = folder / "project.json"
        protected[picture] = sha256(picture)
        project = json.loads(picture.read_text(encoding="utf-8"))
        project["interchange"] = portable_name(project["interchange"])
        (folder / "project-portable.json").write_text(
            json.dumps(project, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        load_project(folder / "project-portable.json")
    assert all(sha256(path) == expected for path, expected in protected.items()), "original files changed"
    return records, protected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "examples/collaboration")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/collaboration-moved")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    alternatives, protected = prepare_portable_examples(source)
    if output.exists():
        # Keep an earlier acceptance run intact; never recursively delete inputs.
        index = 1
        while output.with_name(output.name + f"-{index}").exists():
            index += 1
        output = output.with_name(output.name + f"-{index}")
    output.mkdir(parents=True)
    shutil.copytree(source, output, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".render-cache", "__pycache__"))
    records = []
    for name, contracts in WORKS.items():
        moved = output / name
        for filename in contracts:
            target = moved / portable_name(filename)
            portable = json.loads(target.read_text(encoding="utf-8"))
            # Verification uses moved relative paths while original absolute
            # paths are still present. No fallback to the originals is allowed.
            checks = verify_sources(portable, base=target.parent)
            assert all(item["status"] in ("unchanged", "embedded") for item in checks)
            assert all(Path(item["resolved_path"]).is_relative_to(moved) for item in checks
                       if item["status"] != "embedded")
            relocated = rebase_contract(portable, moved)
            write_contract(moved / (target.stem + ".rebased.json"), relocated)
            records.append({"contract": f"{name}/{target.name}", "references_verified": len(checks),
                            "all_sources_inside_moved_work": True,
                            "explicit_rebase_verified": True})
        load_project(moved / "project-portable.json")
    assert all(sha256(path) == expected for path, expected in protected.items()), "original files changed"
    evidence = {"status": "portable-alternatives-created-copied-and-hash-verified", "destination": str(output),
                "alternatives": alternatives, "records": records,
                "original_files_verified_unchanged": len(protected), "original_sources_modified": False,
                "editable_music_copies_added_to_examples": 0,
                "scope": "移動來源與合約核對及 project validation；本次不宣稱重新編碼或主觀品質驗收。"}
    (source / "portability.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "portability.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
