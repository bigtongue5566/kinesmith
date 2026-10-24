from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_paths_and_native_adapters_are_valid():
    result = load_script("validate_plugins").validate()
    assert result["shared_roles"] == 5
    assert len(result["skills"]) == 5


def test_codex_role_install_is_idempotent_and_preserves_user_edits(tmp_path):
    installer = load_script("install_codex_roles")
    destination = installer.install(ROOT, tmp_path)
    sources = list(destination.glob("*.toml"))
    assert len(sources) == 5
    assert all(tomllib.loads(p.read_text(encoding="utf-8"))["developer_instructions"] for p in sources)
    before = {p.name: p.read_bytes() for p in sources}
    installer.install(ROOT, tmp_path)
    assert before == {p.name: p.read_bytes() for p in sources}
    modified = sources[0]
    modified.write_text(modified.read_text(encoding="utf-8") + "\n# user's customization\n", encoding="utf-8")
    untouched = sources[-1]
    untouched.unlink()
    with pytest.raises(FileExistsError):
        installer.install(ROOT, tmp_path)
    # All conflicts are checked before writing any missing role.
    assert not untouched.exists()
    assert "user's customization" in modified.read_text(encoding="utf-8")


def test_release_zip_reproducible_and_filters_runtime_caches(tmp_path):
    builder = load_script("build_release")
    (tmp_path / "src/kinesmith/__pycache__").mkdir(parents=True)
    (tmp_path / "src/kinesmith/valid.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "src/kinesmith/__pycache__/invalid.pyc").write_bytes(b"cache")
    assert [p.name for p in builder.files(tmp_path)] == ["valid.py"]
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    builder.zip_files(first, [("kinesmith/a.py", b"print(1)\n"), ("kinesmith/b.py", b"print(2)\n")])
    builder.zip_files(second, [("kinesmith/b.py", b"print(2)\n"), ("kinesmith/a.py", b"print(1)\n")])
    assert first.read_bytes() == second.read_bytes()
