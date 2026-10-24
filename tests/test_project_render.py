import copy
import json
from fractions import Fraction

import pytest
from PIL import Image

from kinesmith.project import load_project, revise_project
from kinesmith.render import apply_transition, render_project
from kinesmith.tools import frame_seconds, write_json


def project_at(tmp_path):
    Image.new('RGBA', (64, 36), '#ed6658').save(tmp_path / 'red.png')
    Image.new('RGBA', (64, 36), '#3a66aa').save(tmp_path / 'blue.png')
    project = {'schema_version': '1.0', 'id': 'test', 'title': '測試', 'revision': 1,
               'width': 64, 'height': 36, 'fps': '24000/1001', 'duration_frames': 12,
               'scenes': [{'id': 'a', 'engine': 'image', 'source': 'red.png',
                           'start_frame': 0, 'duration_frames': 8},
                          {'id': 'b', 'engine': 'image', 'source': 'blue.png', 'layer': 1,
                           'start_frame': 4, 'duration_frames': 8,
                           'transition_in': {'type': 'fade', 'duration_frames': 4}}]}
    path = write_json(tmp_path / 'project.json', project)
    return path, project


def test_invalid_timeline_and_asset_containment(tmp_path):
    path, p = project_at(tmp_path)
    load_project(path)
    p['scenes'][0]['duration_frames'] = 13
    write_json(path, p)
    with pytest.raises(ValueError, match='超過'):
        load_project(path)
    p['scenes'][0]['duration_frames'] = 8
    p['scenes'][0]['source'] = '../outside.png'
    write_json(path, p)
    with pytest.raises(ValueError, match='位於'):
        load_project(path)


def test_composite_rational_and_local_revision_cache(tmp_path):
    path, p = project_at(tmp_path)
    one = render_project(path)
    assert one['measured']['frame_count'] == 12
    assert one['duration_seconds'] == float(Fraction(12 * 1001, 24000))
    assert not any(s['cache_hit'] for s in one['scenes'])
    two = render_project(path, output=tmp_path / 'two.webm')
    assert all(s['cache_hit'] for s in two['scenes'])
    before = copy.deepcopy(p['scenes'][1])
    revise_project(path, 'a', '調整主場景參數', params={'accent': 'green'})
    after, _ = load_project(path)
    assert after['scenes'][1] == before
    assert list((tmp_path / 'history').glob('*.png'))
    three = render_project(path)
    assert not three['scenes'][0]['cache_hit']
    assert three['scenes'][1]['cache_hit']
    assert three['scenes'][1]['frame_hashes'] == one['scenes'][1]['frame_hashes']
    # Inspect the actual blended image rather than mirroring the blending formula.
    from kinesmith.render import compose_frames
    images = list(compose_frames(after, three['scenes']))
    assert images[4].getpixel((32, 18))[:3] == (237, 102, 88)
    assert images[7].getpixel((32, 18))[:3] == (58, 102, 170)


def test_wipes_and_fades_have_defined_endpoints():
    scene = {'duration_frames': 10, 'transition_in': {'type': 'wipe-left', 'duration_frames': 4}}
    assert apply_transition(Image.new('RGBA', (8, 4), 'white'), scene, 0).getchannel('A').getextrema() == (0, 0)
    assert apply_transition(Image.new('RGBA', (8, 4), 'white'), scene, 3).getchannel('A').getextrema() == (255, 255)
    assert frame_seconds(24000, '24000/1001') == 1001


def test_revision_replacement_preserves_editable_history(tmp_path):
    path, p = project_at(tmp_path)
    old = (tmp_path / 'red.png').read_bytes()
    replace = tmp_path / 'green.png'
    Image.new('RGBA', (64, 36), 'green').save(replace)
    revise_project(path, 'a', '改綠色', source=str(replace))
    assert next((tmp_path / 'history').glob('a-*.png')).read_bytes() == old
    revised = json.loads(path.read_text(encoding='utf-8'))
    assert (tmp_path / 'red.png').read_bytes() == old
    assert (tmp_path / revised['scenes'][0]['source']).read_bytes() == replace.read_bytes()
    assert revised['revision'] == 2
