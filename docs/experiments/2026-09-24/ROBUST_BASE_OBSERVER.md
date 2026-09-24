# Robust Base Observer Development Trial

## Hypothesis And Fixed Change

The evaluator-only diagnostic established that the previous rate spike was not
actual base drift. A fixed 5 mm Tukey loss was tested to reduce the influence
of large point-to-plane residuals. This does not establish which pixels caused
the error, or prove that all outliers represent the moving robot.

The opt-in private estimator retains the same cloud preparation, 5 cm matching
radius, 50-iteration maximum and fitness/RMSE checks. It additionally requires
at least half the matched residuals to fall inside the robust kernel's support.
That support check is not a confidence bound. Base displacement, rotation,
instantaneous-rate, freshness and joint-motion thresholds are unchanged.

Default registration remains unchanged. No evaluator poses enter estimation or
control; they are used only in retrospective analysis.

## Retained Evidence

Comparison: `runs/robust-base-registration-comparison-20260924-r1`.

| Trace | Actual max speed | Baseline max estimate | Robust max estimate |
|---|---:|---:|---:|
| Coupled arm/torso, nearly stationary base | 0.057 mm/s | 29.540 mm/s | 1.031 mm/s |
| Forward base pulse | 3.264 mm/s | 3.248 mm/s | 3.216 mm/s |
| Reverse base pulse | 2.739 mm/s | 2.766 mm/s | 2.780 mm/s |

The coupled trace's maximum interval translation error fell from 0.984 mm to
0.0344 mm. Maximum reference translation error fell from 0.558 mm to 0.0569 mm.
The reverse trace's reference error increased slightly, from 0.0066 mm to
0.0127 mm; this is not a claim of uniform improvement.

All three traces also recovered separately injected positive and negative
2 mm rigid translations on each axis to within 0.05 mm. This checks that the
robust fit still responds to motion; it does not reproduce sensor, occlusion
or changing-view errors. The retained real base pulses are small and do not
establish general localization or strict stopping qualification.

## Predeclared Native Attempt

Run: `native-coupled-robust-roundtrip-20260924-r1`.

One fresh simulator-only coupled torso/right-arm attempt with the existing
10 cm base-forward EEF endpoint, return to measured initial active joints,
0.25 rad joint-departure limit, 600-action total cap and 60 reserved holds.
Fresh geometry and state admission are required for both legs. Existing
endpoint and settling checks remain mandatory. Evaluator base poses are
written to a separate sidecar, unavailable to control.

External clearance remains unknown and the run remains exploratory. Even a
completed return would not by itself establish strict collision qualification
or semantic task success. No paid calls or concurrent motion owner.

## Native Outcome

The attempt failed closed at outward action 49 (20 initial holds plus 29 moving
actions), with 40.585 mm measured EEF displacement. It then completed all 60
reserved holds: 109 native actions in total. Joint and hold monitors reported
no error. The 10 cm endpoint and return were not reached; Phase 7 is incomplete.

The original rate spike did not recur. Maximum estimated base rate before
rejection was 3.671 mm/s; evaluator-only maximum was 0.05661 mm/s. Instead,
registration at sequence 103 failed its fit/support checks. Retrospective
inspection found:

| Same rejected capture | Identity seed | Legal joint-FK camera-motion seed |
|---|---:|---:|
| RMSE | 18.814 mm | 7.612 mm |
| Robust support | 49.38% | 98.45% |
| Estimated base displacement | 8.248 mm | 0.0186 mm |

This supports an initialization problem as camera self-motion grows. The
correction now prepared locally initializes the robust fit with measured
source/current camera FK. It does not force the fit to that pose or assume
stationary base as an observation. Regression checks retain detection of real
base displacement despite camera self-motion. This seeded variant has not yet
completed a native trial and must not be conflated with this failed attempt.

The legal-only seeded-observer replay subsequently accepted all 50 recorded
outward capture boundaries, including the rejected frame, with maximum estimated
displacement 0.165 mm and rate 3.718 mm/s. It reads no evaluator sidecar and uses
a declared fixture wall clock, so it does not validate live latency or extend
evidence beyond the recorded 4.06 cm EEF excursion. The output is
`runs/coupled-seeded-observer-replay-20260924-r1`. Fifty-five focused observer,
execution and orchestration tests pass; the next evidence needed remains a
native endpoint-and-return attempt.

