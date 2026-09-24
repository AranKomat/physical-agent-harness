import hashlib

import numpy as np
import pytest

from experiments.behavior.contracts import Evidence, Observation, Stamp
from experiments.behavior.sam_transit_target import surface_target


@pytest.fixture
def sample(tmp_path):
    stamp = Stamp(session="sam-target", epoch=0, sequence=704)
    refs = {kind: {"head": Evidence(id=kind, stamp=stamp, observed_at=1.,
                                  source=kind, uri="unused")} for kind in ("rgb", "depth")}
    obs = Observation(stamp=stamp, observed_at=1., proprio=(0.,)*61, **refs)
    frame = dict(obs=obs, depth=np.ones((8, 8)), k=np.eye(3), extrinsic=np.eye(4))
    archive = tmp_path / "masks.npz"
    np.savez(archive, masks=np.ones((1, 8, 8), dtype=bool), ids=np.array([7]),
             labels=np.ones((1, 8, 8), dtype=np.int32))
    result = dict(stamp=stamp.model_dump(), rgb_id="rgb", depth_id="depth", observed_at=1.,
                  published_at=1.1, dequeued_at=1.2, ready_at=1.3, archive_finished_at=1.4,
                  generation=2, ids=[7], artifact=archive.name,
                  sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), motion_authorized=False)
    return frame, result, tmp_path


def consume(sample, **overrides):
    return surface_target(*sample, **(dict(generation=2, tracker_id=7, now=1.5) | overrides))


def test_surface_is_not_identity_or_motion_authority(sample):
    result = consume(sample)
    assert result["surface_median_base_m"] == [3.5, 3.5, 1.]
    assert result["support"] == 64
    assert not result["identity_verified"] and not result["motion_authorized"]


@pytest.mark.parametrize("field,value", [("rgb_id", "other"), ("depth_id", "other"),
    ("generation", 3), ("motion_authorized", True), ("sha256", "wrong"),
    ("artifact", "../masks.npz"), ("ids", [8]), ("ready_at", 9.), ("observed_at", 0.)])
def test_detached_or_invalid_result_rejected(sample, field, value):
    sample[1][field] = value
    with pytest.raises(ValueError):
        consume(sample)


@pytest.mark.parametrize("override", [dict(now=4.), dict(now=1.3), dict(tracker_id=8)])
def test_no_stale_or_missing_id_fallback(sample, override):
    with pytest.raises(ValueError):
        consume(sample, **override)


def test_split_surface_is_not_collapsed_to_background_median(sample):
    frame, result, root = sample
    labels = np.ones((1, 8, 8), dtype=np.int32)
    labels[:, :, 4:] = 2
    path = root / result["artifact"]
    np.savez(path, masks=np.ones_like(labels, dtype=bool), ids=np.array([7]), labels=labels)
    result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="split"):
        consume(sample)


def test_dominant_surface_excludes_small_background_patch(sample):
    frame, result, root = sample
    labels = np.ones((1, 8, 8), dtype=np.int32)
    labels[:, :, -1] = 2
    frame["depth"][:, -1] = 8.
    path = root / result["artifact"]
    np.savez(path, masks=np.ones_like(labels, dtype=bool), ids=np.array([7]), labels=labels)
    result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    target = consume(sample)
    assert target["support"] == 56
    assert target["surface_median_base_m"] == [3., 3.5, 1.]


def test_pinned_selection_rejects_new_episode_and_generation(sample, monkeypatch):
    from experiments.behavior.sam_transit_target import SAMTransitTarget

    frame, result, root = sample
    monkeypatch.setattr("experiments.behavior.sam_transit_target.time.monotonic", lambda: 1.5)
    target = SAMTransitTarget(root, session="sam-target", epoch=0, generation=2, tracker_id=7)
    target(frame, {"sam_target_result": result}, root)
    assert len(target.receipts) == 1
    result["generation"] = 3
    with pytest.raises(ValueError, match="generation"):
        target(frame, {"sam_target_result": result}, root)
    target.session = "another"
    with pytest.raises(ValueError, match="episode"):
        target(frame, {"sam_target_result": result}, root)
