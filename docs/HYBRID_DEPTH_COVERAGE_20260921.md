# Hybrid Retained-View Coverage Diagnostic

## Decision

The retained stationary observation does **not establish full-body clearance**
for a short base translation. Do not admit classical base motion from this
diagnostic. This is a missing-evidence result, not a measured collision, policy
failure, or proof that the proposed move is physically impossible.

No simulator was started, no action was sent, and no model was called. The
diagnostic reused the final settled observation (sequence 5) from
`hybrid-stationary-hold-20260921-r1`. The existing rental was left running as
requested. No learned-policy settings or geometry gates were changed.

## Method And Limitations

- Validate robot-only URDF/config hashes and content-addressed depth files.
- Use `yourdfpy` FK driven by legal 61D proprioception; compare EEF positions
  with legal proprioception. Maximum position discrepancy: `1.154e-6 m`.
- Compose the previously asset-checked camera extrinsics and optical convention
  in the robot base frame. No simulator world/object/robot pose is used.
- Load upstream planning proxies: 79 spheres on 30 links. Their mesh enclosure
  has **not** been qualified. In particular, a list of planning spheres is not
  automatically a conservative full-robot collision model.
- Translate those proxies by 5 cm forward, backward, left or right. Sample
  exposed final surfaces outside the original proxy union using deterministic
  Fibonacci directions, at 128 and 512 samples per sphere. This is not a swept
  volume; excluded original interiors are not marked free.
- Project samples into the three cameras. Require valid positive optical-z
  depth in a 3x3 pixel neighborhood, with the minimum depth exceeding the
  sample's optical z by 2 cm, to report `depth_beyond_sample`.
- Intrinsics come from an **earlier native calibration receipt**, not the exact
  hold boundary. Image dimensions match, but contemporaneous calibration is
  still required. Treat all projection/depth findings as provisional.

Support is a union across cameras, not a surface-area or volume estimate. Neither
a supported point nor a successful numerical FK comparison authorizes motion.
Contact with floor, self-occlusion and proxy overapproximation have not been
disambiguated into collision labels. Optical support does not establish payload
coverage, braking clearance, localization accuracy or changing-scene safety.

## Results

At 512 directions per sphere:

| Hypothetical translation | Exposed samples | Outside all camera views | Depth-beyond support |
| --- | ---: | ---: | ---: |
| Forward 5 cm | 22,974 | 22,353 | 245 |
| Backward 5 cm | 22,134 | 18,284 | 2,862 |
| Left 5 cm | 22,224 | 17,971 | 3,599 |
| Right 5 cm | 22,143 | 17,902 | 3,586 |

The lower 128-direction sampling gave the same qualitative conclusion. This is
sampling sensitivity evidence, not convergence to a certified collision bound.

Even among samples below 40 cm in the base frame, 1,135 of 1,604 forward samples
were outside all views; only 93 had depth-beyond support. Backward and lateral
directions also contained unseen low samples. A clear forward scene image is
therefore not sufficient evidence for this admission gate.

The legal FK estimate places the head camera approximately 1.393 m above the
base origin, pointing forward/down. Both wrist cameras are approximately
0.502 m high and point predominantly down/back in this posture. These geometry
estimates help explain why distant visible scenery does not cover the entire
near-robot travel region.

## Next Gate

1. Capture actual intrinsics alongside native observations and validate the
   calibrated camera/base transform at the same boundary.
2. Establish conservative robot/payload bounds and measured pose uncertainty.
3. Test whether causally accumulated online depth observations cover a proposed
   short path, including low obstacles. Old views require qualified relative
   pose, temporal validity and self-geometry handling; replay success alone is
   not an online clearance qualification.
4. If ordinary-start observations cannot establish clearance, record a rejected
   classical handoff. Do not quietly substitute ground truth, assume unseen
   space is empty, or add uncounted camera/robot motion.
5. Only then run nonzero base movement, measured braking, and A-short/B-short.

This narrows the prerequisite instead of launching another expensive full task
or adding more policy/model architecture. It does not establish that the hybrid
approach will improve task completion.

## Reproducibility

Public numerical helper: `experiments/behavior/depth_coverage.py`. Fourteen
regressions cover visibility classes, invalid depth neighborhoods, occlusion,
margin, transform direction, camera unions, empty input and malformed geometry.
The full suite passes **594 tests**; Ruff passes.

Private run: `hybrid-depth-coverage-20260921-r1/report.json`. Source asset hashes,
source observation hash, all three depth hashes and the diagnostic implementation
hash are recorded there. Robot assets, sensor images and host details remain
private. The report SHA-256 is:

`8674f3023e680e1f89c066d94b6c2e7647b1e2f822f7e56119aa7ac1f7dcdd9a`
