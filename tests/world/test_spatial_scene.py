import pytest

from physical_harness.world.memory.spatial_views import PosedRGBDKeyframe, SpatialViewIndex
from physical_harness.world.spatial_scene import (
    SceneArtifact,
    SceneAuthority,
    request_from_spatial_memory,
)


def keyframe(identifier="k1"):
    return PosedRGBDKeyframe(
        keyframe_id=identifier,
        episode_id="ep",
        observation_id=f"obs-{identifier}",
        sim_time=5.0,
        camera="head",
        rgb_asset_id="rgb",
        depth_ref="depth",
        pose_frame="local_map",
        camera_to_frame=(1,0,0,0, 0,1,0,0, 0,0,1,1, 0,0,0,1),
        pose_source="rgbd_odometry",
        pose_confidence=0.9,
        pose_evidence_ids=(f"obs-{identifier}",),
        reason="decision_required",
        entity_ids=("cup",),
        place_ids=("kitchen",),
    )


def test_scene_authority_is_monotonic_and_explicit():
    display = SceneArtifact(
        "scene", "ep", ("k1",), ("obs-k1",), "local_map", display_ready=True
    )
    assert display.authority == SceneAuthority.DISPLAY
    display.require(SceneAuthority.DISPLAY)
    with pytest.raises(PermissionError):
        display.require(SceneAuthority.COLLISION)


def test_motion_authority_requires_calibration():
    with pytest.raises(ValueError):
        SceneArtifact(
            "scene", "ep", ("k1",), ("obs-k1",), "local_map",
            observed_geometry_refs=("mesh",),
            display_ready=True, collision_ready=True, motion_ready=True,
        )


def test_scene_authority_rejects_non_boolean_readiness():
    with pytest.raises(ValueError, match="boolean"):
        SceneArtifact(
            "scene", "ep", ("k1",), ("obs-k1",), "local_map", display_ready=1
        )


def test_motion_authority_can_be_established_with_provenance():
    scene = SceneArtifact(
        "scene", "ep", ("k1",), ("obs-k1",), "local_map",
        observed_geometry_refs=("mesh",), calibration_evidence_ids=("calib",),
        display_ready=True, collision_ready=True, motion_ready=True,
    )
    assert scene.authority == SceneAuthority.MOTION
    scene.require(SceneAuthority.MOTION)


def test_request_selects_relevant_sparse_views():
    index = SpatialViewIndex("ep")
    index.add_keyframe(keyframe())
    request = request_from_spatial_memory(
        index,
        request_id="r1",
        now=10,
        operation="plan a grasp",
        focus_entities=("cup",),
        place_ids=("kitchen",),
        minimum_authority=SceneAuthority.COLLISION,
    )
    assert request.source_keyframe_ids == ("k1",)
    assert request.minimum_authority == SceneAuthority.COLLISION
