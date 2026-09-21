import math
from dataclasses import replace

import pytest

from physical_harness.hybrid_v0.classical import BasePose
from physical_harness.hybrid_v0.contracts import Snapshot
from physical_harness.hybrid_v0.staging import (
    StagingConfig,
    resolve_staging_pose,
    target_from_depth_pixel,
)


def snapshot(obs="o1", captured=100.0, joint=0.0):
    env = {
        "schema_version": 1,
        "episode_id": "ep",
        "observation_id": obs,
        "sim_time": 4.0,
        "rgb_refs": {"head": "rgb-" + obs},
        "depth_refs": {"head": "depth-" + obs},
        "proprioception": {"joint_positions": [joint]},
        "camera_intrinsics": {"head": {
            "width": 101, "height": 101, "fx": 100.0, "fy": 100.0,
            "cx": 50.0, "cy": 50.0, "depth_scale_m": 0.001,
        }},
        "camera_frames": {"head": "head_optical"},
        "estimated_pose": {
            "method": "rgbd_odometry",
            "frame": "local_map",
            "camera": "head",
            "transform": [[1, 0, 0, 1], [0, 1, 0, 2], [0, 0, 1, .5], [0, 0, 0, 1]],
            "evidence_ids": [obs],
            "confidence": .9,
        },
    }
    return Snapshot.from_envelope(env, captured_wall=captured, frame_epoch="f", geometry_revision="g")


def test_depth_pixel_projects_through_legal_pose_camera():
    s = snapshot()
    target = target_from_depth_pixel(
        s, entity_id="radio", camera="head", pixel_uv=(50.0, 50.0),
        depth_value=2000.0, evidence_ids=("depth-evidence",), confidence=.8,
    )
    assert target.xyz_local == pytest.approx((1.0, 2.0, 2.5))
    assert target.snapshot_fingerprint == s.fingerprint
    assert s.observation_id in target.evidence_ids
    assert s.envelope()["depth_refs"]["head"] in target.evidence_ids


def test_projection_refuses_non_pose_camera():
    s = snapshot()
    with pytest.raises(ValueError, match="posed camera"):
        target_from_depth_pixel(
            s, entity_id="radio", camera="wrist", pixel_uv=(50.0, 50.0),
            depth_value=2.0, depth_is_meters=True, evidence_ids=("e",), confidence=.8,
        )


def test_staging_requires_all_three_geometric_signals():
    s = snapshot()
    target = target_from_depth_pixel(
        s, entity_id="radio", camera="head", pixel_uv=(50.0, 50.0),
        depth_value=2.0, depth_is_meters=True, evidence_ids=("e",), confidence=.8,
    )
    cfg = StagingConfig(radii_m=(.6,), angle_offsets_rad=(0.0, .2), preferred_radius_m=.6)
    with pytest.raises(ValueError, match="No staging candidate"):
        resolve_staging_pose(
            s, target, BasePose(0, 2, 0), config=cfg,
            clearance=lambda *a: True,
            reachable=lambda *a: None,
            visible=lambda *a: 1.0,
        )


def test_staging_ranking_is_deterministic_and_faces_target():
    s = snapshot()
    target = target_from_depth_pixel(
        s, entity_id="radio", camera="head", pixel_uv=(50.0, 50.0),
        depth_value=2.0, depth_is_meters=True, evidence_ids=("e",), confidence=.8,
    )
    cfg = StagingConfig(radii_m=(.5, .7), angle_offsets_rad=(0.0, .3), preferred_radius_m=.7)
    plan = resolve_staging_pose(
        s, target, BasePose(0, 2, 0), config=cfg,
        clearance=lambda *a: True,
        reachable=lambda pose, *a: 1.0 if math.hypot(pose.x-1, pose.y-2) >= .65 else .7,
        visible=lambda pose, *a: 1.0,
    )
    assert plan.selected.target_distance_m == pytest.approx(.7)
    tx, ty, _ = target.xyz_local
    expected = math.atan2(ty-plan.selected.pose.y, tx-plan.selected.pose.x)
    assert plan.selected.pose.yaw == pytest.approx(expected)
    with pytest.raises(ValueError, match="different snapshots"):
        replace(plan, snapshot_fingerprint="foreign")


def test_staging_search_work_is_bounded_not_only_returned_results():
    with pytest.raises(ValueError, match="4096"):
        StagingConfig(radii_m=(.6,) * 65, angle_offsets_rad=(0.,) * 65)


@pytest.mark.parametrize("signal", ["clearance", "reachable", "visible"])
def test_any_unknown_geometry_signal_rejects_candidate(signal):
    s = snapshot()
    target = target_from_depth_pixel(s, entity_id="radio", camera="head", pixel_uv=(50., 50.),
                                     depth_value=2., depth_is_meters=True,
                                     evidence_ids=("detector",), confidence=.8)
    checks = dict.fromkeys(("clearance", "reachable", "visible"), lambda *a: True)
    checks[signal] = lambda *a: None
    with pytest.raises(ValueError, match="No staging candidate"):
        resolve_staging_pose(s, target, BasePose(0, 0, 0), **checks)
