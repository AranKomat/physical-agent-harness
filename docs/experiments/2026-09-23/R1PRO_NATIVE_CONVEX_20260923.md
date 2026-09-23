# R1Pro Native Convex Representation Comparison

## Scope

Follow-up to measured native offsets and collision filtering. The installed
PhysX cooking interface exposes `request_convex_collision_representation`;
its bundled `ConvexMeshDataDemo` documents synchronous requests. A zero-action
native diagnostic queries only the robot's convex-hull collider paths. It does
not query environment/object geometry, use global object poses, change robot
state, release cooking caches, or modify collision properties.

The response is the API's physics collision representation, not independently
verified access to each already-active solver shape. That distinction remains
explicit. The three wheel `boundingSphere` colliders are not replaced with hulls.

## Procedure

1. Load reserved development instance 301 with the no-action evaluator.
2. Read the same robot filters, joint flags and effective offsets as r4.
3. Request each of the 161 convex-hull representations synchronously; retain
   callback status, vertices, indices and polygons. Record authored mesh points
   and mesh-to-own-link transforms without reading world/object poses.
4. On the Mac, match all 164 collider paths and approximation types to the pinned
   authored asset. Require identical point inventory and mesh-to-link coordinates
   within 1 micrometer; leave three wheel spheres explicitly skipped.
5. Independently build convex hulls from both point sets and test containment in
   both directions using normalized hull-plane violations. The predeclared
   tolerance is **10 micrometers**. This metric is not Euclidean Hausdorff distance.

Asset SHA-256: `6029617cdd3aefce981428058a1c82cffe6af20ae61dc5be1da7334342c3bc52`.
URDF SHA-256: `b0d76760cbedfbcbe1ddc280380dd5f497bbca380313bc096d7239a2c50dae61`.

## Results

- Native r5 completed: 161 valid representation callbacks, each one convex hull;
  three wheel spheres skipped. All paths/types and authored mesh coordinates
  matched the pinned asset.
- **Exact bidirectional correspondence failed:** only 2/161 pass the fixed
  hull-plane tolerance. Maximum authored-outside-returned plane violation is
  **7.467535 mm**, at the head-camera (`zed_link`) collider.
- **Conservative containment passed:** every returned hull lies inside its
  corresponding authored hull to numerical precision. Maximum outward plane
  violation is approximately `1.11e-16` meters.
- Returned hull vertex counts range from 8 to 51, commonly 34. Minimum
  returned/authored volume ratio is approximately 0.945724. This is consistent
  with simplification, not a coordinate mismatch or an outward expansion.
- No threshold was changed to turn the equivalence failure into a pass.
- No commanded actions or paid calls. Sim time and source/GPU environment
  fingerprints remained unchanged during inspection. Native output/log were
  checksum-backed up locally; no residual GPU compute process remained.

Private evidence:

- `runs/native-robot-collision-settings-20260923-r5/receipt.json`, SHA-256
  `bd4d502b877d21cca256aa40ced6c561d555d43740387467491041d7724ada48`.
- `runs/native-convex-comparison-20260923-r1/receipt.json`, SHA-256
  `c1e99d6b4d3bbf05999ce9fac6c4b01c37683bdac5bafc53f56cc6b1518edae3`.

Six focused comparison tests cover differing vertex inventories, shrinkage,
expansion, a known translation, small roundoff and invalid points. Full private
suite: **907 passed, one existing skip**. Ruff passes. Public production code
was unchanged; the full public suite was not rerun for this report.

## Decision And Next Experiment

Do not shrink the authored geometry to match the returned hulls. The existing
authored hulls conservatively contain these representations and are suitable
for the next **offline diagnostic** using explicitly reviewed native filtering.
This is stronger evidence for their conservatism, not full collision or motion
qualification. The earlier sphere/chain failures are not evidence that the
authored convex model itself must be replaced.

Next: evaluate changed postures and bounded swept paths with the conservative
hulls and the measured active/held joint partition. Preserve the legacy planner
configuration while constructing any diagnostic candidate. Separately resolve
wheel shapes and active-shape correspondence. External sensor-derived clearance,
braking, control timebase and endpoint/return execution remain required for
Phase 7; this result does not authorize motion.
