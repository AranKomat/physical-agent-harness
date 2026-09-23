# Observed Target Closure Support

## Result And Correction

The prior scene rejection screen sampled depth at pixel stride four. The closure
audit uses every retained target-cloud point (2,925), exposing open-finger
overlap missed by that stride. Candidate 1 is therefore removed from the
surviving set. A full-robot endpoint repeat with dense target points also rejects
candidate 3 at its endpoint, independently of its earlier path rejection.

The endpoint screen now appends the complete retained target cloud transformed
into the same base frame. It records the added point count and possible duplicate
scene/target samples; counts are not unique surface-area or severity measures.
This prevents throwing away available target evidence during coarse scene sampling.

Only candidates 0 and 2 remain without observed endpoint intrusions. Their
earlier 17-posture path checks used coarse scene points and are not silently
upgraded to dense-target path validation. Clearance/stopping blockers remain.

## Closure Diagnostic

At each fixed candidate pose, both finger joints are sampled from 0.05 to 0 m
in 2 mm steps. Pinned exported native hand meshes and canonical rotation are
used to count retained static target points inside each convex finger shape.
No robot is commanded; points do not move or deform in this diagnostic.

| Candidate | Open finger overlap | First overlap finger 1 / finger 2 joint position |
| --- | ---: | --- |
| 0 | 0 | 0.034 / 0.028 m |
| 1 | 2 points | 0.024 / 0.050 m; rejected at open state |
| 2 | 0 | 0.028 / 0.034 m |

Candidates 0 and 2 both encounter observed target points during closure. This
does not prove simultaneous stable contacts, opposing normals, frictional force
closure, or successful lift. Unseen surfaces and physical response remain open.
Do not equate the counterfactual static penetration sweep with contact dynamics.

## Evidence

Local private runs:

- `grasp704-closure-support-20260924-r1`: 26 closure samples for candidates 0/1/2,
  per-link counts, source/cloud/config/exported-geometry hashes.
- `grasp704-obb-dense-target-20260924-r1`: all eight full-robot endpoint checks
  using 61,200 coarse scene points plus all 2,925 retained target points.

Scripts: `grasp704_closure_support.py`, `grasp_endpoint_batch.py`.
The pinned proposal archive and hand annotation are unchanged. No inferred
grasp translation, box expansion or allowed-contact exclusion was introduced.
Zero robot actions, new model inference or paid calls. Phase 9 remains partial.

## Dense-Target Path Follow-Up

`grasp704-obb-dense-paths-20260924-r1` applies the corrected dense-target input
to the same 17-fraction joint interpolation. Candidate 0 has no sampled hits.
Candidate 2 is rejected at fraction 0.9375 with nine observed point intrusions
outside the ambiguous start body. Its clean endpoint does not rescue that path.
All other candidates remain endpoint-rejected and receive no path screening.

Candidate 0 is now the sole retained offline survivor. Freeze the proposal set:
no further proposal batches or sampling refinements before addressing the
staging/coverage/stop prerequisites. A 17-posture no-hit result is still not
continuous clearance, an executable trajectory, or successful manipulation.
The complete receipt is backed up locally under the private lab runs directory.
