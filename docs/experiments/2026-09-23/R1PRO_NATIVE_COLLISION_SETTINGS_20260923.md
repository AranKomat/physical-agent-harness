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

## Initial Unresolved Offsets (r2)

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

## Effective Offset Follow-Up (r3/r4)

The installed PhysX tensor articulation view provides read-only getters for
effective contact/rest offsets. The extended diagnostic also reads the robot's
PhysxCollisionAPI instances, collected API lists and joint collision flags.
It never queries shape/world transforms or changes collision properties.

Attempt r3 recorded no PhysxCollisionAPI instances and 44 disabled joint collision
flags, then failed its robot-only scope check before reading offsets. The guard
allowed descendants but not the exact robot root; the native articulation view
uses that root. Attempt r4 explicitly permits the exact root or a descendant,
requires exactly one articulation/path, and preserves unrelated-root rejection.
Eight scope tests pass. Failed r3 remains preserved, not replaced or reported as
a successful offset measurement. The simulator's shutdown returned process code
zero despite the r3 exception; the receipt, not exit status alone, establishes
completion.

Successful r4 measurements:

- Exactly one articulation, rooted at the robot's exact prim path; 164 shapes.
- Effective contact offsets: **1.362500-5.035345 mm**, not uniformly 1 mm.
  139 shapes have the minimum value; 25 have larger offsets.
- All 164 effective rest offsets are zero.
- No PhysxCollisionAPI instances on the robot and no collected link-level APIs.
  The source's conditional 1 mm assignment therefore has no instances to update.
  The underlying derivation of the effective offsets was not measured.
- Self-collision is enabled for the articulation.
- All 44 joint collision flags resolve to false, with no authored override.
  All 25 legacy-only excluded pairs correspond to these connected body pairs;
  independently, all 25 are direct parent/child pairs in the pinned URDF.
- Sim time unchanged during inspection; zero commanded actions and paid calls.
  Source and GPU-environment hashes unchanged; no residual GPU compute process.

Offsets are reported in native shape order. This run does not claim a per-mesh
shape correspondence or validate cooked geometry. Contact offsets are contact
generation settings, not a verified geometric safety margin or physical inflation.
No simulator/planner settings or legacy exclusions were changed.

As a diagnostic only, removing native-explicitly-filtered pairs from the earlier
legacy-filtered authored-convex receipt leaves 11,003 pairs with a minimum gap
of 23.140139 mm. This is a subset calculation at one measured posture, not a new
collision configuration, full native geometry audit, or swept-path certificate.

Both new runs/logs are checksum-backed up locally. Private suite: **901 passed,
one existing skip**; seven focused convex tests and eight new scope tests pass;
Ruff clean. Public production code is unchanged, so the full public suite was not
rerun for this documentation-only follow-up.

Private r4 receipt: `runs/native-robot-collision-settings-20260923-r4/receipt.json`.
SHA-256: `a738034692ab7c75309ad56c7a6ac1bf6da06e80008888a7b2b0241029932ba3`.

Next: reconcile a diagnostic collision configuration with the verified native
explicit/connected-pair rules, assess changed postures and swept paths, and
establish cooked geometry/wheel-shape correspondence. External clearance and
stopping remain separate requirements. Phase 7 execution remains unqualified.