The owner again reported missing return capture after the aborted native worker
exited; that wrapper exception is secondary to the retained registration loss.
GPU memory returned to 0 MiB. Local backup verification covered 113 captures
and 669 unique RGB/depth artifacts with zero hash mismatches.

Native receipt SHA-256:
`789687cc6c74730f3b20e1ad171fc9bf45b4a30b37408a715a0eb09373936307`.

Analysis outputs: `runs/coupled-robust-evaluator-analysis-20260924-r1` and
`runs/coupled-robust-gate-analysis-20260924-r2`. The first gate-analysis invocation
ran before its required depth artifact finished downloading and produced no
result; its directory remains retained. No native retry followed that local
file-availability failure.

## Seeded Native Follow-Up

Predeclared run: `native-coupled-seeded-roundtrip-20260924-r1`, with the same
10 cm out-and-return intent, fresh geometry admissions, joint limits and total
action budget. No automatic repeat is authorized by a failure.

Preflight found that the endpoint requires 87.022 mm camera translation and
5.639 degrees camera rotation from torso motion alone. The old first-reference
camera limits (50 mm / 5 degrees) would reject that legal self-motion even with
a correct registration. In the opt-in seeded observer, raw-camera bounds now
include the measured camera-FK change plus the unchanged permitted base motion.
For `C = inv(E0) B E1`, the added camera translation allowance is 2 mm plus
`2 * norm(E1.translation) * sin(0.005 / 2)` for base rotation about the camera
lever arm. The rotation allowance adds 0.005 rad to measured camera self-rotation.
The original raw-camera limits remain lower bounds on that envelope.

After registration, the same 2 mm / 0.005 rad base-displacement guards and
20 mm/s / 0.04 rad/s base-rate guards still apply. This corrects a frame mismatch;
it does not authorize additional base drift. Fifty-eight focused tests pass,
including large camera self-motion, retained real base-drift rejection and
rotation lever-arm coverage. Evaluator poses remain out of the controller.

The native run completed 348 actions: 144 outward, 144 return and 60 reserved
holds. The 10 cm outward endpoint and return endpoint both passed independent
native EEF/FK and settling checks. The final post-hold endpoint remained within
tolerance, but the raw-velocity stop predicate failed. Consequently the original
run remains `complete=false`; it is not a full Phase 7 pass.

Outward and return position errors were approximately 0.00068 mm and 0.00078 mm
in the simulator's reported EEF frame. These are numerical consistency results,
not calibrated real-world precision claims. The final position error was
0.00062 mm. The final right-wrist raw speed was 0.01056 rad/s and torso-joint-2
raw speed was 0.010007 rad/s, against the predeclared 0.01 rad/s limit.

All reserved holds completed and no joint-monitor or base-observer failure was
reported. The final 24 physics intervals instead show maximum right-wrist
position-derived speed of 0.0000418 rad/s; maximum across all angular joints was
0.001034 rad/s. Raw velocity and integrated position evidence disagree. This
does not authorize raising the velocity limit or rewriting the trial outcome.

An opt-in `--position-stop` candidate is now prepared locally. It requires 25
consecutive, source-bound native joint samples spanning 24 physics intervals,
checks all 22 joints, includes float32 quantization allowance, and retains the
same 0.01 rad/s angular and 0.01 m/s finger interval-speed limits. It preserves
raw readings and rejects missing, nonfinite, stale-endpoint or intermediate-motion
evidence. These are bounds on sampled interval averages, not instantaneous
continuous motion or a physical stop certificate. The existing base-stop checks
and raw abort gates remain unchanged; the old single-observation stop path
remains the default. No evaluator truth is used by this candidate.

Retrospective comparison accepts the recorded final window under that candidate,
but explicitly leaves the original run failed. It has not yet passed a new
native trial. Eighty-seven focused tests pass. Failed endpoint-verification
receipts will now be retained before rejection, fixing a diagnostic omission
that had hidden the final check's individual fields.

