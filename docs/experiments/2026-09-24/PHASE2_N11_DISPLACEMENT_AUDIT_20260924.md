# Phase 2 N11 Displacement Audit

Date: 2026-09-24  
Run: `displacement-sam-20260923-r1`  
Scope: read-only audit of retained native RGB/mask evidence; no model calls,
robot actions, or identity bindings.

## Observed evidence

The retained N11 case contains 13 chronological head-camera frames from a
native contact trace, with one local tracker ID and a nonempty mask in every
frame. The mask centroid moves from approximately `(510.6, 528.2)` pixels in
the first frame to `(481.7, 458.2)` pixels in the last frame. Mask area varies
from 2,976 to 8,685 pixels. This is useful evidence of image-space target
displacement during the trace and is stronger than a static repeated view.

## Why N11 remains insufficient for the Phase 2 gate

The source observations have `camera_pose=null` at all sampled boundaries.
They therefore provide no legal camera-to-background/world transform with
which to distinguish target motion from camera motion. The trace also has no
independent physical identity proof for the tracker ID. A moving mask and a
reused local ID cannot authorize inherited metric geometry or prove that the
same physical object was followed.

Accordingly, this audit supports the descriptive claim **“native image-space
displacement observed”**, but does not close the protocol scenario
“continuous object motion relative to the background.” It also does not close
similar-object crossing, full occlusion, or full-loss reappearance.

## Next required evidence

To promote N11 or a replacement case, retain contemporaneous legal camera pose
and source-bound RGB/depth for the sequence, plus either a background/static
scene reference or an independently qualified motion estimate. Keep the
identity ledger ambiguous until that evidence is available. Do not synthesize
the missing pose from evaluator state or infer it from the mask centroid.

## Provenance

Source directory on the GPU host:

`/workspace/physical-ai-lab/runs/displacement-sam-20260923-r1/`

| Artifact | SHA-256 |
| --- | --- |
| `plan.json` | `135548fd15a9736df5c9e34668bad6f703ba3cdc763d9d65ecb0268416a598a7` |
| `source-assets.json` | `58c938a2099846be9ac35f0dfdad0fc1f080a454532ce59e4cef9bedbebeb3c7` |
| `report.json` | `1aa5f876e21eb68ef388b8360ff66eb72d3fb750fa130229f7f918f60275d173` |
