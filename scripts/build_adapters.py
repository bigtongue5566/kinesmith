"""Generate native optional subagent definitions from shared role instructions."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def generate(root: Path = ROOT) -> list[Path]:
    generated = []
    for source in sorted((root / "roles").glob("*.md")):
        _, header, body = source.read_text(encoding="utf-8").split("---", 2)
        metadata = yaml.safe_load(header)
        body = body.strip() + "\n"
        claude = root / "agents" / source.name
        claude.parent.mkdir(parents=True, exist_ok=True)
        claude.write_text(
            "---\n" + yaml.safe_dump({**metadata, "model": "inherit"},
                                      sort_keys=False, allow_unicode=True) + "---\n\n" + body,
            encoding="utf-8",
        )
        name = "kinesmith_" + metadata["name"].replace("-", "_")
        codex = root / "adapters/codex/agents" / (name + ".toml")
        codex.parent.mkdir(parents=True, exist_ok=True)
        codex.write_text(
            "name = " + json.dumps(name) + "\n"
            "description = " + json.dumps(metadata["description"], ensure_ascii=False) + "\n"
            "developer_instructions = " + json.dumps(body, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        generated.extend((claude, codex))
    return generated


if __name__ == "__main__":
    print(json.dumps([str(p.relative_to(ROOT)) for p in generate()], ensure_ascii=False, indent=2))
