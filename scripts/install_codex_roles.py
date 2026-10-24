"""Install Kinesmith native Codex agents in a chosen project, without replacing user edits."""

from __future__ import annotations

import argparse
from pathlib import Path


def install(plugin: Path, project: Path) -> Path:
    sources = sorted((plugin / "adapters/codex/agents").glob("kinesmith_*.toml"))
    if len(sources) != 5:
        raise ValueError("Expected five generated Kinesmith Codex role definitions")
    destination = project.resolve() / ".codex/agents"
    # Validate all conflicts before creating any files.
    for source in sources:
        target = destination / source.name
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise FileExistsError(f"Refusing to overwrite modified role: {target}")
    destination.mkdir(parents=True, exist_ok=True)
    for source in sources:
        target = destination / source.name
        if not target.exists():
            target.write_bytes(source.read_bytes())
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    print(install(Path(__file__).resolve().parents[1], args.project))
