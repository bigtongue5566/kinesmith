"""Save installed software provenance separately from the project's asset ledger."""
from __future__ import annotations

import importlib.metadata
import json
import subprocess

from kinesmith.project import ROOT
from kinesmith.tools import ffmpeg_path, write_json


def main():
    records = []
    for dist in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata['Name'].lower()):
        meta = dist.metadata
        classifiers = meta.get_all('Classifier') or []
        licenses = [x for x in classifiers if x.startswith('License ::')]
        license_value = meta.get('License-Expression') or meta.get('License') or '; '.join(licenses)
        records.append({'name': meta['Name'], 'version': dist.version,
                        'license_metadata': license_value,
                        'project_urls': meta.get_all('Project-URL') or [],
                        'license_files': [str(p) for p in (dist.files or [])
                                          if 'license' in str(p).lower() or 'copying' in str(p).lower()]})
    output = ROOT / 'docs/software-inventory.json'
    write_json(output, {'python_packages': records,
                       'web_packages': json.loads((ROOT / 'vendor/manifest.json').read_text(encoding='utf-8'))})
    for flag, name in [('-L', 'ffmpeg-license.txt'), ('-buildconf', 'ffmpeg-buildconf.txt')]:
        result = subprocess.run([ffmpeg_path(), flag], capture_output=True)
        (ROOT / 'docs' / name).write_bytes(result.stdout + result.stderr)
    print(output)


if __name__ == '__main__':
    main()
