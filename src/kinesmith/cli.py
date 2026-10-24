"""An intentionally small argparse interface around independent production helpers."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

from .project import ROOT, load_project, revise_project


def doctor() -> dict:
    from playwright.sync_api import sync_playwright
    from .render import versions
    data = {'versions': versions(), 'vendor': (ROOT / 'vendor/manifest.json').exists(),
            'manim': importlib.util.find_spec('manim') is not None,
            'blender': importlib.util.find_spec('bpy') is not None,
            'browser': None, 'browser_error': None}
    try:
        with sync_playwright() as p:
            options = {'headless': True}
            if os.environ.get('KINESMITH_CHROMIUM'):
                options['executable_path'] = os.environ['KINESMITH_CHROMIUM']
            browser = p.chromium.launch(**options)
            data['browser'] = browser.version
            browser.close()
    except Exception as exc:
        data['browser_error'] = str(exc)
    data['ready'] = bool(data['browser'] and data['vendor'])
    data['all_engines_ready'] = data['ready'] and data['manim'] and data['blender']
    return data


def init_project(destination: str) -> dict:
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f'不覆寫既有路徑：{destination}')
    source = ROOT / 'examples/gallery'
    if not source.is_dir():
        raise FileNotFoundError('Plugin 缺少 examples/gallery，請使用完整發行包')
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('.render-cache', 'renders', '__pycache__', 'media'))
    return {'project': str(destination / 'project.json')}


def main(argv=None):
    # Windows legacy consoles may default to cp950 even when JSON contains CJK.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(prog='kinesmith', description='Craft motion, not just animate it.')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor', help='實際檢查工具與瀏覽器啟動')
    p = sub.add_parser('init', help='複製可編輯六引擎作品作為起點')
    p.add_argument('destination')
    p = sub.add_parser('validate', help='驗證作品 Schema、時間軸與來源')
    p.add_argument('project')
    p = sub.add_parser('render', help='渲染原生來源並合成')
    p.add_argument('project')
    p.add_argument('--scene', help='搭配 --force 只強制重建此場景；其他場景照雜湊快取')
    p.add_argument('--format', choices=['webm', 'mp4', 'gif', 'png'], default='webm')
    p.add_argument('--output')
    p.add_argument('--force', action='store_true')
    p = sub.add_parser('analyze', help='一般音訊的 energy／frequency／估計 onset')
    p.add_argument('audio')
    p.add_argument('--output', required=True)
    p = sub.add_parser('qa', help='完整解碼、客觀量測與代表影格')
    p.add_argument('video')
    p.add_argument('--output-dir', '--output', dest='output_dir', required=True)
    p.add_argument('--project', help='作品提供預期時長／尺寸／FPS')
    p = sub.add_parser('import-opusmith', help='唯讀匯入實際音樂專案或 MIDI／USTX')
    p.add_argument('source')
    p.add_argument('--output', required=True)
    p.add_argument('--fps', default='30')
    p.add_argument('--offset', type=float, default=0)
    p.add_argument('--audio')
    p.add_argument('--version')
    p = sub.add_parser('handoff', help='Visual-first 可攜配樂需求，不直接呼叫其他 Plugin')
    p.add_argument('project')
    p.add_argument('--output', required=True)
    p.add_argument('--request', default='請依場景情緒與指定 cue 創作配樂。')
    p = sub.add_parser('joint-request', help='建立限定範圍的雙向修訂需求')
    p.add_argument('contract')
    p.add_argument('--output', required=True)
    p.add_argument('--id', required=True)
    p.add_argument('--target', choices=['visual', 'music'], required=True)
    p.add_argument('--scope', choices=['visual', 'music', 'both'], required=True)
    p.add_argument('--request', required=True)
    p = sub.add_parser('verify-sources', help='核對關聯作品的 SHA256')
    p.add_argument('contract')
    p = sub.add_parser('rebase-contract', help='搬移作品後，先驗 SHA256 再明確重定位交接來源')
    p.add_argument('contract')
    p.add_argument('--base', required=True)
    p.add_argument('--output', required=True)
    p = sub.add_parser('revise', help='保存來源版本與 Prompt，局部更換場景參數／來源')
    p.add_argument('project')
    p.add_argument('--scene', required=True)
    p.add_argument('--prompt', required=True)
    p.add_argument('--source')
    p.add_argument('--params', help='場景原生參數的 JSON object')
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            result = doctor()
        elif args.command == 'init':
            result = init_project(args.destination)
        elif args.command == 'validate':
            project, path = load_project(args.project)
            result = {'valid': True, 'path': str(path), 'scenes': len(project['scenes'])}
        elif args.command == 'render':
            from .render import render_project
            result = render_project(args.project, output=args.output, fmt=args.format,
                                    scene_id=args.scene, force=args.force)
            result = {k: result[k] for k in ('output', 'output_sha256', 'measured', 'revision') if k in result}
        elif args.command == 'analyze':
            from .audio import analyze_audio
            data = analyze_audio(args.audio, args.output)
            result = {'output': args.output, 'duration_seconds': data['duration_seconds']}
        elif args.command == 'qa':
            from .qa import qa_video
            expected = None
            if args.project:
                from .tools import frame_seconds
                p, _ = load_project(args.project)
                expected = {k: p[k] for k in ('width', 'height', 'fps')}
                expected['duration_seconds'] = frame_seconds(p['duration_frames'], p['fps'])
            result = qa_video(args.video, args.output_dir, expected)
        elif args.command == 'import-opusmith':
            from .opusmith import load_opusmith
            from .interchange import write_contract
            data = load_opusmith(args.source, fps=args.fps, offset_seconds=args.offset,
                                  audio=args.audio, version=args.version)
            write_contract(args.output, data)
            result = {'output': args.output, 'capabilities': data['capabilities'],
                      'duration': data['duration'], 'warnings': data['warnings']}
        elif args.command == 'handoff':
            from .interchange import make_visual_request, write_contract
            _, path = load_project(args.project)
            data = make_visual_request(path, request=args.request)
            write_contract(args.output, data)
            result = {'output': args.output, 'mode': data['mode'], 'requests': data['requests']}
        elif args.command == 'joint-request':
            from .interchange import revise_contract, write_contract
            from .tools import sha256
            data = json.loads(Path(args.contract).read_text(encoding='utf-8'))
            result = revise_contract(data, request_id=args.id, target=args.target, scope=args.scope,
                                     text=args.request, parent_sha256=sha256(args.contract))
            write_contract(args.output, result)
            result = {'output': args.output, 'mode': result['mode'], 'requests': result['requests']}
        elif args.command == 'verify-sources':
            from .interchange import verify_sources
            result = verify_sources(json.loads(Path(args.contract).read_text(encoding='utf-8')),
                                    base=Path(args.contract).resolve().parent)
        elif args.command == 'rebase-contract':
            from .interchange import rebase_contract, write_contract
            data = json.loads(Path(args.contract).read_text(encoding='utf-8'))
            result = rebase_contract(data, args.base)
            write_contract(args.output, result)
            result = {'output': args.output, 'sources': len(result['sources']), 'audio': len(result['audio'])}
        elif args.command == 'revise':
            data = revise_project(args.project, args.scene, args.prompt, args.source,
                                   json.loads(args.params) if args.params else None)
            result = {'revision': data['revision'], 'record': data['revisions'][-1]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (Exception, KeyboardInterrupt) as exc:
        print(f'kinesmith: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
