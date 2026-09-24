# cuRobo Phase 7 Planner Smoke Test

This is a planner-only integration test after the completed SAM staging run. It
does not qualify arm motion, scene clearance, or Phase 7. The target is the
current left-gripper pose reconstructed by cuRobo FK from the final retained
proprioception, so the test does not use an object target or a guessed pose.

## Result

- Planner construction: passed.
- `plan_pose` no-op target: passed.
- Returned trajectory: `1 x 1 x 21 x 11`.
- Planner interpolation step: `0.05 s`.
- Wall time: `34.83 s`.
- Robot actions: `0`.
- Paid calls: `0`.
- Collision world: empty.
- Motion authorization: false.

The result proves that the inspected cuRoboV2 API can be instantiated and can
return a trajectory through the current adapter-shaped call. It is not evidence
that the trajectory is safe or useful.

## Configuration Issue Found

The inherited planner YAML is from an older configuration shape and cannot be
passed directly to the current pinned cuRobo source. The smoke configuration
required these explicit migrations:

- filter obsolete `KinematicsLoaderCfg` and `CSpaceParams` fields;
- use `base_link` from the pinned R1Pro URDF instead of virtual
  `base_footprint_x`;
- use `left_gripper_link`, which exists in the URDF, instead of the absent
  `left_eef_link`;
- remove obsolete virtual-base and inactive right-arm joints from the active
  single-arm cspace;
- provide a default joint position;
- disable collision loading for this smoke test because no qualified collision
  world was installed.

The old YAML and the pinned URDF both have SHA-256 values recorded in the
companion receipt. The processed and planner URDFs currently hash identically.

## Required Before Native Arm Motion

The configuration migration must be made explicit in a reproducible private
planner setup, then rerun with:

1. the full torso-plus-arm joint partition and exact native joint order;
2. qualified R1Pro collision geometry, including the gripper and external
   scene;
3. a current scene-install receipt from legal RGB-D/proprioceptive evidence;
4. a declared free-space endpoint and return path;
5. independent FK, swept-collision, stop, and endpoint verification.

Until those conditions hold, this smoke result must not be used to authorize
the trajectory or to claim Phase 7 completion.
