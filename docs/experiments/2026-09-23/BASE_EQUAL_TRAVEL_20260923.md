# Equal-Travel Command-Size Diagnostic

## Protocol

`base-drive-shortpulse-20260923-r1` returns to original physics (no solver
variant) and compares five commands at 0.01 m/s against the previous ten at
0.005 m/s. Both command integrals are 1.6667 mm at 30 Hz. Five preflight holds
and fifteen braking holds remain unchanged; the new total is 25 actions.
Same fixture and seed, no altered gains, limits, mass, friction or abort gates.
Unknown clearance remains exploratory. No policy/model calls or automatic retry.

The operator authorized bounded simulator diagnostics without repeated approval
requests. This explicit profile is not a new navigation default. The runner
rejects combining the command-size profile with the solver variant.

## Measured Results

Initial proprioception and all five preflight observations exactly match the
original-physics `base-drive-pulse-20260923-r2` baseline. All 25 actions completed
without callback errors or an abort. Source/environment hashes remained stable.

| Measurement | Original 0.005 m/s x 10 | New 0.01 m/s x 5 |
| --- | ---: | ---: |
| Nominal travel | 1.6667 mm | 1.6667 mm |
| Evaluator-only forward displacement in pulse | 0.002067 mm | 0.532365 mm |
| Virtual-joint planar net displacement | 0.002262 mm | 0.532508 mm |
| Pulse substep intervals above 2 mm/s (position-derived) | 0/40 | 20/20 |
| Maximum pulse body interval speed | 0.436 mm/s | 3.495 mm/s |
| Maximum body planar excursion during braking | 0.001966 mm | 0.000983 mm |
| Controller output vs PhysX target difference | 0 | 0 |

No sampled frame reported sleeping. Braking has zero position-derived intervals
above 2 mm/s. Eleven of fifteen braking endpoints meet the existing raw stopped
test, but **final stop acknowledgement remains false**. The quiet interval
requirement is not waived. World poses remain retrospective-only and never
authorize control.

The observed response depends strongly on command amplitude/duration despite an
equal nominal travel integral. This supports amplitude sensitivity, not a proved
friction mechanism or guaranteed tracking gain. Actual travel is about 32% of
nominal. Do not convert this into an inverse-gain controller or escalate commands
automatically. One same-start comparison is not general motor qualification.

This supplies a useful moving/braking contrast for Phase 5 localization and
stop-estimator evaluation. It does not complete strict clearance, stopping,
navigation or arm-return gates. No benchmark success is claimed.

## Legal Localization Replay

The fixed-reference head RGB-D estimator with measured-joint FK processed all
26 captures. It consumed only legal pixels, calibration and proprioception;
sealed evaluator poses were compared afterward. At pulse end, estimated forward
position relative to the first capture was 0.41990 mm versus measured 0.53286 mm.
After braking, it was 0.52394 mm versus 0.53353 mm. Maximum observed translation
error was **0.11372 mm**, rotation error **0.00002314 rad**. The larger in-motion
error and later convergence must not be hidden by reporting only the final error.

This establishes detectable movement on this trace, not a calibrated global
error bound, dynamic-scene robustness or a replacement runtime stop authority.
Private replay: `runs/base-drive-shortpulse-rgbd-20260923-r1/receipt.json`;
robot asset and input evidence hashes are retained there. No extra native actions
or paid calls were used for this local replay.

### Timing Follow-Up: Suspected One-Control Image Lag

The first moving control interval has legal estimated planar speed 0.273 mm/s
versus evaluator-derived 2.973 mm/s. The first braking interval has estimated
2.977 mm/s while evaluator displacement is approximately zero. Thus a naive
2 mm/s threshold on uncorrected RGB-D interval speed would miss initial movement
and report movement after braking. Do not promote it to stop authority.

A retrospective lag diagnostic compares the same 22 interior captures for all
offsets. Positive offset pairs estimate k with evaluator state k-offset:

| Offset in 30 Hz controls | Mean translation difference | Maximum |
| --- | ---: | ---: |
| -1 (future truth, evaluator-only negative control) | 58.49 micrometres | 221.65 micrometres |
| 0 | 34.33 micrometres | 113.72 micrometres |
| +1 | 11.29 micrometres | 18.58 micrometres |
| +2 | 32.72 micrometres | 107.06 micrometres |

At the pinned BEHAVIOR source, `eval/evaluator.py:249` requests
`n_render_iterations=1`. `envs/env_base.py:642` only adds renders when more are
requested. `simulator.py:1396` explicitly notes delayed rendering propagation.
`sensors/vision_sensor.py:308` reads annotator data. These observations support a
render-lag hypothesis but do not prove which component causes the alignment.
The corrected error is not a new accuracy claim: selecting an offset after
looking at evaluator truth is diagnostic, not online calibration.

Next compare normal post-action observation with render-only recaptures at
unchanged sim time and measured joint state, retaining both streams. Do not
rewrite historical timestamps, shift data into control, alter frozen-policy
inputs, or assume a universal one-frame correction from this single trace.

Private diagnostic: `runs/base-drive-shortpulse-lag-20260923-r1/receipt.json`.
Source replay SHA-256:
`8bfd0b5d51ab33b4e034de26d1be6170c51f8d1e510bbb46337ddfb656aef75e`.
Three focused tests verify synthetic delay alignment, a common comparison range,
and rejection of missing/out-of-order timing. Focused Ruff passes. No native
actions or paid calls were used for this timing analysis.

## Evidence

Private analysis: `runs/base-drive-shortpulse-analysis-20260923-r1/receipt.json`.
Receipt SHA-256:
`3d2ef87ee9f6f2040ee0caed7707e9a43307872e6a3320887c409a9406db6c93`.
Evaluator pose SHA-256:
`b3777c17340cfd362a29fc42474b1fcb5f73373e5d601d7c4b731c23517107aa`.
Drive telemetry SHA-256:
`271da5cc40a355b0a452b4ad749e1a34111e6ba860eaaf0fd7b584aa60a29baa`.

The run/log are copied locally and a checksum directory comparison reports no
differences. Our low-priority four-core process exited and GPU allocation cleared;
the shared instance and unrelated workload were not changed. Full private suite:
**1048 passed, one existing skip**. New tests enforce equal nominal travel,
the reduced action cap, unchanged fifteen braking holds, exact declared profile
analysis and rejection of combined diagnostic interventions.
