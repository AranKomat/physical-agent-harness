# Native Stop Evidence: Audit And Qualification Requirements

## Concrete Correction

Auditing the older private `physical_ai.harness_radio_driver` found that
`receipt_metadata()` unconditionally reported `stop_acknowledged: true`.
Its `stop()` cleared the action hook and stopped recording, but did not measure
whole-robot settling. Pausing simulator stepping may freeze simulated motion;
it does not demonstrate braking or rest-to-rest physical execution.

The driver now reports false for both paths. Cleanup remains idempotent, disarms
the hook and latches the driver before recording cleanup, including on cleanup
failure. No hold actions were added, and no extra motion was authorized.
This legacy driver is not eligible for strict continued execution until stopping
is qualified. Historical receipts remain unchanged but their stop flags must not
be reused as physical-stop qualification evidence.

The public experiment runner already rejects false stop acknowledgement before
verification, ledger completion or further actions. Its existing negative receipt
test covers this boundary. The recent wrist diagnostics use separate drivers and
are unaffected by this correction; their failed stop receipts remain failures.

## Required Stop Semantics

Before implementing a replacement native stop callback, specify and qualify:

1. A fixed-command quiet interval of at least five complete 30 Hz control
   intervals, not five isolated instantaneous endpoint readings.
2. Complete measurement coverage for base, both arms, torso and grippers.
   Missing callbacks, stale captures, reset epochs or nonfinite values fail closed.
3. Current-source joint measurements and legally estimated base motion, with
   declared measurement-error bounds and interval timing. Integrating raw base
   velocity is not independent verification of that same velocity.
4. Unchanged candidate thresholds: wrist 0.006 rad/s, planar base 0.002 m/s,
   yaw 0.005 rad/s, plus the other existing joint/gripper limits. These are
   qualification targets, not a claim that the present sensors can certify them.
5. Distinguish endpoint location tolerance, interval-average velocity, peak
   velocity, and swept displacement. None automatically proves the others.
6. Keep monitoring during the stop operation, enforce the existing action and
   time budgets, and retain an unresolved-stop fault on failure. Cleanup is
   recorded separately from measured physical stopping.

## Measurement Resolution Check

For two scalar position samples separated by dt, with each position's absolute
error bounded by epsilon, an interval-average velocity upper bound is
`abs(delta_position) / dt + 2 * epsilon / dt`. This is not a peak-velocity bound.

- At 120 Hz and 0.006 rad/s, even zero measured wrist displacement requires
  per-sample error at most 0.000025 rad to support that interval-average limit.
- At 30 Hz and 0.002 m/s, zero measured planar displacement requires per-sample
  position error at most 0.0000333 m (using a norm-bounded vector error).
- Across five 30 Hz intervals the latter allowance becomes 0.0001667 m, but
  net displacement can hide motion out and back. A longer baseline alone does
  not establish stationarity throughout the quiet interval.

The head-depth registration's fit thresholds (fitness >= 0.75 and RMSE <=
0.015 m) are fit-quality filters, not calibrated pose-error bounds. Neither its
small measured stationary drift nor its information matrix can be substituted
for such a bound. Camera-to-base motion also needs the measured joint/FK chain;
camera stillness is not automatically base stillness.

## Next Experiment Decision

Do not repeat the same wrist ramp or silently switch to position-derived stop
authority. The next useful native diagnostic must collect complete joint substep
telemetry and legally derived camera/base motion, including the camera-to-base
kinematic chain, during a separately approved bounded motion/braking protocol.
Keep the candidate stop monitor in shadow mode.

If simulator ground truth is used to quantify estimator error retrospectively,
isolate it in an evaluator-only artifact unavailable to control, and document
that separation. It cannot substitute for legal online stop evidence. Require
an explicit protocol and authorization before any new commanded motion.

Until measurement uncertainty, stopping and external clearance are qualified,
Phases 5-7 remain incomplete. No claim of task progress or GPT benefit follows
from this audit.
