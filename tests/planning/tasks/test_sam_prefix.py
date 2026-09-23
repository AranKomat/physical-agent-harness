from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from physical_harness.integrations.sam import PrefixFrame, load_predictor, run_prefix, sha_file
from physical_harness.perception.visual import VisualAsset, VisualRole
from tests.planning.tasks.conftest import make_basis


def prefix(tmp_path, count=3):
    frames = []
    for n in range(count):
        path = tmp_path / f'{n}.jpg'
        Image.new('RGB', (8, 8), (n, n, n)).save(path)
        a = VisualAsset(f'image-{n}', 'fixture', VisualRole.OBSERVATION, 'head', n, n, sha_file(path), (f'rgb-{n}',))
        frames.append(PrefixFrame(make_basis(n), a, path))
    return tuple(frames)

class Predictor:

    def __init__(self, mutation=None, frame_count=3):
        self.calls = []
        self.closed = False
        self.mutation = mutation
        self.frame_count = frame_count

    def handle_request(self, r):
        self.calls.append(r)
        if r['type'] == 'start_session':
            assert len(list(Path(r['resource_path']).glob('*.jpg'))) == self.frame_count
            return {'session_id': 'sam-test-session'}
        if r['type'] == 'close_session':
            self.closed = True
        return {'frame_index': 0, 'outputs': {}}

    def handle_stream_request(self, r):
        self.calls.append(r)
        assert r['propagation_direction'] == 'forward'
        assert r['force_tracker_propagation'] is True
        assert r['max_frame_num_to_track'] == self.frame_count
        for i in range(self.frame_count):
            index = i
            masks = np.ones((1, 8, 8), dtype=bool)
            ids = np.array([1], dtype=int)
            if self.mutation == 'missing' and i == 2:
                continue
            if self.mutation == 'future' and i == 2:
                index = 3
            if self.mutation == 'float_mask' and i == 2:
                masks = masks.astype(float)
            if self.mutation == 'duplicate_ids' and i == 2:
                masks = np.ones((2, 8, 8), dtype=bool)
                ids = np.array([1, 1])
            yield {'frame_index': index, 'outputs': {'out_obj_ids': ids, 'out_binary_masks': masks}}
            if self.mutation == 'duplicate_tail' and i == 2:
                yield {'frame_index': index, 'outputs': {'out_obj_ids': ids, 'out_binary_masks': masks}}

def test_actual_sam_request_contract_publishes_tail_only(tmp_path):
    frames = prefix(tmp_path)
    p = Predictor()
    r = run_prefix(p, frames=frames, cutoff=frames[-1].basis, seed_point=(0.5, 0.5), seed_evidence_id='rgb-0', deadline=200, clock=lambda: 100)
    assert p.closed and r['causal_publication'] == 'tail_only'
    assert r['basis']['observation_id'] == 'obs-2'
    assert r['objects'][0]['local_id'] == 1
    assert not r['persistent_entity_ids']
    assert sum((c['type'] == 'add_prompt' for c in p.calls)) == 1


def test_single_frame_prefix_never_uses_zero_propagation_bound(tmp_path):
    frames = prefix(tmp_path, count=1)
    p = Predictor(frame_count=1)
    result = run_prefix(
        p, frames=frames, cutoff=frames[0].basis, seed_point=(0.5, 0.5),
        seed_evidence_id='rgb-0', deadline=200, clock=lambda: 100,
    )
    assert p.closed
    assert result['basis']['observation_id'] == 'obs-0'
    assert result['source_assets'] == ['image-0']
    assert result['causal_publication'] == 'tail_only'

@pytest.mark.parametrize('mutation', ['missing', 'future', 'float_mask', 'duplicate_ids', 'duplicate_tail'])
def test_bad_sam_outputs_fail_and_close_session(tmp_path, mutation):
    frames = prefix(tmp_path)
    p = Predictor(mutation)
    with pytest.raises(ValueError):
        run_prefix(p, frames=frames, cutoff=frames[-1].basis, seed_point=(0.5, 0.5), seed_evidence_id='rgb-0', deadline=200, clock=lambda: 100)
    assert p.closed

@pytest.mark.parametrize('mutation', ['hash', 'future_available', 'foreign_camera', 'png', 'cutoff', 'hypothetical', 'reverse', 'seed'])
def test_causal_prefix_validation_before_model_calls(tmp_path, mutation):
    frames = list(prefix(tmp_path))
    cutoff = frames[-1].basis
    seed = 'rgb-0'
    if mutation == 'hash':
        frames[0] = replace(frames[0], image=replace(frames[0].image, sha256='b' * 64))
    elif mutation == 'future_available':
        frames[1] = replace(frames[1], image=replace(frames[1].image, available_at=99))
    elif mutation == 'foreign_camera':
        frames[1] = replace(frames[1], image=replace(frames[1].image, camera='wrist'))
    elif mutation == 'png':
        frames[0] = replace(frames[0], path=tmp_path / 'not-a-jpeg.png')
    elif mutation == 'cutoff':
        cutoff = frames[1].basis
    elif mutation == 'hypothetical':
        frames[0] = replace(frames[0], image=replace(frames[0].image, role=VisualRole.HYPOTHETICAL_OUTCOME))
    elif mutation == 'reverse':
        frames.reverse()
    else:
        seed = 'later-seed'
    p = Predictor()
    with pytest.raises((ValueError, PermissionError)):
        run_prefix(p, frames=tuple(frames), cutoff=cutoff, seed_point=(0.5, 0.5), seed_evidence_id=seed, deadline=200, clock=lambda: 100)
    assert not p.calls

def test_loader_never_imports_or_downloads_without_optins():
    import sys
    assert 'sam3' not in sys.modules
    for allow, license in [(False, False), (True, False), (False, True)]:
        with pytest.raises(PermissionError):
            load_predictor({}, allow_inference=allow, licenses_accepted=license)
    assert 'sam3' not in sys.modules

def test_unreviewed_config_rejected_without_model_load():
    with pytest.raises(ValueError):
        load_predictor({'version': 'sam3.1', 'auto_download': True}, allow_inference=True, licenses_accepted=True)

@pytest.mark.parametrize('mode', ['wrong_shape', 'no_objects', 'negative_id'])
def test_mask_geometry_and_empty_output(tmp_path, mode):
    frames = prefix(tmp_path)

    class Changed(Predictor):

        def handle_stream_request(self, req):
            for row in super().handle_stream_request(req):
                if row['frame_index'] == 2:
                    if mode == 'wrong_shape':
                        row['outputs']['out_binary_masks'] = np.ones((1, 7, 8), dtype=bool)
                    elif mode == 'no_objects':
                        row['outputs'] = {'out_obj_ids': [], 'out_binary_masks': []}
                    else:
                        row['outputs']['out_obj_ids'] = np.array([-1])
                yield row
    p = Changed()
    kwargs = dict(frames=frames, cutoff=frames[-1].basis, seed_point=(0.5, 0.5), seed_evidence_id='rgb-0', deadline=200, clock=lambda: 100)
    if mode == 'no_objects':
        assert run_prefix(p, **kwargs)['objects'] == []
    else:
        with pytest.raises(ValueError):
            run_prefix(p, **kwargs)
    assert p.closed
