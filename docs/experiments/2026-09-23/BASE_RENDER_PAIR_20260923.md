# Paired Render Freshness Diagnostic

## Protocol And Integrity

`base-render-pair-20260923-r1` repeats the declared original-physics short pulse:
five preflight holds, five 0.01 m/s commands, fifteen braking holds. After each
normal observation, two render-only updates precede a second legal observation.
The second stream uses distinct observation IDs and is never fed to control,
feedback, stop checks or a policy. Both streams retain actual capture wall times;
no historical timestamp is shifted.

All 25 actions completed, with 26 paired captures. Every pair passed identical
simulation time, joint positions/velocities and proprioception checks. There
were no callback errors. Legal joint telemetry and separately isolated evaluator
body poses are byte-for-byte identical to the unpaired short-pulse run. Extra
renders did not change this run's physical trajectory. Final raw stop still fails.

## Paired Localization Results

Both streams use the same pinned legal head RGB-D/FK estimator and are evaluated
against the same sealed body-pose trace after execution.

| Measurement | Normal observation | After two render-only updates |
| --- | ---: | ---: |
| Maximum observed translation error | 113.72 micrometres | 16.80 micrometres |
| Maximum observed rotation error | 0.00002314 rad | 0.00000591 rad |
| Moving intervals detected above 2 mm/s | 4/5 | 5/5 |
| Braking intervals below 2 mm/s | 14/15 | 15/15 |
| First moving interval estimated speed | 0.273 mm/s | 2.987 mm/s |
| First braking interval estimated speed | 2.977 mm/s | 0.0331 mm/s |
| Maximum interval-speed magnitude discrepancy | 2.977 mm/s | 0.1275 mm/s |

The normal stream reproduces the original unpaired localization errors. Thus
previous additional renders do not alone solve freshness of the next normal
post-action observation. The second capture at the same physical state is the
useful correction in this test.

The retrospective lag comparison for the refreshed stream now favors zero lag:
maximum translation difference 16.80 micrometres at zero versus 106.81 at one
control interval and 212.11 at two. This supports render freshness as the source
of the prior apparent delay, rather than simply fitting a timestamp offset.
It does not identify every internal renderer component or guarantee freshness
for other configurations, sensor streams or moving objects.

## Consequence For The Sequence

Use explicitly refreshed, provenance-bound observations for subsequent classical
localization/stop qualification, with pause-state checks and current wall-time
availability. Do not retimestamp old captures or install an automatic stale
decision bypass. The tested path is available as an opt-in diagnostic; the older
radio driver's shared policy/observer capture remains unchanged to preserve the
frozen policy's recipe. A production integration must keep those boundaries
separate and measure render cost before adoption.

These results are a concrete Phase 5 sensor-timing advance. They do not certify
a pose-error bound from one trace, prove peak velocity between camera frames,
provide missing low-body clearance, or qualify whole-robot stopping. The
2 mm/s comparisons are offline interval-average diagnostics, not replacement
stop acknowledgements. GraspGenX and later manipulation phases were not used.

## Evidence

Native receipt SHA-256:
`925ba36ac0b82dc2ec9b34bb9f3e2cc966d973937bd41d06782079068a4a746f`.
Analysis directories:
`runs/base-render-primary-rgbd-20260923-r1`,
`runs/base-render-refreshed-rgbd-20260923-r1`, and
`runs/base-render-refreshed-lag-20260923-r1`.
The latter binds the refreshed replay with SHA-256
`335826dd00fac513a0aa82b76258e0f13c6847d8ff416c2a78b4ff480ff2e6d4`.

Raw run and log are backed up locally; checksum directory comparison reported
no differences. Native process exited and released GPU allocation. Execution
was low-priority and limited to four cores; no instance lifecycle or unrelated
workload changes. No paid calls. Full private suite: **1059 passed, one existing
skip**; eight new paired-capture tests cover observation isolation, changed
physics, missing pairs and provenance/state mismatches. Focused Ruff passes.
