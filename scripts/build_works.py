"""Package verified videos and editable artifacts without raw frame caches/runtimes."""
from __future__ import annotations

import hashlib
import json
from zipfile import ZIP_DEFLATED, ZipFile

from kinesmith.project import ROOT


def main():
    entries = []
    excluded = {'.render-cache', '__pycache__', '.venv', '.cache', 'media'}
    for folder in ('examples/gallery', 'examples/collaboration', 'outputs'):
        for path in (ROOT / folder).rglob('*'):
            relative = path.relative_to(ROOT)
            if path.is_file() and not excluded.intersection(relative.parts):
                entries.append((relative.as_posix(), path))
    for path in (ROOT / 'docs').glob('*'):
        if path.is_file():
            entries.append((path.relative_to(ROOT).as_posix(), path))
    for name in ('README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md'):
        entries.append((name, ROOT / name))
    archive = ROOT / 'dist/kinesmith-works-0.1.0.zip'
    with ZipFile(archive, 'w', ZIP_DEFLATED, compresslevel=6) as stream:
        for name, path in sorted(entries):
            stream.write(path, 'kinesmith-works/' + name)
    with archive.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    evidence = {'file': archive.name, 'bytes': archive.stat().st_size,
                'sha256': digest,
                'entries': len(entries),
                'note': 'Use the matching full Plugin package for tools, pinned vendor libraries and uv.lock.'}
    (ROOT / 'dist/works-manifest.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
