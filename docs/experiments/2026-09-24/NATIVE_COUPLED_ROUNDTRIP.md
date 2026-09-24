# Native Coupled Out-and-Return Attempt

Follow-up: [bounded evaluator-pose diagnostic](COUPLED_BASE_RATE_DIAGNOSTIC.md)
reproduced the abort and established that the reported rate was not actual
base drift in that later run. The original failure remains retained below.

## Outcome

The first native coupled trial **aborted during outward motion** at the existing
RGB-D base-rate gate. It did not reach the 10 cm endpoint or attempt a return.
Phase 7 remains incomplete. This was explicitly exploratory with unknown
external clearance, not a strict benchmark run.

Private run: `runs/native-coupled-roundtrip-20260924-r1`

- Fresh legal reset capture, bounded torso4 + right-arm7 IK, endpoint checks,
  continuous authored self-separation with tracking allowance and sampled scene
  intrusion checks passed before commands.
- Native actions: **89 completed**, comprising 29 outward-profile actions
  (including 20 initial holds) and all 60 reserved holds.
- Measured right EEF displacement before abort: **3.803 mm**, not 10 cm.
- Outward substep samples: 116; hold substep samples: 240.
- Joint-monitor and hold-monitor errors: none.
- Maximum measured active tracking error: 0.0002582 rad.
- Maximum held-body joint drift: 0.0001266 rad.
- Final raw settled feedback: true. This is not strict stop qualification.
- Paid calls: zero. No automatic retry or threshold relaxation.

## Abort Evidence

At observation sequence 63, RGB-D/FK base estimation reported:

| Measurement | Value | Existing abort bound |
|---|---:|---:|
| Displacement from reference | 0.558 mm | 2 mm |
| Rotation from reference | 0.000286 rad | 0.005 rad |
| Translation rate | **0.029337 m/s** | **0.02 m/s** |
| Rotation rate | 0.018003 rad/s | 0.04 rad/s |

The translation-rate gate triggered. Small accumulated displacement does not
prove the rate was erroneous: actual drift and an estimation transient remain
unresolved. The failure stayed latched. The separate reserved-hold observer
completed its measurements without error and the owner issued no return.

The outer orchestration exited nonzero while waiting for a return-admission
capture that the correctly aborted owner never requested. The native receipt,
not that generic orchestration exception, identifies the motion failure.

## What This Establishes

Unlike the prior fixtures, this run exercised coupled controller writes,
substep readback/telemetry, fresh initial geometry admission, and the reserved
hold path in BEHAVIOR. It does not establish endpoint accuracy, a completed
return, useful manipulation, collision clearance or task success.

The next investigation should use these retained observations to distinguish
base-pose estimation/timing error from actual drift before another motion
attempt. Do not weaken the base-rate threshold merely to obtain completion.

## Evidence And Cleanup

Receipt SHA-256:
`7669ab169693086a06a315df1e161f32b1b398c99a1b438d6cd9c18135defe26`

The native and owner receipts, admission outputs, joint logs and sensor evidence
are retained privately. Worker exit was verified, no experiment worker remained
running, and GPU memory returned to 0 MiB. The rental was not stopped or rebooted.
Work ran at low priority on CPU cores 19-22; no changes were made to the user's
separate workload.

Software verification before the trial: 137 focused private tests passed;
the public suite passed 1,520 tests and Ruff.

## Retained-Data Diagnosis

Two local replays compared the last nine outward base observations using the
same source-bound head depth and legal joint-based camera extrinsics. They
issued no actions or paid calls:

- `runs/coupled-base-rate-replay-20260924-r1`: 50 ICP iterations maximum.
- `runs/coupled-base-rate-replay-20260924-r2`: 200 ICP iterations maximum.

At the failed sequence 63:

| Registration path | Estimated translation rate |
|---|---:|
| First reference, identity initialization | 29.540 mm/s |
| First reference, joint-FK camera-motion initialization | 29.538 mm/s |
| Consecutive frames, identity initialization | 2.804 mm/s |

Increasing the iteration limit produced identical reported values. The
first-reference residual grew from 1.37 mm at sequence 49 to 6.58 mm at sequence
63; the final consecutive-pair residual was 3.30 mm. All satisfied the existing
registration fitness/residual checks, illustrating that those checks alone do
not establish rate-estimation accuracy. The local first-reference rate closely
reproduces, but is not bit-identical to, the native rate.

The replay verified 1/30-second comparison intervals and calibration/evidence
binding. Capture implementation inspection confirms paired renders check
unchanged simulator time, joints, velocity, proprioception and calibration.
These checks do not independently establish rendered sensor synchronization or
base-pose accuracy.

Conclusion: there is substantial reference-dependent estimator disagreement,
not evidence that simply increasing iterations or seeding from FK fixes the
abort. Consecutive registration is not ground truth. No production estimator,
abort threshold or motion admission was changed, and no native retry was made.
Before retrying, validate interval motion against independent evidence or a
known-motion estimator test; do not select the lower rate simply because it
would pass. Phase 7 remains incomplete.

### RGB Feature Cross-Check

`runs/coupled-rgb-motion-replay-20260924-r1` uses reciprocal SIFT matches,
source-frame measured depth and RANSAC PnP, followed by the same legal camera-FK
compensation. This changes the registration measurement, not the sensor or FK
source. The local diagnostic used OpenCV 5.0.0; it was not installed on the GPU
host or added to the runtime.

| RGB/depth PnP path | Translation rate at sequence 63 |
|---|---:|
| Difference of first-reference estimates | 26.920 mm/s |
| Consecutive frames | 21.894 mm/s |

The consecutive pair retained 402/420 inliers, spanning approximately 663 by
711 pixels, with median reprojection residual 0.086 pixels. First-reference
pairs retained 202/256 and 201/257 inliers, with median residuals around 0.24
pixels. Exact synthetic reprojection of those measured 3D feature sets recovered
a known millimetric translation to less than 1e-8 m error. That checks solver
convention and scale only, not sensor accuracy. Some refined inliers exceed the
initial RANSAC residual cutoff; no motion admission uses these fits.

Both feature-based rates exceed the unchanged 20 mm/s abort bound. This
contradicts treating the low consecutive-depth rate as sufficient evidence of
a false abort. Subpixel feature error, shared depth/FK errors and actual base
motion remain possible. The next native diagnostic should record base pose to
an evaluator-only sidecar, unavailable to control, rather than replacing the
estimator with whichever one gives a passing rate. No new native motion was
issued for this cross-check, and it does not complete any phase.
