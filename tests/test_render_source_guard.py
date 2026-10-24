import pytest
from PIL import Image

from kinesmith.render import render_project
from kinesmith.tools import write_json


def test_source_change_during_render_never_publishes_cache(tmp_path, monkeypatch):
    source = tmp_path / 'scene.html'
    source.write_text('original', encoding='utf-8')
    project = {'schema_version': '1.0', 'id': 'race', 'title': 'race', 'revision': 1,
               'width': 32, 'height': 32, 'fps': '24', 'duration_frames': 1,
               'scenes': [{'id': 'one', 'engine': 'canvas', 'source': 'scene.html',
                           'start_frame': 0, 'duration_frames': 1}]}
    write_json(tmp_path / 'project.json', project)

    def concurrent_edit(scene, context, root, frames):
        Image.new('RGBA', (32, 32), 'white').save(frames / '000000.png')
        source.write_text('changed during render', encoding='utf-8')
        return {}

    monkeypatch.setattr('kinesmith.render.render_browser', concurrent_edit)
    with pytest.raises(RuntimeError, match='中途改變'):
        render_project(tmp_path)
    assert not list((tmp_path / '.render-cache').rglob('render.json'))
    assert not (tmp_path / 'renders/v1.webm').exists()
