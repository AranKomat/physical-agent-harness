# Hybrid Experiment Sequence

Updated 2026-09-21 after Hybrid V0.1 integration. This sequence supersedes doing
more GPT-supervised full-radio trials before the motor handoff is interpretable.
It does not authorize new spend, training, license acceptance or weakening gates.

## Current Position

The [native hold-codec and stationary-settling diagnostics](HYBRID_NATIVE_QUALIFICATION_20260921.md)
passed. Hold commands match the pinned native convention; a five-tick stationary
diagnostic achieved five measured settled captures. No nonzero commanded base
move, moving-base braking test or classical-to-policy handoff has been qualified.
The V0.1 resolver and telemetry are offline-tested utilities, not implementations
of the missing perception/collision/native callbacks.

## Ordered Gates

| Stage | Experiment | Status / Prerequisite |
| --- | --- | --- |
| 1 | Native base control, no GPT or VLA | Partial: codec and stationary settling passed; online local pose, full-body swept clearance and measured moving-base stop still required |
| 2 | Legal sensors to target point to staging proposal, no motion | Pending detector/depth/localization validation; resolver software is tested |
| 3 | Behavior-Skill A-short versus B-short, no GPT | Blocked on 1 and 2; 384 policy-action ceilings, independent ordinary resets |
| 4 | Behavior-Skill A versus B radio, no GPT | After interpretable short handoff; 3,224 total robot-action ceilings, one exploratory pair then replication |
| 5 | Arm/torso staging and return, no object interaction | Only after B; named-joint/FK/IK, full-body swept clearance and measured endpoint checks |
| 6 | C-short, then A/B/C radio | After staging qualification; preserve an empirically supported handoff envelope |
| 7 | Bounded classical contact diagnostic, conditional | Only if geometry/staging are qualified but policy contact still fails; not implemented by this overlay |
| 8 | Screen 2-3 visually verifiable tasks with the same frozen policy | Seek controllable pick/carry/place progress, not another large checkpoint search |
| 9 | H0 fixed hybrid versus H1 same motor with GPT executive | Only after useful hybrid motor competence; retain separate fresh verification |
| 10 | H1 versus H2 with causal episodic/visual memory | Only on a genuinely memory-sensitive online task; no further memory architecture first |

Async execution, monitoring and energy optimization follow demonstrated
competence; policy-action time share is not measured energy efficiency.

## Immediate Protocol

Stage 1 uses ordinary resets and tiny forward/backward/lateral/yaw commands, tens
of ticks rather than hundreds. Pass only with legal finite full native actions,
bounded arm/torso/gripper drift, consistent legal local pose, fresh per-tick
observations, established swept clearance, measured stops and exact action/time
accounting. Include blocked/unknown corridors and failed-stop tests. Do not use
the fixture's always-true geometry callbacks on BEHAVIOR.

Stage 2 validates detector-selected pixels, actual measured depth and legally
estimated camera-to-local-map transforms across several views. RTSM labels are
not sufficient alone given the prior false positives. Visual confirmation may
complement a detector. Any simulator-ground-truth analysis is strictly
out-of-band and unavailable to control, target selection, prompts or retrieval.
Measure error distributions relative to workspace and contact tolerances rather
than inventing a favorable cutoff after seeing outcomes.

For stage 3, use one frozen Behavior-Skill checkpoint and its exact image/state
normalization, full action interface and 32-action prefix. A-short receives 384
policy actions from ordinary reset; B-short adds qualified classical transit,
measured stop, fresh capture and real queue/history/in-flight drain before the
same policy-action ceiling. Total horizons intentionally differ. No GPT, memory,
retreat, task-specific weight routing or training. Log censored exposure rather
than assuming every ceiling was reached.

Record handoff state, visibility/image scale, base/EEF-target distances where
measured, pose confidence, gripper/joint values, exact policy fingerprint, reset
generation, first 10-30 native action vectors/magnitudes, contact/progress trends,
reversal/backtracking, failures and every rejected handoff. The V0.1 telemetry
callback provides the structured boundary record; native traces must still
supply actual first-action/progress measurements. No template invents them.

For stage 4, rerun A through the same current wrapper as B rather than substituting
an old baseline. Hold starts, task, instructions and checkpoint fixed. Classical
and settling actions consume the shared 3,224-action ceiling. Track Q/success
out-of-band plus visible progress, displacement, contacts, policy/classical
action shares, inference calls, wall time and admission rejection. One pair is
exploratory, not a reliable effect estimate.

## Later Boundaries

Stage 5's direct joint interpolation must reject blocked or unknown swept space.
A qualified external planner may replace it behind the existing interface; do
not weaken the gate. Stage 6 should leave ordinary visual-servo/contact work to
the VLA rather than staging the EEF onto the button. Permitted demonstrations
may inform the envelope without retraining, but record their task/episode
provenance and call such a setup demonstration-informed, not zero-shot target-task
generalization. Never load those scene states as ordinary test starts.

Radio power is not reliably visually observable in the current setup. Do not
interpret an uncertain verifier as failure of reasoning or claim that reaching
the radio proves power-on. Prefer a visibly verifiable task for H0/H1/H2.
GPT should respond to failures, lost targets, unexpected changes, uncertain
verification or exhausted plans; successful internal phase transitions need no
additional call. Paused-world recapture remains diagnostic only until separately
qualified, with no automatic stale-decision bypass.
