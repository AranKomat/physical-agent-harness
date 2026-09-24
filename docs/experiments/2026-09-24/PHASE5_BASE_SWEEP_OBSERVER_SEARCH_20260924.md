# Phase 5 Base-Sweep Observer Search

Date: 2026-09-24

## Question

Can one wrist-camera posture, or a simultaneous pair of wrist-camera postures,
observe enough of the robot's newly swept low-body region to justify attempting
a strict short base segment?

This was a CPU-only search with zero robot actions and zero model calls. It used
the checksum-pinned sequence-768 legal posture from the completed staging run,
the retained target-directed heading and the pinned R1Pro URDF, camera mounts and
authored collision meshes.

## Frozen Search

The candidate segment is 5 cm in base coordinates:

```text
[0.0477478, -0.0148375, 0] m
```

Authored convex-hull vertices and face centroids were translated through 25%,
50%, 75% and 100% of that segment. Samples above 40 cm or inside any starting
convex hull were removed, leaving 3,610 newly swept low-body samples.

The search evaluated 128 deterministic Sobol joint configurations per arm and
all 16,384 simultaneous left/right pairs. The first screen was deliberately
optimistic frustum geometry. The second screen applied authored-hull ray
blocking, but excluded the opposite arm from each wrist's ray test. It is thus
an upper bound on robot-unoccluded coverage, not a pessimistic rejection caused
by a particular opposite-arm pose.

## Results

| Screen | Best coverage | Missing |
| --- | ---: | ---: |
| Current three cameras | `0/3,610` | `3,610` |
| Frustum-only best left wrist | `3,610/3,610` | `0` |
| Frustum-only best simultaneous pair | `3,610/3,610` | `0` |
| Optimistic robot-occlusion pair upper bound | `1,468/3,610` | `2,142` |

The frustum-only result initially looked sufficient. Robot self-occlusion removes
that apparent solution: even the best two-wrist upper bound covers only 40.7% of
the sample set. Scene occlusion and fresh depth could only reduce usable support.

## Decision

Do not run the proposed native wrist-observer setup for strict base admission.
It cannot satisfy the current sampled-coverage requirement, even before scene
occlusion, depth validity, endpoint collision, path, stopping and uncertainty
checks. This is a useful Phase 5 negative result and avoids another exploratory
motion trial that could not close the gate.

This finite search does not prove that every possible R1Pro posture is
insufficient, and the surface samples do not enclose the continuous swept volume.
It does show that continuing to tune the same head/two-wrist posture strategy is
low value. Strict Phase 5/6 needs a different authority source, such as qualified
environment geometry, a purpose-built low-body sensor, or a protocol whose
benchmark rules explicitly permit collision queries independent of hidden task
state.

Private receipt:
`runs/base-sweep-observer-search-20260924-r2/receipt.json`, SHA-256
`2efa773ed37ec8597d844eaef696aba51a2801cca5319a7fef0c0faf99d60557`.
