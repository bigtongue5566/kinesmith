"""Separate native process prevents bpy/Manim state from leaking across scenes."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path


def main():
    context_path = Path(sys.argv[1])
    ctx = json.loads(context_path.read_text(encoding='utf-8'))
    source = Path(ctx['source_path'])
    frames = Path(ctx['frames_path'])
    os.environ['KINESMITH_CONTEXT'] = str(context_path)
    sys.path.insert(0, str(source.parent))
    spec = importlib.util.spec_from_file_location('kinesmith_native_scene', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if ctx['engine'] == 'manim':
        from manim import tempconfig
        with tempconfig({'pixel_width': ctx['width'], 'pixel_height': ctx['height'],
                         'frame_rate': ctx['fps_number'], 'media_dir': str(frames.parent / 'native'),
                         'save_pngs': True, 'format': 'png', 'zero_pad': 6,
                         'write_to_movie': False, 'disable_caching': True,
                         'preview': False, 'verbosity': 'WARNING'}):
            scene = getattr(module, ctx.get('class_name', 'MotionScene'))()
            scene.render()
        images = sorted((frames.parent / 'native').rglob('*.png'))
        if len(images) != ctx['duration_frames']:
            raise ValueError(f"Manim produced {len(images)} frames; expected {ctx['duration_frames']}. "
                             'Native Scene runtime must exactly match timeline duration.')
        for i, path in enumerate(images):
            shutil.copyfile(path, frames / f'{i:06d}.png')
    elif ctx['engine'] == 'blender':
        import bpy
        module.build_scene(ctx)
        scene = bpy.context.scene
        scene.render.resolution_x = ctx['width']
        scene.render.resolution_y = ctx['height']
        scene.render.resolution_percentage = 100
        # Blender uses integer fps/fps_base. This preserves rational rates exactly.
        from fractions import Fraction
        fps = Fraction(ctx['fps'])
        scene.render.fps = fps.numerator
        scene.render.fps_base = fps.denominator
        scene.frame_start = 0
        scene.frame_end = ctx['duration_frames'] - 1
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        bpy.ops.wm.save_as_mainfile(filepath=str(frames.parent / 'editable.blend'))
        for frame in range(ctx['duration_frames']):
            scene.frame_set(frame)
            scene.render.filepath = str(frames / f'{frame:06d}.png')
            bpy.ops.render.render(write_still=True)
    else:
        raise ValueError(ctx['engine'])


if __name__ == '__main__':
    main()
