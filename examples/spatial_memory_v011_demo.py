"""Small fixture showing posed-keyframe memory without building a permanent 3D map."""

import sys
from pathlib import Path

# Allow direct execution from an unpacked overlay; an installed repo does not need this.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from physical_harness.memory.spatial_views import SpatialViewIndex, keyframes_from_legal_envelope
from physical_harness.spatial_scene import SceneAuthority, request_from_spatial_memory


def main():
    envelope = {
        "episode_id": "demo",
        "observation_id": "obs-17",
        "sim_time": 17.0,
        "rgb_refs": {"head": "native/rgb/17", "wrist": "native/rgb/w17"},
        "depth_refs": {"head": "native/depth/17", "wrist": "native/depth/w17"},
        "estimated_pose": {
            "method": "rgbd_odometry",
            "frame": "local_map",
            "camera": "head",
            "transform": [[1,0,0,1.2],[0,1,0,-0.4],[0,0,1,1.1],[0,0,0,1]],
            "evidence_ids": ["obs-16", "obs-17"],
            "confidence": 0.87,
        },
    }
    index = SpatialViewIndex("demo")
    for keyframe in keyframes_from_legal_envelope(
        envelope,
        rgb_asset_ids={"head": "asset:head:17", "wrist": "asset:wrist:17"},
        reason="decision_required",
        entity_ids=("mug_2",),
        place_ids=("kitchen_counter",),
        tags=("pre_grasp",),
    ):
        index.add_keyframe(keyframe)

    request = request_from_spatial_memory(
        index,
        request_id="scene:grasp:mug_2",
        now=18.0,
        operation="build local geometry for collision-aware grasp planning",
        focus_entities=("mug_2",),
        place_ids=("kitchen_counter",),
        minimum_authority=SceneAuthority.COLLISION,
    )
    print(index.snapshot())
    print(request)


if __name__ == "__main__":
    main()
