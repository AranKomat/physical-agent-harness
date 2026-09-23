# Frame-704 Endpoint And Convention Audit

## Result

Phase 9 remains partial. None of the eight retained proposals is admitted to
path planning or motion. Numerical IK success is not grasp success.

The endpoint screen used the frame-bound inputs from [the proposal report](GRASP_VIEW704.md),
161 authored convex shapes, native explicit/connected-joint exclusions, and
61,200 sampled points from the three contemporaneous depth cameras.

| Candidate | Self-collision records | Observed points inside robot | Target points in inner box | Nearest target-to-box distance |
| --- | ---: | ---: | ---: | ---: |
| 0 | 20 | 158 | 0 | 28.85 mm |
| 1 | 0 | 3 | 0 | 39.52 mm |
| 2 | 0 | 403 | 0 | 33.47 mm |
| 3 | 0 | 635 | 0 | 27.82 mm |
| 4 | 0 | 1487 | 0 | 32.97 mm |
| 5 | 0 | 1440 | 0 | 30.07 mm |
| 6 | 0 | 366 | 0 | 30.12 mm |
| 7 | 0 | 3494 | 0 | 40.93 mm |

Intrusion counts are rejection diagnostics, not calibrated contact measurements.
No target-contact exclusion was applied. Sparse points cannot certify free space,
and zero target support does not prove that the full unseen object is absent.

## Convention Check

Inspected pinned GraspGen-X source `b9429097728cb1c430dd78b92edf17ba318aad03`:
`grasp_server.py` centers the input cloud, then adds its center back to output
translations. `gripper_config_wizard.py` applies `base_rotation` to native hand
geometry. This is consistent with our current base-from-camera times proposal
times canonical-from-native chain. It is not an independent physical calibration.

A CPU-only audit checked input hashes, cloud/proposal round trips and a synthetic
canonical box-center point transformed through both direct and native-hand chains.
Maximum cloud reconstruction error was 1.20e-7 m; synthetic chain error was zero.
All eight boxes still had zero retained target support. Nearest points were at
canonical z=0.098-0.109 m, beyond the annotated box's z=0.050-0.070 m interval.
This is not a numerical-tolerance issue. It does not yet distinguish a deficient
hand annotation, learned proposal convention, or poor proposals on this partial cloud.
The synthetic check proves algebraic consistency only, not the learned convention.

## Evidence And Next Decision

Local private artifacts under `internal/physical-ai-lab/runs/`:

- `grasp-endpoints704-20260924-r1/receipt.json`, SHA-256
  `c0990d2723c6c8caf1416654fc9addfa4445a43fbe41f0ff2dc2bbe01647f1a1`.
- `grasp704-convention-20260924-r1/receipt.json`: linked hashes for the cloud,
  hand, generation receipt, proposals and IK receipt; all eight distance checks.

Scripts: `grasp_endpoint_batch.py` and `audit_grasp704_convention.py`.
The convention audit ran locally without GPU, paid calls or robot actions.
No full regression suite was rerun for this report.

Next compare the candidate hand annotation and output convention against the
released reference gripper/inference example, with a visual cloud/hand overlay.
Do not introduce a fitted translation, widen the box to manufacture support,
or spend another proposal batch before this distinction is resolved. Existing
frame-416 invalidated evidence stays invalid. Motion authority remains false.
