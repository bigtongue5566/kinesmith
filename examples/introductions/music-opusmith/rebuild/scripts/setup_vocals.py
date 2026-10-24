"""Optional local OpenUtau bootstrap using official, hash-pinned distributions.

No voicebank/model is bundled with the plugin. Python is run through uv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
from zipfile import ZipFile

import httpx

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT/"skills/opusmith/references/vocals/voicebanks.json"


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def download(url: str, path: Path, expected: str, *, maximum=600_000_000):
    """Only pinned official HTTPS downloads; redirects remain HTTPS."""
    if not expected or len(expected) != 64 or not url.startswith("https://"):
        raise ValueError("expected HTTPS URL and pinned SHA256")
    if path.exists() and sha(path) == expected:
        return
    partial = path.with_suffix(path.suffix+".part")
    try:
        with httpx.Client(timeout=120, follow_redirects=False) as client:
            for redirect in range(6):
                with client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = str(response.url.join(response.headers["location"]))
                        if not url.startswith("https://"):
                            raise ValueError("insecure redirect")
                        continue
                    response.raise_for_status()
                    total = 0
                    with partial.open("wb") as out:
                        for block in response.iter_bytes(1024*1024):
                            total += len(block)
                            if total > maximum:
                                raise ValueError("download too large")
                            out.write(block)
                    break
            else:
                raise ValueError("too many redirects")
        if sha(partial) != expected:
            raise ValueError("download hash mismatch; do not silently accept a replaced asset")
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def extract(archive: Path, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive, metadata_encoding="cp932") as zip:
        if sum(i.file_size for i in zip.infolist()) > 3_000_000_000:
            raise ValueError("expanded archive too large")
        for info in zip.infolist():
            name = info.filename.replace("\\", "/")
            if ":" in name or name.startswith("/") or ".." in name.split("/"):
                raise ValueError("unsafe archive member")
            target = (destination/name).resolve()
            if not target.is_relative_to(destination.resolve()) or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("unsafe archive path/symlink")
        zip.extractall(destination)


def setup(directory: Path, bank_id: str, dotnet: Path, *, engine: Path | None = None,
          evaluation=False):
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    bank = catalog["banks"][bank_id]
    if not bank["license"]["commercial_output_verified"] and not evaluation:
        raise ValueError("This bank is evaluation-only; use --evaluation to acknowledge its review status")
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if engine is None:
        if platform.system() != "Windows" or platform.machine().lower() not in {"amd64", "x86_64"}:
            raise ValueError("Automatic engine download is Windows x64; supply --engine-dir for a matching official 0.1.576 runtime on other OSes (untested)")
        engine = directory/"OpenUtau"
        spec = catalog["engine"]
        download(spec["url"], directory/"OpenUtau-win-x64.zip", spec["sha256"])
        extract(directory/"OpenUtau-win-x64.zip", engine)
    engine = engine.resolve()
    if not (engine/"OpenUtau.Core.dll").is_file():
        raise ValueError("--engine-dir must contain the extracted OpenUtau.Core.dll")
    archive = directory/(bank_id+".zip")
    download(bank["url"], archive, bank["sha256"])
    singers = directory/bank_id
    extract(archive, singers)
    data = directory/"runtime"
    if "vocoder" in bank:
        vocoder = bank["vocoder"]
        package = directory/(vocoder["id"]+".oudep")
        download(vocoder["url"], package, vocoder["sha256"])
        extract(package, data/"Dependencies"/vocoder["id"])
    data.mkdir(exist_ok=True)
    env = {**os.environ, "DOTNET_CLI_HOME": str(directory/"dotnet-home"),
           "NUGET_PACKAGES": str(directory/"nuget"), "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
           "DOTNET_GENERATE_ASPNET_CERTIFICATE": "false"}
    build = directory/"bridge"
    subprocess.run([str(dotnet), "build", str(ROOT/"adapters/openutau/Opusmith.OpenUtau.csproj"),
                    "-p:RestoreLockedMode=true", "-c", "Release", f"-p:OpenUtauDir={engine}",
                    "-o", str(build)], check=True, env=env, timeout=180)
    for file in build.iterdir():
        if file.is_file():
            shutil.copyfile(file, engine/file.name)
    settings = {"bank_id": bank_id, "engine": str(engine), "dotnet": str(dotnet.resolve()),
        "singers": str(singers), "bank": str(singers/bank["folder"]), "data": str(data),
        "license_record": bank["license"], "evaluation": evaluation}
    settings_path = directory/(bank_id+"-settings.json")
    settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"設定：{settings_path}\n聲庫：{bank['name']}\n只在本機下載；未上傳或重分發聲庫。")
    return settings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", choices=["ritsu-kire", "qixuan"], default="ritsu-kire")
    parser.add_argument("--directory", type=Path, default=ROOT/".cache/vocal-tools")
    parser.add_argument("--dotnet", type=Path, default=Path(shutil.which("dotnet") or "dotnet"))
    parser.add_argument("--engine-dir", type=Path)
    parser.add_argument("--evaluation", action="store_true")
    args = parser.parse_args()
    setup(args.directory, args.bank, args.dotnet, engine=args.engine_dir, evaluation=args.evaluation)