Receipt SHA-256:
`6968b6b22fac5a1116d91506f69db7f78350979fc13e28a1eb6be955c0bb27b5`.

Local backup: 354 captures, 2,108 unique RGB/depth artifacts, zero hash mismatches.
GPU memory returned to 0 MiB; the rental and unrelated CPU workload were not
stopped or modified. Analysis: `runs/coupled-final-stop-analysis-20260924-r1`
(original predicate) and `runs/coupled-final-stop-analysis-20260924-r2`
(explicit counterfactual candidate comparison). Public verification: 1,520
tests, Ruff, repository ownership and local-link checks passed.

## Position-Interval Native Validation

Predeclared run: `native-coupled-position-stop-20260924-r1`. It retains the
same 10 cm outward endpoint, return, fresh admissions, 348-action profile
including reserved holds, and seeded robust base observer. The only intended
measurement-protocol change is explicit opt-in to the 24-substep joint-position
stop check. Raw velocity readings and their stop verdict remain in each
verification receipt. Rejected endpoint receipts are retained before failure.

This is a new attempt, not reclassification of the preceding trial. No paid
calls, no relaxation of joint interval-speed or base-motion bounds, no use of
evaluator poses by control, and no strict external-clearance claim.

The run completed successfully under its declared protocol:

- 348/348 native actions: 144 outward, 144 return and 60 reserved holds;
- fresh outward and return geometry admission passed;
- outward endpoint, return endpoint and final post-hold endpoint all reached;
- all three source-bound base-settling checks passed;
- all three 24-interval joint-position settling checks passed;
- no joint monitor, base observer, hold monitor or owner error;
- no paid calls and no second actuator owner.

At the outward, return and final checks, maximum position-derived angular rates
were 0.000865, 0.000944 and 0.001034 rad/s. The corresponding maximum raw
readings were 0.01988, 0.02321 and 0.02378 in mixed joint units. The final raw
single-sample predicate remained false, as expected from the preceding run;
that disagreement is retained in the successful receipt rather than hidden.
All position-derived rates remained below the unchanged 0.01 limits.

Endpoint position errors were 0.000684 mm outward, 0.000776 mm on return and
0.000619 mm after the final holds. These are simulator consistency measurements,
not calibrated physical-robot precision. The position-stop sensitivity replay
also rejected all 94 retained 200 ms windows with more than 5 mm native EEF
movement; no clearly moving window was accepted as settled.

This passes the native arm/torso endpoint-return mechanics and the explicitly
qualified simulator position-window stop protocol for this motion class. It does
**not** complete strict Phase 7: the execution remained labeled exploratory
because external swept-volume visibility is incomplete, native cooked-shape
equivalence remains unqualified and wheel coverage is absent. Evaluator poses
were retrospective only and `motion_qualified=false` remains appropriate.

Native receipt SHA-256:
`b7f2d910cd73708031ff30e3b26e9977ece86cec02ab6765637581d2109159b6`.

Evaluator sidecar SHA-256:
`c168c41a5645d1e6f6eb9047381d0781ea8d06129c99f1c76d0d718e38b0556e`.

Retrospective evaluator comparison reports maximum actual base rate
0.0569 mm/s and maximum legal observer estimate 3.902 mm/s; no base-observer
loss occurred. Private focused verification: 87 tests passed. GPU cleanup was
verified at 0 MiB. Full local evidence verification is recorded separately
after the resumable copy completes.

## Strict Clearance Follow-Up

The subsequent [strict clearance candidate search](STRICT_CLEARANCE_SEARCH_20260924.md)
tested eight alternative 10 cm right-EEF translations from the same fresh legal
reset capture. Two failed continuous self-separation; the six scene-screened
candidates left 97.1% to 100.0% of endpoint exposed moving-geometry vertices
outside all retained camera views. No observed scene-point intrusion was found,
but unknown volume was not reclassified as free.

No candidate authorizes another strict native run. This reinforces the existing
Phase 7 boundary: endpoint/return mechanics and the simulator position-window
stop protocol passed, while current external swept-volume observation did not.
