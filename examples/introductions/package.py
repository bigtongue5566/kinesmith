"""Build the independently downloadable editable introduction-film collection.

Run after verify.py --render and the recorded visual review. No runtimes/raw caches.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from kinesmith.tools import sha256, write_json

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = REPO/'outputs/introductions'


def main():
    checked = json.loads((OUT/'verification.json').read_text(encoding='utf-8'))
    if set(checked) != {'kinesmith', 'codex'} or not all(
            v['technical_checks_passed'] and v['audio']['passed'] for v in checked.values()):
        raise RuntimeError('Both complete films must have measured QA evidence before packaging')
    dist = REPO/'dist/introductions'
    dist.mkdir(parents=True, exist_ok=True)
    files = []
    excluded = {'.render-cache', '__pycache__', '.cache'}
    for path in ROOT.rglob('*'):
        if path.is_file() and not excluded.intersection(path.relative_to(ROOT).parts):
            files.append((path.relative_to(REPO).as_posix(), path))
    for name in ('kinesmith-introduction.mp4', 'codex-explained.mp4', 'verification.json', 'motion-report.md', 'local-revision.json'):
        path = OUT/name
        if not path.is_file():
            raise FileNotFoundError(path)
        files.append((path.relative_to(REPO).as_posix(), path))
    for slug in ('kinesmith-introduction', 'codex-explained'):
        for suffix in ('-render.json', '-render.md'):
            path = OUT/(slug+suffix)
            files.append((path.relative_to(REPO).as_posix(), path))
    for name in ('kinesmith', 'codex'):
        for basename in ('contact-sheet.jpg', 'cut-continuity.jpg', 'qa.json', 'qa.md'):
            path = OUT/f'{name}-qa'/basename
            files.append((path.relative_to(REPO).as_posix(), path))
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'README.md'):
        files.append((name, REPO/name))
    manifest = {name: dict(bytes=path.stat().st_size, sha256=sha256(path)) for name, path in sorted(files)}
    archive = dist/'kinesmith-introductions-v1.zip'
    with ZipFile(archive, 'w', ZIP_DEFLATED, compresslevel=6) as stream:
        for name, path in sorted(files):
            stream.writestr('kinesmith/'+name, path.read_bytes())
        stream.writestr('kinesmith/introductions-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    with ZipFile(archive) as stream:
        if stream.testzip():
            raise RuntimeError('ZIP CRC check failed')
        for name, record in manifest.items():
            import hashlib
            if hashlib.sha256(stream.read('kinesmith/'+name)).hexdigest() != record['sha256']:
                raise RuntimeError(name)
    for name in ('kinesmith-introduction.mp4', 'codex-explained.mp4', 'motion-report.md'):
        shutil.copy2(OUT/name, dist/name)
    write_json(dist/'introductions-manifest.json', manifest)
    checks = '\n'.join(f'{sha256(path)}  {path.name}' for path in sorted(dist.iterdir())
                       if path.is_file() and path.name != 'SHA256SUMS')+'\n'
    (dist/'SHA256SUMS').write_text(checks, encoding='utf-8')
    print(json.dumps(dict(archive=archive.name, bytes=archive.stat().st_size,
                          entries=len(manifest), sha256=sha256(archive)), indent=2))


if __name__ == '__main__':
    main()
