from __future__ import annotations

import pytest

from physical_harness.experiment.actors import Goal
from physical_harness.experiment.existing_bridge import from_existing_driver
from physical_harness.experiment.fixture import FixtureNative
from physical_harness.experiment.native_rpc import decode_observation, encode_observation


def test_existing_legal_driver_adapter_no_codec_guessing():
    native = FixtureNative('ep')
    pixels = native.observe().cameras[0].data
    envelope = dict(schema_version=1, episode_id='ep', observation_id='o1', sim_time=0,
                    rgb_refs={'head': 'native-head'}, depth_refs={'head': 'depth'},
                    proprioception={'joints': [0.0]},
                    camera_intrinsics={'head': {'width': 64, 'height': 48}},
                    camera_frames={'head': 'optical'})
    adapter = from_existing_driver(name='test', episode='ep',
                capture_legal=lambda: envelope, read_rgb=lambda ref: pixels,
                run_skill=native.run_skill, stop=native.stop,
                qualification_id='fixture-only', place=lambda env: ('room', 'wide view'))
    observation = adapter.observe()
    assert observation.id == 'o1' and observation.cameras[0].data == pixels
    assert observation.place_id == 'room'
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
