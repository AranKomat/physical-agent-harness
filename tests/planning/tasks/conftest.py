from dataclasses import replace

import pytest

from physical_harness.core.actions import Basis, Gripper, Pose
from physical_harness.integrations.experiment.journal import Journal


def make_basis(n=0, **kwargs):
    return replace(Basis('fixture', f'obs-{n}', f'capture-{n}', float(n), 100.0 + n, 'local', 'origin', f'geometry-{n}', 0, 'fixture-robot', 'calibration', (f'rgb-{n}', f'depth-{n}')), **kwargs)

@pytest.fixture
def basis():
    return make_basis()

@pytest.fixture
def journal(tmp_path):
    j = Journal(tmp_path / 'journal.sqlite', 'fixture', max_microusd=0, max_calls=1)
    yield j
    j.close()

@pytest.fixture
def gripper():
    return Gripper('fixture-hand', '1', 'fixture-assets', ('jaw',), (0.04,), (0.0,), (0.0,), (0.05,), Pose('grasp'), 0.08)
