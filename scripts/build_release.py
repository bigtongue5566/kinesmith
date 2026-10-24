"""Build reproducible installable Plugin and two native local marketplaces."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = (
    "plugin.json", ".codex-plugin", ".claude-plugin", "skills", "roles", "agents", "adapters",
    "scripts", "src", "schemas", "tests", "docs", "examples", "vendor", "licenses", "assets",
    "pyproject.toml", "uv.lock", "package.json", "package-lock.json", "README.md", "LICENSE",
    "THIRD_PARTY_NOTICES.md", "AGENTS.md",
)
SKIP = {"__pycache__", ".venv", ".cache", "node_modules", ".git", ".pytest_cache", ".render-cache", "renders"}


def files(root: Path):
    for item in INCLUDE:
        path = root / item
        if not path.exists():
            continue
        for file in ([path] if path.is_file() else sorted(path.rglob("*"))):
            relative = file.relative_to(root)
            if (file.is_file() and not SKIP.intersection(relative.parts)
                    and file.suffix not in {".pyc", ".pyo"}):
                yield file


def zip_files(archive: Path, entries):
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=6) as zipped:
        for name, data in sorted(entries):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, data)


def build(root: Path = ROOT) -> dict:
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    for manifest in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        if json.loads((root / manifest).read_text(encoding="utf-8"))["version"] != version:
            raise ValueError(f"Version mismatch: {manifest}")
    selected = list(files(root))
    if not (root / "vendor").exists():
        raise FileNotFoundError("Run uv run scripts/bootstrap_web.py to bundle browser engines and licenses")
    dist = root / "dist"
    if not dist.resolve().is_relative_to(root.resolve()):
        raise ValueError("Release directory must remain inside the project")
    dist.mkdir(exist_ok=True)
    marketplace = dist / "marketplace"
    package = marketplace / "plugins/kinesmith"
    # Recreate only this verified generated directory, including stale empty cache dirs.
    if package.is_symlink() or not package.resolve().is_relative_to(dist.resolve()):
        raise ValueError("Generated package must not be a symlink")
    if package.exists():
        marker = package / "plugin.json"
        if not marker.is_file() or json.loads(marker.read_text(encoding="utf-8")).get("name") != "kinesmith":
            raise ValueError("Refusing to replace an unrecognized generated package")
        shutil.rmtree(package)
    package.mkdir(parents=True)
    entries = []
    source_hashes = {}
    for file in selected:
        relative = file.relative_to(root)
        target = package / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)
        data = file.read_bytes()
        entries.append(("kinesmith/" + relative.as_posix(), data))
        source_hashes[relative.as_posix()] = hashlib.sha256(data).hexdigest()
    catalogs = {
        ".agents/plugins/marketplace.json": {
            "name": "kinesmith-local", "interface": {"displayName": "Kinesmith Local"},
            "plugins": [{"name": "kinesmith", "source": {"source": "local", "path": "./plugins/kinesmith"},
                         "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                         "category": "Productivity"}],
        },
        ".claude-plugin/marketplace.json": {
            "name": "kinesmith-local", "owner": {"name": "Kinesmith contributors"},
            "plugins": [{"name": "kinesmith", "source": "./plugins/kinesmith"}],
        },
    }
    for name, catalog in catalogs.items():
        target = marketplace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive = dist / f"kinesmith-{version}.zip"
    zip_files(archive, entries)
    catalog_archive = dist / f"kinesmith-marketplace-{version}.zip"
    catalog_entries = [("kinesmith-marketplace/" + p.relative_to(marketplace).as_posix(), p.read_bytes())
                       for p in marketplace.rglob("*") if p.is_file()]
    zip_files(catalog_archive, catalog_entries)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (archive, catalog_archive)}
    (dist / "SHA256SUMS.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    (dist / "source-manifest.json").write_text(json.dumps(source_hashes, indent=2) + "\n", encoding="utf-8")
    return {"version": version, "plugin": str(archive), "marketplace": str(catalog_archive),
            "files": len(selected), "sha256": hashes}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=False))
