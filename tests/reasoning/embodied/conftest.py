import hashlib
import io
from dataclasses import replace

import pytest
from PIL import Image

from physical_harness.core.actions import Basis, Gripper, Pose
from physical_harness.core.discovery import DiscoveryRequest, FrameRef, RegionRef
from physical_harness.integrations.experiment.journal import Journal


def make_basis(seq=0, *, episode='ep', wall=100.0, sim=0.0, domain='fixture', **changes):
    b = Basis(episode, f'obs-{seq}', f'source-{seq}', sim, wall, 'local', 'epoch-0', 'geo-0', 0, 'robot', 'calibration', (f'e-{seq}',), domain)
    return replace(b, **changes)

def make_frame(seq=0, *, basis=None, color=(128, 20, 20), camera='head', available=None):
    b = basis or make_basis(seq, wall=100.0 + seq, sim=float(seq))
    image = Image.new('RGB', (32, 24), color)
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    raw = stream.getvalue()
    f = FrameRef(b, f'image-{camera}-{seq}', hashlib.sha256(raw).hexdigest(), camera, 32, 24, b.captured_wall if available is None else available)
    return (f, raw)

def make_request(identifier='req', seq=0, *, wall=None, task_revision='task-v1', frames=None, **changes):
    if frames is None:
        b = make_basis(seq, wall=100.0 + seq if wall is None else wall, sim=float(seq))
        f, _ = make_frame(seq, basis=b)
        frames = (f,)
    else:
        b = frames[-1].basis
        f = frames[-1]
    r = RegionRef('region-a', f.asset_id, (0.1, 0.1, 0.8, 0.8))
    request = DiscoveryRequest(identifier, 'Find a red radio', task_revision, b, frames, (r,), (), 'empty', max(b.captured_wall, *(x.available_wall for x in frames)), b.captured_wall + 20, ('initial_view',))
    return replace(request, **changes)

def response(request, *, count=1, attention=True):
    values = []
    for n in range(count):
        values.append({'local_id': f'new-{n}', 'frame_id': request.frames[-1].asset_id, 'region_id': 'region-a', 'box': None, 'known_id': None, 'description': 'red rectangular device on a table', 'hypotheses': ['radio', 'speaker'], 'status': 'hypothesis', 'retention': 'retain', 'value': {'task': 3, 'future': 1, 'landmark': 0, 'novelty': 1, 'uncertainty_value': 2, 'redundancy': 0, 'transience': 0}, 'needs_view': True})
    return {'request_id': request.id, 'request_fingerprint': request.fingerprint, 'updates': values, 'attention': [{'local_id': 'new-0', 'reason': 'possible target', 'significance': 'high'}] if attention and count else [], 'scene_summary': 'A room with a table.'}

@pytest.fixture
def journal(tmp_path):
    j = Journal(tmp_path / 'journal.sqlite', 'ep', max_microusd=100000, max_calls=100)
    yield j
    j.close()

@pytest.fixture
def basis():
    return make_basis()

@pytest.fixture
def gripper():
    return Gripper('gripper', 'v1', 'assets', ('finger',), (0.04,), (0.0,), (0.0,), (0.05,), Pose('grasp'), 0.08)
