import json

import pytest

from physical_harness.memory.spatial_views import (
    CoverageObservation,
    PosedRGBDKeyframe,
    SpatialViewIndex,
    keyframes_from_legal_envelope,
)


def pose(x=0.0, y=0.0, z=1.0):
    return (
        1.0, 0.0, 0.0, x,
        0.0, 1.0, 0.0, y,
        0.0, 0.0, 1.0, z,
        0.0, 0.0, 0.0, 1.0,
    )


def kf(identifier, t, *, camera="head", entities=(), places=(), quality=1.0):
    observation = f"obs-{identifier}"
    return PosedRGBDKeyframe(
        keyframe_id=identifier,
        episode_id="ep",
        observation_id=observation,
        sim_time=t,
        camera=camera,
        rgb_asset_id=f"rgb-{identifier}",
        depth_ref=f"depth-{identifier}",
        pose_frame="local_map",
        camera_to_frame=pose(t, 0, 1),
        pose_source="rgbd_odometry",
        pose_confidence=0.9,
        pose_evidence_ids=(observation,),
        reason="object_sighting",
        entity_ids=entities,
        place_ids=places,
        quality=quality,
    )


def test_select_prefers_relevant_diverse_views():
    index = SpatialViewIndex("ep")
    index.add_keyframe(kf("a", 1, camera="head", entities=("cup",), places=("kitchen",)))
    index.add_keyframe(kf("b", 2, camera="wrist", entities=("cup",), places=("kitchen",)))
    index.add_keyframe(kf("c", 9, camera="head", entities=("plate",), places=("kitchen",)))
    index.add_keyframe(kf("d", 10, camera="head", entities=("cup",), places=("hall",), quality=0.7))

    selected = index.select_keyframes(now=12, entity_ids=("cup",), limit=2)
    assert {item.keyframe_id for item in selected} == {"a", "b"} or {item.keyframe_id for item in selected} == {"b", "d"}
    assert all("cup" in item.entity_ids for item in selected)
    assert len({item.camera for item in selected}) == 2


def test_coverage_distinguishes_negative_evidence_from_not_looked():
    index = SpatialViewIndex("ep")
    keyframe = kf("a", 10, entities=("cup",), places=("table",))
    index.add_keyframe(keyframe)
    weak = CoverageObservation(
        "weak", "ep", 11, "table", 0.4, 0.1, ("ev1",), ("a",), "cup", False
    )
    strong = CoverageObservation(
        "strong", "ep", 12, "table", 0.95, 0.05, ("ev2",), ("a",), "cup", False
    )
    index.add_coverage(weak)
    index.add_coverage(strong)
    assert not weak.supports_negative_evidence()
    assert strong.supports_negative_evidence()
    assert index.negative_evidence(target_entity_id="cup", region_id="table", now=20).coverage_id == "strong"
    assert index.negative_evidence(target_entity_id="cup", region_id="table", now=200, max_age_s=20) is None


def test_coverage_rejects_non_boolean_sighting_result():
    with pytest.raises(ValueError, match="bool"):
        CoverageObservation(
            "bad", "ep", 1, "table", 0.9, 0.1, ("ev",), target_entity_id="cup",
            target_seen="not_seen",
        )


def test_snapshot_roundtrip_is_deterministic():
    index = SpatialViewIndex("ep")
    index.add_keyframe(kf("a", 1, entities=("cup",)))
    snap = json.loads(json.dumps(index.snapshot()))
    restored = SpatialViewIndex.from_snapshot(snap)
    assert restored.snapshot() == index.snapshot()


def test_projection_uses_only_pose_camera():
    envelope = {
        "episode_id": "ep",
        "observation_id": "obs-1",
        "sim_time": 3.0,
        "rgb_refs": {"head": "rgb-head", "wrist": "rgb-wrist"},
        "depth_refs": {"head": "depth-head", "wrist": "depth-wrist"},
        "estimated_pose": {
            "method": "rgbd_odometry",
            "frame": "local_map",
            "camera": "head",
            "transform": [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 1],
                [0, 0, 0, 1],
            ],
            "evidence_ids": ["obs-1"],
            "confidence": 0.8,
        },
    }
    result = keyframes_from_legal_envelope(
        envelope,
        rgb_asset_ids={"head": "asset-head", "wrist": "asset-wrist"},
        reason="initial",
    )
    assert len(result) == 1
    assert result[0].camera == "head"
    assert result[0].depth_ref == "depth-head"


def test_projection_refuses_unposed_observation():
    with pytest.raises(ValueError):
        keyframes_from_legal_envelope(
            {"episode_id": "ep", "observation_id": "o", "sim_time": 0, "rgb_refs": {}, "depth_refs": {}},
            rgb_asset_ids={},
            reason="initial",
        )


def test_keyframe_rejects_reflected_pose():
    reflected = list(pose())
    reflected[0] = -1
    with pytest.raises(ValueError, match="proper"):
        PosedRGBDKeyframe(
            keyframe_id="reflected",
            episode_id="ep",
            observation_id="obs-reflected",
            sim_time=1,
            camera="head",
            rgb_asset_id="rgb",
            depth_ref="depth",
            pose_frame="local_map",
            camera_to_frame=tuple(reflected),
            pose_source="rgbd_odometry",
            pose_confidence=0.9,
            pose_evidence_ids=("obs-reflected",),
            reason="initial",
        )
