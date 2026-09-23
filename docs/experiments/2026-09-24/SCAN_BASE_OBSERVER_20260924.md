# Scan Base Observer

## Purpose

Connect the existing legal head RGB-D odometry and robot FK to a bounded,
latched base-drift observer for the approved exploratory sensing scan. This is
not a new localization algorithm and does not certify stopping.

Private implementations: `scripts/scan_base_observer.py` and
`scripts/replay_scan_base_observer.py`. The observer accepts paired-render
RGB/depth/proprioception and calibration only. It never opens evaluator poses,
scene object state, segmentation or task truth. It checks content hashes,
stamp/time/modality binding and calibration association before estimating.

The established first-reference RGB-D estimator supplies camera motion. Robot
FK removes camera movement relative to the base using
`E_initial * T_camera_initial_current * inverse(E_current)`.
Consecutive estimates must be one 30-Hz control interval apart; camera
registration failures, stale images, missing intervals and expired completion
latch failure instead of falling back to zero motion. The first observation is
an origin, not a zero-speed measurement.

## Declared Diagnostic Bounds

- Capture-to-result age: at most five wall seconds.
- Estimated displacement from the scan origin: at most 2 mm.
- Estimated full rotation from origin: at most 0.005 rad.
- Consecutive control-boundary translation rate: at most 0.02 m/s.
- Consecutive full rotation rate: at most 0.04 rad/s.

These are exploratory abort thresholds, not calibrated error bars or changes
to strict stop gates. The observer cannot dispatch actions. Missing evidence
does not authorize motion, and `stop_qualified` remains false.

## Retained Experiment

Input: `base-render-pair-20260923-r1/receipt.json` and its legal head images.
Robot URDF/config hashes remain pinned to the earlier FK experiment.
Output: `scan-base-observer-20260924-r1/receipt.json`.

All 26 paired-render captures were processed. Maximum estimated base
displacement was 0.524032 mm and maximum consecutive translation rate was
0.00324756 m/s. These are observer outputs on the retained deliberate pulse,
not independent accuracy measurements. No evaluator truth was opened.

The replay deliberately uses source capture time plus 0.1 seconds as its clock;
this exercises chronological data flow but **does not measure live latency**.
There were zero new robot actions and zero model calls.

Twelve focused tests cover valid observations, stale/future time, missing control
intervals, repeated simulator time, foreign episode binding, corrupt evidence,
detached calibration, unverified renders, failed registration, excessive drift
and slow completion. The private full suite passes 1,185 tests with one existing
skip; Ruff passes for the new observer, runner and tests.

## Remaining Work

Bind this observer and the tightened joint monitor into the one native scan
runner, with fresh-episode geometric admission and reserved braking holds.
Measure native estimation latency and observed motion response before treating
this as a usable runtime monitor. Inter-frame estimates cannot rule out motion
between control boundaries; calibration uncertainty, external clearance and
strict stopping remain unresolved. No scan or task-level phase is completed by
this retained replay.
