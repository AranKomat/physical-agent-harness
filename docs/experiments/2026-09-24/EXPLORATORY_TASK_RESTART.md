# Exploratory Task Restart

Date: 2026-09-24. User approved bounded simulator-only exploratory task trials,
with unknown clearance recorded, unchanged abort limits and no strict phase credit.
No paid calls were made. No strict motion gate was changed.

## Attempts

Private run prefix: `exploratory-task-20260924-`.

| Run | Observed outcome |
| --- | --- |
| r1 | Grounding snapshot directory name rejected before native startup |
| r2 | Grounding worker lacked yourdfpy; no native startup |
| r3 | Initial native RGB-D capture; frozen prompt mismatch rejected before actions |
| r4 | 768 frozen Behavior-Skill acquisition actions, 25 captures; zero classical actions |

r4 failed at transit initialization because the native environment lacked
yourdfpy. Subsequent code review also found a deeper incompatible contract:
`target_grounding` emits detection-only boxes, while `exploratory_transit._target`
requires the legacy segmented identity, derived mask and metric medians.
Installing the missing dependency alone would not repair this path.

The owner now rejects these unsupported transit modes before workers launch.
Do not restore GrabCut or promote boxes to metric masks to make the run pass.
Use fresh source-bound SAM masks and measured depth in a tested integration first.
No fifth rollout was started. All owned workers were reaped.

## Interpretation

This is infrastructure/integration failure, not evidence of staging benefit or
task success. No phase completed. The serial setup failures were avoidable:
future preflight must exercise the complete perception-to-transit contract before
paying for another native acquisition. The action budget was acquisition followed
by the probe, not post-probe policy exposure; earlier commentary misstated that.

Behavior-Skill source/checkpoint and codec remained frozen. Grounding-DINO files
matched the repository-pinned hashes. The unrelated CPU workload was not stopped
or modified. This run used nice 10, but did not enforce CPU affinity.
