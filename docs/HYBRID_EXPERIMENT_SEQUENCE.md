# Hybrid Experiment Sequence

Updated 2026-09-22 after Action Compiler V1 integration. This sequence supersedes doing
more GPT-supervised full-radio trials before the motor handoff is interpretable.
It does not authorize new spend, training, license acceptance or weakening gates.

## Current Position

The [native hold-codec and stationary-settling diagnostics](HYBRID_NATIVE_QUALIFICATION_20260921.md)
passed. Hold commands match the pinned native convention; a five-tick stationary
diagnostic achieved five measured settled captures. Subsequent labeled
[native exploratory pulses](HYBRID_NATIVE_EXPLORATION_20260921.md) passed forward
response and measured braking at one start, but reverse and yaw tracking failed.
Moving localization, collision clearance and classical-to-policy handoff remain
unqualified. Same-start reproducibility is not general motion qualification.
The V0.1 resolver and telemetry are offline-tested utilities, not implementations
of the missing perception/collision/native callbacks.

A [retained-view depth coverage diagnostic](HYBRID_DEPTH_COVERAGE_20260921.md)
identified substantial blind regions around proposed 5 cm translations. A
[fresh calibrated hold and authored-mesh audit](HYBRID_CALIBRATED_GEOMETRY_20260921.md)
reproduced that result with contemporaneous intrinsics. Short-trace stationary
odometry passed its bounds, but the 60-tick follow-up exceeded them for head
translation and right-wrist rotation; moving localization remains unqualified. Accumulating the
short stationary trace did not resolve blind regions, and upstream planning
spheres do not enclose all authored collision vertices. Separate empty-scene
base-response calibration is authorized, but cannot bypass benchmark clearance.
The [empty-scene response experiment](HYBRID_EMPTY_BASE_DIAGNOSTIC_20260921.md)
did not qualify tracking or stopping. Its failed baseline and cross-axis motion
must be resolved separately from the learned policy; do not promote it to B-short.
The sustained native radio hold passed 60 zero-base ticks. This does not repair
the empty-fixture discrepancy. The subsequent native pulses provide the bounded
moving-base stop evidence; they do not validate the empty fixture.

The [motion-measurement diagnosis](HYBRID_MOTION_MEASUREMENT_DIAGNOSIS_20260921.md)
subsequently isolated inaccurate per-tick odometry and misleading instantaneous
velocity interpretation. Fixed-reference head-depth registration passed forward
and yaw replay checks and a live forward shadow run. This supports a separate,
explicitly labeled tiny-perturbation handoff diagnostic; it does not complete
target localization or certify a navigation corridor.

The [tiny-perturbation A-short/B-short diagnostic](HYBRID_TINY_HANDOFF_20260921.md)
completed with 384 policy actions in each condition, no immediate obvious visual
handoff disruption, and no task success in either condition. This is a limited
positive handoff result, not completion of target-directed stage 3. The next
experiment records same-boundary camera calibration for legal target measurement.

Two [fresh calibrated approaches](HYBRID_TARGET_ACQUISITION_20260921.md) now
completed. One ended without the target in view; the other supports an assisted
offline RGB-D measurement about 1.72 m horizontally from the base. This exposes
the remaining target-acquisition/transit gap, not a completed staging proposal.

## Current Parallel Results

The [compiler replay](ACTION_COMPILER_REPLAY_20260922.md) processed 78 legal
RGB-D views and produced zero qualified contact actions. The
[GraspGenX readiness audit](GRASPGENX_READINESS_20260922.md) identifies actual
R1Pro gripper/TCP and closure-geometry gaps; inference is not enabled.
The [online grounding report](ONLINE_TARGET_GROUNDING_20260922.md) records the
fresh shadow experiment, not navigation authority. The
[post-policy stop diagnosis](POST_POLICY_STOP_ANALYSIS_20260922.md) preserves
the failed stop gate. A fresh 60-hold diagnostic captured 240 physics substeps;
the velocity/position mismatch persists at that rate, and offline depth shows
little continuing drift after an early offset. No stop estimator was substituted
and no clearance or navigation qualification follows from those diagnostics.

