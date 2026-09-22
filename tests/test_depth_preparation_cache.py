import numpy as np
import pytest

from experiments.behavior import head_depth_shadow as module


@pytest.mark.parametrize('change', ['none', 'depth', 'calibration', 'dtype'])
def test_prepared_cache_requires_exact_inputs(monkeypatch, change):
    prepared, registered = [], []

    def prepare(depth, calibration):
        cloud = object()
        prepared.append(cloud)
        return cloud

    def register(clouds):
        registered.append(clouds)
        return True, np.eye(4), np.eye(6)

    monkeypatch.setattr(module, '_prepare_cloud', prepare)
    monkeypatch.setattr(module, '_register_clouds', register)
    cache = module.CachedPointToPlane()
    k = dict(width=4, height=4, fx=2., fy=2., cx=1., cy=1.)
    a, b, c = (np.full((4, 4), n, dtype=np.float32) for n in (1, 2, 3))
    cache(None, a, None, b, k)
    previous = b.copy()
    b[:] = 99  # Caller mutation must not modify the cache key.
    if change == 'depth':
        previous[0, 0] += 1
    elif change == 'calibration':
        k['fx'] += 1
    elif change == 'dtype':
        previous = previous.astype(np.float64)
    cache(None, previous, None, c, k)
    assert len(prepared) == (3 if change == 'none' else 4)
    assert (registered[1][0] is registered[0][1]) == (change == 'none')
    assert len(registered) == 2
