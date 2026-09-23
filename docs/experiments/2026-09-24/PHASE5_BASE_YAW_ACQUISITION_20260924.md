# Phase 5 Base-Yaw And Target-Acquisition Diagnostic

Date: 2026-09-24  
Run: `native-yaw-hardcase-20260924-r2`  
Scope: simulator-only exploratory diagnostic; no learned policy, paid calls, benchmark scoring, or motion authority.

## Result

The run used the pinned BEHAVIOR source and radio public instance 301. It sent
one positive yaw pulse (`0.05 rad/s` command for 15 native actions) followed by
the existing measured hold/braking path. It retained 26 legal RGB-D captures,
25 executed actions, camera calibration, and quarantined evaluator-only robot
and camera poses.

The controller mapping is live: the R1Pro base remains a three-channel
velocity controller with `[vx, vy, wz]` ordering and no robot-level action
normalization. The measured proprioceptive yaw velocity during the pulse was
`0.09405 rad/s` on average over the final five samples, versus the requested
`0.05 rad/s`; the diagnostic therefore rejected command tracking. The stop
path did acknowledge five consecutive settled samples in `0.1667 s`.

The camera pose changed by approximately `0.0109 rad` (`0.626 degrees`) over
the pulse. The initial and final head views showed the living-room wall,
fireplace, and television, but no radio. The trace therefore did not create a
target-bearing hard case and cannot advance Phase 2 identity/loss or qualify
Phase 5 localization/transit.

## Interpretation

This result rules out the earlier hypothesis that the sensing runner was
writing yaw into the wrong action index. It instead exposes two separate
issues that must not be conflated:

1. The public radio instance does not place the target in the initial head
   view, so a generic short pulse is not a valid discovery experiment.
2. The observed velocity response is not within the existing qualification
   tolerance, even though the stop acknowledgement succeeded. No gain,
   threshold, or motor-path change is authorized by this diagnostic.

The unknown-clearance exploratory label remains in force. This is not evidence
of collision-free transit, stopping qualification, or benchmark progress.

## Next action

Do not rerun SAM on this trace and do not repeat the same yaw pulse. The next
native run should first establish a target-bearing acquisition view using an
explicit, bounded online scan protocol, while retaining legal source-bound
RGB-D, camera pose, and publication provenance at each selected boundary. If
the simulator cannot produce such a view without relying on evaluator-only
object state or an unqualified motion command, record that as an external
qualification blocker instead of promoting the trace.

## Provenance

Remote artifact directory:

`/workspace/physical-agent-harness/runs/native-yaw-hardcase-20260924-r2/`

| Artifact | SHA-256 |
| --- | --- |
| `audit.json` | `4eb9811b47b9f7de98e0b7e2997b2e2fe1e5dd3f3212f01e0591ecd7cf26f5a0` |
| `diagnostic_truth.jsonl` | `b4e8ae0a337329efe5e4d4ea3797c0d1e5041b66c05e24c711bc1b1ac06dcb9d` |

The run directory is 118 MiB and remains on the remote experiment checkout.