## Ordered Gates

These are the updated 15 stages. Older experiment reports retain their original
stage numbers; use names rather than equating those historical numbers.

| Stage | Experiment | Status / Prerequisite |
| --- | --- | --- |
| 1 | Integrate Action Compiler V1, software only | Complete at `48695a0`; no native compiler motion |
| 2 | Retained legal RGB-D geometry/catalog replay | First replay complete; zero qualified contact candidates; actual-gripper inference blocked |
| 3 | Online target acquisition | Three fresh shadow resets complete; positive detection and failure cases retained; metric/multi-view qualification incomplete |
| 4 | Bounded target-directed base transit | Blocked on stop feedback, moving localization and swept clearance; no metre-scale move |
| 5 | Target-directed A-short/B-short, no GPT | After 3/4; prior tiny perturbation is not this experiment |
| 6 | Equal-total-action A/B radio | After interpretable target-directed short handoff; 3,224 actions each |
| 7 | Arm/torso free-space staging and return | After B; qualified FK/IK, clearance and measured endpoint |
| 8 | C-short, then A/B/C radio | After staging; unchanged frozen policy and explicit handoff envelope |
| 9 | Compiler candidate quality and execution, no GPT | Offline contract checks started; native positive execution still gated |
| 10 | Bounded classical contact/press | After grounded part semantics, contact normal and qualified staging |
| 11 | Screen 2-3 other tasks | Same frozen policy/compiler; no checkpoint search or task-specific switching |
| 12 | GPT selects compiled action IDs | Only after useful deterministic motor competence; no invented joint targets |
| 13 | Event-driven GPT recovery | After 12; target loss, failed primitives, ambiguity and changed state |
| 14 | Current state versus causal memory | Only on a genuinely memory-sensitive online task |
| 15 | Neural duty-cycle optimization | After success; action/DOF time shares are not measured energy |

Async execution, monitoring and energy optimization follow demonstrated
competence; policy-action time share is not measured energy efficiency.

## Immediate Protocol

An explicitly authorized simulator-only exploratory lane now permits bounded
native-radio response pulses with clearance recorded as **unknown**, not free.
It is separate from the strict qualification sequence below. Passing response
and stopping checks in this lane does not establish swept clearance or authorize
a strict hybrid handoff. No GPT or VLA calls are needed for these diagnostics.

Stage 4 uses ordinary resets and bounded local commands after tiny response tests, tens
of ticks rather than hundreds. Pass only with legal finite full native actions,
bounded arm/torso/gripper drift, consistent legal local pose, fresh per-tick
observations, established swept clearance, measured stops and exact action/time
accounting. Include blocked/unknown corridors and failed-stop tests. Do not use
the fixture's always-true geometry callbacks on BEHAVIOR.

Stage 3 validates detector-selected pixels, actual measured depth and legally
estimated camera-to-local-map transforms across several views. RTSM labels are
not sufficient alone given the prior false positives. Visual confirmation may
complement a detector. Any simulator-ground-truth analysis is strictly
out-of-band and unavailable to control, target selection, prompts or retrieval.
Measure error distributions relative to workspace and contact tolerances rather
than inventing a favorable cutoff after seeing outcomes.

For stage 5, use one frozen Behavior-Skill checkpoint and its exact image/state
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

For stage 6, rerun A through the same current wrapper as B rather than substituting
an old baseline. Hold starts, task, instructions and checkpoint fixed. Classical
and settling actions consume the shared 3,224-action ceiling. Track Q/success
out-of-band plus visible progress, displacement, contacts, policy/classical
action shares, inference calls, wall time and admission rejection. One pair is
exploratory, not a reliable effect estimate.

## Later Boundaries

Stage 7's direct joint interpolation must reject blocked or unknown swept space.
A qualified external planner may replace it behind the existing interface; do
not weaken the gate. Stage 8 should leave ordinary visual-servo/contact work to
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
