"""Validate shared packaging; optionally exercise native platform CLIs without model calls."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib
import uuid

import yaml

from install_codex_roles import install

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {"kinesmith", "kinesmith-setup", "kinesmith-render", "kinesmith-audio-visual", "kinesmith-revise"}


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Missing frontmatter: {path}")
    return yaml.safe_load(text.split("---", 2)[1])


def validate(root: Path = ROOT) -> dict:
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    for path in (root / "plugin.json", root / ".codex-plugin/plugin.json", root / ".claude-plugin/plugin.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["name"] != "kinesmith" or data["version"] != version:
            raise ValueError(f"Manifest identity mismatch: {path}")
    actual = {p.parent.name for p in (root / "skills").glob("*/SKILL.md")}
    if actual != SKILLS:
        raise ValueError(f"Missing or unexpected skills: {actual}")
    broken_links = []
    for path in (root / "skills").rglob("*.md"):
        if path.name == "SKILL.md":
            metadata = frontmatter(path)
            if metadata["name"] != path.parent.name or not metadata.get("description"):
                raise ValueError(f"Invalid Skill metadata: {path}")
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" not in link and not link.startswith("#"):
                target = (path.parent / link.split("#")[0]).resolve()
                if not target.is_relative_to(root.resolve()) or not target.exists():
                    broken_links.append({"file": str(path), "link": link})
    if broken_links:
        raise ValueError(f"Broken skill links: {broken_links}")
    roles = list((root / "roles").glob("*.md"))
    if len(roles) != 5:
        raise ValueError("Expected five shared role definitions")
    for role in roles:
        metadata = frontmatter(role)
        claude = frontmatter(root / "agents" / role.name)
        codex_path = root / "adapters/codex/agents" / ("kinesmith_" + role.stem.replace("-", "_") + ".toml")
        codex = tomllib.loads(codex_path.read_text(encoding="utf-8"))
        body = role.read_text(encoding="utf-8").split("---", 2)[2].strip()
        if (claude["name"] != metadata["name"] or claude.get("model") != "inherit"
                or "model" in codex or codex["developer_instructions"].strip() != body):
            raise ValueError(f"Role adapter drift: {role}")
    return {"status": "passed", "skills": sorted(actual), "shared_roles": len(roles), "version": version}


def rpc_skills(executable: str, cwd: Path, env: dict) -> dict:
    """Call app-server discovery only; never create a model turn."""
    process = subprocess.Popen([executable, "app-server", "--stdio"], cwd=cwd, env=env,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, encoding="utf-8", errors="replace")
    messages: queue.Queue = queue.Queue()

    def reader():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                continue

    threading.Thread(target=reader, daemon=True).start()

    def request(identifier, method, params):
        process.stdin.write(json.dumps({"id": identifier, "method": method, "params": params}) + "\n")
        process.stdin.flush()
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            try:
                message = messages.get(timeout=min(1, max(.01, deadline-time.monotonic())))
            except queue.Empty:
                continue
            if message.get("id") == identifier:
                return message
        raise TimeoutError(f"Native discovery timeout: {method}")

    try:
        initialized = request(1, "initialize", {"clientInfo": {"name": "kinesmith-validator", "version": "0.1.0"},
                                                "capabilities": {"experimentalApi": True}})
        if "error" in initialized:
            return initialized
        process.stdin.write(json.dumps({"method": "initialized", "params": {}}) + "\n")
        process.stdin.flush()
        return request(2, "skills/list", {"cwds": [str(cwd)], "forceReload": True})
    finally:
        process.kill()
        process.wait(timeout=10)


def native(root: Path = ROOT, claude: str | None = None, render_smoke: bool = False) -> dict:
    package = root / "dist/marketplace/plugins/kinesmith"
    if not package.exists():
        raise FileNotFoundError("Run uv run scripts/build_release.py first")
    sandbox = root / ".cache" / ("platform-validation-" + uuid.uuid4().hex[:8])
    sandbox.mkdir(parents=True)
    project = sandbox / "motion-project"
    project.mkdir()
    install(package, project)
    commands = []

    def run(platform, executable, arguments, environment, working_directory=None, agent_inventory=False):
        try:
            process = subprocess.run([executable, *arguments], cwd=working_directory or sandbox, env=environment,
                                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            result = {"platform": platform, "arguments": arguments, "exit_code": process.returncode,
                      "stdout": process.stdout[-15000:], "stderr": process.stderr[-3000:]}
            if agent_inventory and process.returncode == 0:
                payload = json.loads(process.stdout)
                descriptions = [tool.get("parameters", {}).get("properties", {}).get("agent_type", {}).get("description", "")
                                for entry in payload for namespace in entry.get("tools", [])
                                for tool in namespace.get("tools", []) if tool.get("name") == "spawn_agent"]
                description = "\n".join(descriptions)
                result["stdout"] = "完整 model-visible prompt 未收錄；只保留原生 agent_type inventory。"
                result["agent_type_description"] = description
                result["roles_found"] = [p.stem for p in (project / ".codex/agents").glob("*.toml")
                                         if p.stem + ":" in description]
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            result = {"platform": platform, "arguments": arguments, "error": str(exc)}
        commands.append(result)
        return result

    codex = shutil.which("codex")
    claude = claude or shutil.which("claude")
    # These environment keys retain their documented platform-config meaning.
    # They isolate validation from the user's real account settings and credentials.
    codex_env = {**os.environ, "CODEX_HOME": str(sandbox / "codex-config")}
    claude_env = {**os.environ, "CLAUDE_CONFIG_DIR": str(sandbox / "claude-config"),
                  "DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
    (sandbox / "codex-config").mkdir()
    discovery = None
    if codex:
        run("codex", codex, ["--version"], codex_env)
        run("codex", codex, ["plugin", "marketplace", "add", str(root / "dist/marketplace"), "--json"], codex_env)
        run("codex", codex, ["plugin", "add", "kinesmith@kinesmith-local", "--json"], codex_env)
        run("codex", codex, ["plugin", "list", "--marketplace", "kinesmith-local", "--json"], codex_env)
        # Trust only this generated fixture, so Codex reads its project-scoped agents.
        # The real user project and global settings are never changed by this harness.
        config = sandbox / "codex-config/config.toml"
        with config.open("a", encoding="utf-8") as stream:
            stream.write("\n[projects." + json.dumps(str(project)) + "]\ntrust_level = \"trusted\"\n")
        inventory = run("codex-agents", codex, ["debug", "prompt-input"], codex_env,
                        working_directory=project, agent_inventory=True)
        try:
            discovery = rpc_skills(codex, project, codex_env)
        except (OSError, TimeoutError) as exc:
            discovery = {"error": str(exc)}
    if claude:
        run("claude", claude, ["--version"], claude_env)
        run("claude", claude, ["plugin", "validate", str(package)], claude_env)
        run("claude", claude, ["plugin", "validate", str(package / "agents")], claude_env)
        run("claude", claude, ["plugin", "marketplace", "add", str(root / "dist/marketplace")], claude_env)
        run("claude", claude, ["plugin", "install", "kinesmith@kinesmith-local", "--scope", "user", "--json"], claude_env)
        run("claude", claude, ["plugin", "list", "--json"], claude_env)
        claude_inventory = run("claude-components", claude,
                               ["plugin", "details", "kinesmith@kinesmith-local"], claude_env)
    installed = {}
    for platform, config in (("codex", "codex-config"), ("claude", "claude-config")):
        # Avoid descending into opaque renderer caches or exceeding Windows path limits.
        matches = [p / "skills/kinesmith/SKILL.md"
                   for p in (sandbox / config / "plugins/cache/kinesmith-local/kinesmith").glob("*")
                   if (p / "skills/kinesmith/SKILL.md").is_file()]
        installed[platform] = []
        for skill in matches:
            installed_root = skill.parents[2]
            if installed_root == package:
                continue
            installed[platform].append({
                "root": str(installed_root),
                "skills": [p.parent.name for p in (installed_root / "skills").glob("*/SKILL.md")],
                "claude_agents": [p.name for p in (installed_root / "agents").glob("*.md")],
                "source_matches": all((installed_root / p).read_bytes() == (package / p).read_bytes()
                                      for p in ("src/kinesmith/__init__.py", "plugin.json")),
            })
            uv = shutil.which("uv")
            if uv:
                prefix = ["run", "--offline", "--no-dev", "--python", sys.executable,
                          "--project", str(installed_root), "kinesmith"]
                runtime_env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
                canvas_project = installed_root / "examples/gallery/project-canvas.json"
                run(platform + "-runtime", uv, [*prefix, "validate", str(canvas_project)], runtime_env)
                if render_smoke:
                    # Copy the source to a short workspace path before rendering; never modify installed examples.
                    work = sandbox / (platform + "-render")
                    shutil.copytree(installed_root / "examples/gallery", work,
                                    ignore=shutil.ignore_patterns(".render-cache", "renders", "media", "__pycache__"))
                    run(platform + "-render", uv,
                        [*prefix, "render", str(work / "project-canvas.json"),
                         "--output", str(work / "canvas.webm")], runtime_env)
    serialized = json.dumps(discovery, ensure_ascii=False)
    skill_discovery_passed = all(name in serialized for name in SKILLS) and "error" not in (discovery or {})
    codex_agents_passed = bool(codex and len(inventory.get("roles_found", [])) == 5)
    claude_roles = [p.stem for p in (root / "agents").glob("*.md")]
    claude_inventory_passed = bool(claude and claude_inventory.get("exit_code") == 0 and all(
        name in claude_inventory.get("stdout", "") for name in [*SKILLS, *claude_roles]))
    result = {
        "static": validate(root), "commands": commands, "codex_skill_discovery": discovery,
        "codex_skill_discovery_passed": skill_discovery_passed,
        "codex_native_agent_inventory_passed": codex_agents_passed,
        "claude_component_inventory_passed": claude_inventory_passed,
        "installed": installed, "codex_project_role_files": [str(p) for p in (project / ".codex/agents").glob("*.toml")],
        "model_invocations": 0,
        "limits": ["未執行已登入模型的自然語言創作。", "兩平台已探索五個可用原生角色，但未實際委派模型執行。",
                   "原生 inventory、validator 及安裝後渲染成功，不等於模型已呼叫 Skills。"],
    }
    failures = [r for r in commands if r.get("exit_code") != 0]
    source_copies_match = all(item["source_matches"] for items in installed.values() for item in items)
    result["status"] = "passed" if (not failures and all(installed.values()) and source_copies_match and skill_discovery_passed
                                       and codex_agents_passed and claude_inventory_passed) else "incomplete"
    output = root / "outputs/platform-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "docs/platform-validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--claude", type=str)
    parser.add_argument("--render-smoke", action="store_true", help="Render Canvas from each installed copy")
    args = parser.parse_args()
    result = native(claude=args.claude, render_smoke=args.render_smoke) if args.native else validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)
