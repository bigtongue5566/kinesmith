"""Fetch pinned upstream distributions with npm registry integrity verification.

uv run scripts/bootstrap_web.py [--chromium]
No npm runtime or CDN is needed for renders after this one-time bootstrap.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    'roughjs': ('4.6.6', {'bundled/rough.js': 'rough/rough.js'}),
    'p5': ('1.11.11', {'lib/p5.min.js': 'p5/p5.min.js'}),
    'three': ('0.180.0', {'build/three.module.min.js': 'three/three.module.min.js',
                           'build/three.core.min.js': 'three/three.core.min.js'}),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium', action='store_true')
    args = parser.parse_args()
    vendor = ROOT / 'vendor'
    vendor.mkdir(exist_ok=True)
    records = []
    for package, (version, files) in PACKAGES.items():
        url = f'https://registry.npmjs.org/{package}/{version}'
        with urllib.request.urlopen(url, timeout=60) as response:
            metadata = json.load(response)
        dist = metadata['dist']
        with urllib.request.urlopen(dist['tarball'], timeout=120) as response:
            archive = response.read()
        algorithm, digest = dist['integrity'].split('-', 1)
        if algorithm != 'sha512' or base64.b64encode(hashlib.sha512(archive).digest()).decode() != digest:
            raise ValueError(f'Integrity mismatch: {package}')
        archive_path = vendor / 'source' / f'{package}-{version}.tgz'
        archive_path.parent.mkdir(exist_ok=True)
        archive_path.write_bytes(archive)
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
            for source, target in files.items():
                path = vendor / target
                path.parent.mkdir(parents=True, exist_ok=True)
                stream = tar.extractfile(f'package/{source}')
                path.write_bytes(stream.read())
            licenses = [m for m in tar.getmembers() if m.isfile() and
                        m.name.lower().split('/')[-1] in ('license', 'license.md', 'license.txt', 'copying')]
            for n, member in enumerate(licenses):
                path = vendor / f'{package}-LICENSE{n or ""}.txt'
                path.write_bytes(tar.extractfile(member).read())
        records.append({'name': package, 'version': version, 'license': metadata['license'],
                        'source': url, 'tarball': dist['tarball'], 'integrity': dist['integrity'],
                        'files': {target: hashlib.sha256((vendor / target).read_bytes()).hexdigest()
                                  for target in files.values()}})
        print(f'{package}@{version}: verified SHA512, installed')
    (vendor / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    if args.chromium:
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)


if __name__ == '__main__':
    main()
