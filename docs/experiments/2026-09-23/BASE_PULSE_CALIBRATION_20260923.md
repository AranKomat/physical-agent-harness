# Bounded Base Pulse Calibration

## Protocol And Outcome

One separately approved simulator-only attempt: five initial holds, ten forward
commands at 0.005 m/s, fifteen braking holds, maximum 30 actions. Unknown clearance
remained explicitly exploratory. Raw abort/stop thresholds and the native codec
were unchanged. No model calls, automatic retry or return movement.

All 30 actions and 120 physics callbacks completed without callback errors or
latched abort. Initial five raw stopped samples passed. Final raw stopping did
not pass. The pulse produced negligible base displacement, so this trial **does
not qualify moving localization or braking**.

The command schedule was checked against the saved 23-D action vectors: ten
base-x entries equal to `0.005 / 0.75`; all other base entries zero and all
non-base holds unchanged. Stop counting reset at phase boundaries. Evaluator
base poses were isolated from control exactly as in the preceding full-body
hold calibration and consumed only after native execution ended.

## Evaluator Measurements

| Phase | Actions | Forward displacement | Max planar excursion | Max substep planar interval rate |
| --- | ---: | ---: | ---: | ---: |
| Initial hold | 5 | 0.492 micrometres | 1.192 micrometres | 0.128 mm/s |
| Forward pulse | 10 | 2.067 micrometres | 3.632 micrometres | 0.436 mm/s |
| Braking hold | 15 | approximately zero | 1.966 micrometres | 0.229 mm/s |

Nominal commanded travel was 1.667 mm. Actual evaluator forward displacement
was approximately 0.12% of that value and near the simulator's numerical
resolution scale. Treat this as a failed attempt to create a useful motion
contrast, not as evidence of precise micro-motion control.

Recorded raw stopped endpoint counts were 5/5, 10/10 and 5/15 respectively.
These counts do not establish a sustained stop or moving/braking competence.

The legal RGB-D/FK replay processed all 31 captures, with maximum observed
translation error 8.323 micrometres and rotation error 1.206e-5 rad against the
isolated evaluator. Because the robot barely moved, this adds essentially
near-stationary evidence, not the missing moving-estimator qualification.

## Cause Audit And Next Decision

The pinned evaluator calls `policy.forward()` on every control step; the driver
updates the command before each call. Existing codec audit checks the native
input/output scaling. Inspection of the holonomic controller's velocity branch
shows frame rotation and forwarding to the joint controller, not an explicit
low-speed dead zone in that branch.

This does not prove a friction/dead-zone explanation. The run did not record
the applied low-level velocity targets, drive gains or forces. Those are the
next missing diagnostics before attributing the failure or selecting a stronger
pulse. Do not change policy normalization, controller gains or simulator physics
to make this result pass. A stronger commanded pulse requires a new declared
protocol/approval; this authorization is consumed.

Phases 5-7 remain incomplete. No strict motion or task success is claimed.

## Evidence

Private source run: `runs/base-pulse-calibration-20260923-r1`.
Analysis: `runs/base-pulse-analysis-20260923-r1`.
Legal estimator evaluation: `runs/base-pulse-rgbd-evaluation-20260923-r1`.

Receipt SHA-256:
`13b01ef27d13e488a038fd3ca9d030f8cd8a050e5c50352c7777f6c8e60a8203`.
Evaluator JSONL SHA-256:
`73ea7485b92a99a5860fc0607fb143f3800ed291257d0592e9c30ba6567f543f`.
Legal joint JSONL SHA-256:
`6bb09938058f5b45bd80ecd8c8dc0eab48424317df39c4e644b9d08a8d11818f`.

Source snapshots and source/environment checks are retained. Raw data and log
copied locally; complete run checksum comparison found no differences. New
schedule/analysis tests pass and Ruff passes. Full private suite: 1020 passed,
one existing skip. GPU compute list was empty after completion. Rental lifecycle
unchanged.
