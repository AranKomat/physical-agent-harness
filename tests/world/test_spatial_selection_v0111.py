from dataclasses import replace

from physical_harness.world.memory.spatial_views import PosedRGBDKeyframe, SpatialViewIndex
from physical_harness.world.spatial_scene import request_from_spatial_memory


def pose(x=0.0, y=0.0, z=1.0):
    return (
        1.0, 0.0, 0.0, x,
        0.0, 1.0, 0.0, y,
        0.0, 0.0, 1.0, z,
        0.0, 0.0, 0.0, 1.0,
    )


def kf(identifier, t, x, *, entity="cup", place="kitchen"):
    obs = f"obs-{identifier}"
    return PosedRGBDKeyframe(
        keyframe_id=identifier,
        episode_id="ep",
        observation_id=obs,
        sim_time=t,
        camera="head",
        rgb_asset_id=f"rgb-{identifier}",
        depth_ref=f"depth-{identifier}",
        pose_frame="local_map",
        camera_to_frame=pose(x, 0, 1),
        pose_source="rgbd_odometry",
        pose_confidence=0.9,
        pose_evidence_ids=(obs,),
        reason="decision_required",
        entity_ids=(entity,),
        place_ids=(place,),
    )


def test_local_scene_requires_entity_and_place_conjunction():
    index = SpatialViewIndex("ep")
    index.add_keyframe(kf("old-cup", 9, 0.0, entity="cup", place="hall"))
    index.add_keyframe(kf("kitchen-plate", 10, 0.1, entity="plate", place="kitchen"))
    index.add_keyframe(kf("current-cup", 11, 0.2, entity="cup", place="kitchen"))

    request = request_from_spatial_memory(
        index,
        request_id="scene",
        now=12,
        operation="local grasp geometry",
        focus_entities=("cup",),
        place_ids=("kitchen",),
    )
    assert request.source_keyframe_ids == ("current-cup",)


def test_same_camera_same_place_retains_metric_viewpoint_diversity():
    index = SpatialViewIndex("ep")
    index.add_keyframe(kf("a", 1, 0.0))
    index.add_keyframe(kf("b", 2, 0.05))
    index.add_keyframe(kf("c", 3, 0.60))

    selected = index.select_keyframes(
        now=4,
        entity_ids=("cup",),
        place_ids=("kitchen",),
        limit=2,
        require_all_filters=True,
        min_separation_m=0.25,
    )
    assert selected[0].keyframe_id == "c"
    assert {item.keyframe_id for item in selected} == {"a", "c"}


def test_general_history_keeps_or_semantics_by_default():
    index = SpatialViewIndex("ep")
    index.add_keyframe(kf("cup-hall", 1, 0.0, entity="cup", place="hall"))
    index.add_keyframe(kf("plate-kitchen", 2, 0.4, entity="plate", place="kitchen"))
    selected = index.select_keyframes(
        now=3, entity_ids=("cup",), place_ids=("kitchen",), limit=4
    )
    assert {item.keyframe_id for item in selected} == {"cup-hall", "plate-kitchen"}


def test_busy_keyframe_metadata_remains_bounded_but_exceeds_old_limit():
    entities = tuple(f"entity-{index}" for index in range(128))
    view = replace(kf("busy", 1, 0.0), entity_ids=entities)
    index = SpatialViewIndex("ep")
    index.add_keyframe(view)
    assert index.select_keyframes(now=2, entity_ids=("entity-127",)) == (view,)
