from __future__ import annotations

import pytest

from physical_harness.integrations.experiment.actors import Goal
from physical_harness.integrations.experiment.existing_bridge import from_existing_driver
from physical_harness.integrations.experiment.fixture import FixtureNative
from physical_harness.integrations.experiment.native import NativeBindings
from physical_harness.integrations.experiment.native_rpc import (
    decode_observation,
    encode_observation,
)


def test_existing_legal_driver_adapter_no_codec_guessing():
    native = FixtureNative('ep')
    pixels = native.observe().cameras[0].data
    envelope = dict(schema_version=1, episode_id='ep', observation_id='o1', sim_time=0,
                    rgb_refs={'head': 'native-head'}, depth_refs={'head': 'depth'},
                    proprioception={'joint_positions': [0.0]},
                    camera_intrinsics={'head': {'width': 64, 'height': 48, 'fx': 50,
                                                'fy': 50, 'cx': 32, 'cy': 24,
                                                'depth_scale_m': .001}},
                    camera_frames={'head': 'head_optical'},
                    estimated_pose={'method': 'rgbd_odometry', 'frame': 'local_map',
                                    'camera': 'head', 'confidence': .9,
                                    'evidence_ids': ['o1'],
                                    'transform': [[1, 0, 0, 0], [0, 1, 0, 0],
                                                  [0, 0, 1, 1], [0, 0, 0, 1]]})
    adapter = from_existing_driver(name='test', episode='ep',
                capture_legal=lambda: envelope, read_rgb=lambda ref: pixels,
                run_skill=native.run_skill, stop=native.stop,
                qualification_id='fixture-only', place=lambda env: ('room', 'wide view'))
    observation = adapter.observe()
    assert observation.id == 'o1' and observation.cameras[0].data == pixels
    assert observation.place_id == 'room'
    assert observation.legal_envelope['depth_refs']['head'] == 'depth'
    assert observation.legal_envelope['estimated_pose']['camera'] == 'head'
    assert decode_observation(encode_observation(observation)) == observation
    envelope['camera_intrinsics']['head']['width'] = 99
    with pytest.raises(ValueError, match='dimensions'):
        adapter.observe()


def test_goal_requires_subject_and_container_identity_checks():
    with pytest.raises(ValueError, match='subject'):
        Goal('g', 'IN(ball,basket)', ('ball', 'IN', 'basket'), 'inside', ('basket',))
    with pytest.raises(ValueError, match='endpoint'):
        Goal('g', 'IN(ball,basket)', ('ball', 'IN', 'basket'), 'inside', ('ball',))
    assert Goal('g', 'IN(ball,basket)', ('ball', 'IN', 'basket'), 'inside', ('ball', 'basket'))


def test_native_motion_qualification_is_fail_closed():
    def callback(*args):
        return True

    with pytest.raises(ValueError, match='disagree'):
        NativeBindings('bad', callback, callback, callback,
                       motion_qualified=True, clearance_status='unknown')
    native = NativeBindings('exploratory', callback, callback, callback)
    assert native.motion_qualified is False
    assert native.clearance_status == 'unknown'
