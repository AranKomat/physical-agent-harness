# R1Pro Native Collision Settings

## Scope And Recovery

After the approved GPU-driver recovery, a zero-commanded-action native inspection
loaded the reserved development instance 301 and read only the robot's collision
configuration. Initialization/reset settling is separate from commanded actions.
No object/global poses were used for control, no policy/planner was invoked, and
no paid calls were made. The rental remains running; it was not stopped or destroyed.

Attempt r1 failed before simulator startup because the private inspection script
imported `pxr` before the simulator initialized its Python modules. Attempt r2
moved that import inside the evaluator context and completed. Both attempts and
logs are preserved locally with empty checksum-based rsync comparisons. The
corrected script passes Ruff. Simulator processes exited and no GPU compute
processes remained after the run.

## Measured Results

- Native BEHAVIOR source: `b1979916ec1549b10a4e65e630bc6504a9af1b00`.
- Exactly 14 declared disabled link pairs, all present as symmetric runtime USD
  filtered-pair relations; no additional explicit pairs were found.
- No wholly disabled links.
- 164 enabled collider prims: 161 `convexHull`, three `boundingSphere`.
- The left and right finger1-to-wrist-camera pairs are explicitly filtered.
  These are the two submillimeter gaps in the earlier authored-convex audit.
- Inspection sim time stayed at 0.3416666844859719 seconds.
- Source and GPU-environment hashes matched before/after inspection.

The native 14-pair list and legacy planner 35-pair list share ten pairs. The four
native-only pairs are left/right arm link2 to torso link4 and left/right finger1
to the corresponding wrist camera. The 25 legacy-only pairs are parent/child
link pairs. Explicit USD filters alone do not establish the simulator's implicit
connected-link collision behavior. Neither list was changed or merged.

Private receipt: `runs/native-robot-collision-settings-20260923-r2/receipt.json`.
SHA-256: `620698ff5393bcee74a8eba70eedb4931638326191c14dd4b3c9b878e3a96dec`.

## Unresolved Offsets And Next Gate

All 164 inspected CollisionAPI prims returned no authored contact/rest-offset
values. This is **not evidence of zero offsets**. The pinned source defines a
1 mm contact offset and zero rest offset, but sets them only on collected
PhysxCollisionAPI instances. This diagnostic did not enumerate that separate API
list or query effective cooked-shape offsets, so the source defaults cannot yet
be reported as measured native values.

Next inspect PhysxCollisionAPI placement/effective offsets and connected-link
semantics, then reconcile the planner collision model explicitly. Cooked-shape
equivalence, wheel geometry, external clearance and swept-path checks remain
unqualified. Native filtering explains why the two small geometric gaps do not
by themselves demonstrate a native collision problem; it does not authorize
removing checks from the planner or opening any motion gate.
