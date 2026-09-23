import numpy as np
import pytest

from experiments.behavior import head_depth_shadow
from experiments.behavior.contracts import Observation, Stamp
from experiments.behavior.observations import EvidenceStore
from physical_harness.perception.localization import LocalizationLost


def capture(store, sequence, at):
    stamp = Stamp(session="shadow", epoch=0, sequence=sequence)
    rgb = store.put(np.zeros((6, 8, 3), dtype=np.uint8), "rgb", stamp, at)
    depth = store.put(np.ones((6, 8), dtype=np.float32), "depth", stamp, at)
    observation = Observation(stamp=stamp, observed_at=at, rgb={"head": rgb},
                              depth={"head": depth}, proprio=(0.,) * 61)
    calibration = {"head": {"stamp": stamp.model_dump(), "observed_at": at,
        "rgb_evidence_id": rgb.id, "depth_evidence_id": depth.id,
        "image_shape": [6, 8], "intrinsic_matrix": [[10, 0, 4], [0, 10, 3], [0, 0, 1]]}}
    return observation, calibration


def tracker(tmp_path, monkeypatch):
    delta = np.eye(4)
    delta[0, 3] = .01
    monkeypatch.setattr(head_depth_shadow, "point_to_plane", lambda *_: (True, delta, np.eye(6)*20))
    store = EvidenceStore(tmp_path)
    return store, head_depth_shadow.HeadDepthShadow(store)


def test_shadow_keeps_initial_reference_without_accumulation(tmp_path, monkeypatch):
    store, shadow = tracker(tmp_path, monkeypatch)
    shadow.update(*capture(store, 0, 0))
    for seq in (1, 2, 3):
        result = shadow.update(*capture(store, seq, seq*.5))
        assert result["evidence_ids"] == ["frame-0", f"frame-{seq}"]
        assert result["transform"][0][3] == pytest.approx(-.01)
        assert result["scope"] == "shadow_camera_motion_not_base_or_clearance_authority"


def test_wall_gap_latches_shadow_loss_even_with_small_sim_gap(tmp_path, monkeypatch):
    store, shadow = tracker(tmp_path, monkeypatch)
    shadow.update(*capture(store, 0, 0))
    with pytest.raises(LocalizationLost, match="wall-time gap"):
        shadow.update(*capture(store, 1, 3))
    with pytest.raises(LocalizationLost, match="new episode"):
        shadow.update(*capture(store, 2, 3.5))


def test_wrong_boundary_is_not_a_pose_estimate(tmp_path, monkeypatch):
    store, shadow = tracker(tmp_path, monkeypatch)
    observation, calibration = capture(store, 0, 0)
    calibration["head"]["depth_evidence_id"] = "other-frame"
    with pytest.raises(ValueError, match="boundary mismatch"):
        shadow.update(observation, calibration)
