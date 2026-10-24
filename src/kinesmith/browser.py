"""Deterministic browser frames. The HTML remains a normal native engine document."""
from __future__ import annotations

import base64
import asyncio
import json
import os
import mimetypes
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from playwright.async_api import async_playwright

from .project import ROOT


async def asset_route(route, root: Path):
    """Fulfill a virtual origin in-process: no socket, server, proxy or CDN."""
    url = urlparse(route.request.url)
    if url.netloc != 'kinesmith.local':
        await route.abort()
        return
    request_path = unquote(url.path)
    base = ROOT / 'vendor' if request_path.startswith('/vendor/') else root
    relative = request_path.removeprefix('/vendor/') if request_path.startswith('/vendor/') else request_path.lstrip('/')
    target = (base / relative).resolve()
    if not target.is_relative_to(base.resolve()) or not target.is_file():
        await route.fulfill(status=404, body='Missing local asset')
        return
    mime = 'text/javascript' if target.suffix in ('.js', '.mjs') else mimetypes.guess_type(target)[0]
    await route.fulfill(status=200, content_type=mime or 'application/octet-stream', body=target.read_bytes())


def render_browser(scene: dict, context: dict, root: Path, frames: Path) -> dict:
    return asyncio.run(_render_browser(scene, context, root, frames))


async def _render_browser(scene: dict, context: dict, root: Path, frames: Path) -> dict:
    errors = []
    diagnostics = []
    url = 'http://kinesmith.local'
    timeout = float(os.environ.get('KINESMITH_FRAME_TIMEOUT', '30'))
    async with async_playwright() as playwright:
        options = {'headless': True, 'args': ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']}
        if os.environ.get('KINESMITH_CHROMIUM'):
            options['executable_path'] = os.environ['KINESMITH_CHROMIUM']
        browser = await playwright.chromium.launch(**options)
        page = await browser.new_page(viewport={'width': context['width'], 'height': context['height']},
                                device_scale_factor=1)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: errors.append(f'{request.url}: {request.failure}'))
        page.on('response', lambda response: errors.append(f'HTTP {response.status}: {response.url}')
                if response.status >= 400 else None)
        await page.route('**/*', lambda route: asset_route(route, root))
        # Random and sampled clock are controlled; native loops must use frame/fps.
        await page.add_init_script("""(() => {
          let s = %d >>> 0;
          Math.random = () => {s += 0x6D2B79F5; let t=s;
            t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);
            return ((t^t>>>14)>>>0)/4294967296;};
          window.__kinesmithMilliseconds = 0;
          Date.now = () => window.__kinesmithMilliseconds;
          performance.now = () => window.__kinesmithMilliseconds;
        })();""" % context['seed'])
        try:
            await page.goto(url + '/' + quote(scene['source'].replace('\\', '/')), wait_until='load', timeout=60000)
            if errors:
                raise RuntimeError('\n'.join(errors))
            await asyncio.wait_for(page.evaluate('async () => {await window.kinesmithReady; await document.fonts.ready;}'), timeout)
            if not await page.evaluate('typeof window.renderFrame === "function"'):
                raise ValueError(f"{scene['source']} 必須定義 window.renderFrame(frame, ctx)")
            for frame in range(scene['duration_frames']):
                ctx = {**context, 'frame': frame, 'time': frame / context['fps_number'],
                       'globalFrame': scene['start_frame'] + frame}
                try:
                    result = await asyncio.wait_for(page.evaluate('''async ([frame,ctx]) => {
                window.__kinesmithMilliseconds = ctx.time*1000;
                await window.renderFrame(frame,ctx);
                const c=document.querySelector('#stage');
                if (!c || c.width !== ctx.width || c.height !== ctx.height)
                  throw Error('stage canvas dimensions must equal project dimensions');
                return {png:c.toDataURL('image/png').split(',')[1],
                        diagnostics:window.kinesmithDiagnostics || []};
                    }''', [frame, ctx]), timeout)
                except asyncio.TimeoutError as exc:
                    raise RuntimeError(f"{scene['id']} frame {frame} exceeded {timeout}s; check native loops") from exc
                (frames / f'{frame:06d}.png').write_bytes(base64.b64decode(result['png']))
                if result['diagnostics']:
                    diagnostics.append({'frame': frame, 'items': result['diagnostics']})
                if errors:
                    raise RuntimeError('\n'.join(errors))
            version = browser.version
        finally:
            await browser.close()
    (frames.parent / 'diagnostics.json').write_text(json.dumps(diagnostics), encoding='utf-8')
    return {'browser': version, 'diagnostics': diagnostics}
