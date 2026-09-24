# Physical Agent Experiment Handoff

**Prepared:** 2026-09-25

**Public repository:** `AranKomat/physical-agent-harness`

**Repository state before this handoff update:** `61bf0f5` (`Add external experiment handoff`)

**Operator-local experiment plan:** `PHYSICAL_AGENT_EXPERIMENT_SEQUENCE_HANDOFF_20260923.md`

**Detailed chronological ledger:** `docs/experiments/EXPERIMENT_HANDOFF_20260923.md`

## Executive Summary

The harness software, causal evidence contracts, semantic-memory path, and several
simulator actuator interfaces are working. The main blocker is no longer missing
architecture. It is the lack of a legal, current whole-body clearance authority for
the default BEHAVIOR R1Pro embodiment. The three onboard RGB-D cameras leave large
parts of moving base, torso, arm, and hand geometry unobserved. Unknown space is not
being treated as free.

The strongest completed results are:

- retained Embodied Runtime V3 replay passed 64 causal checks;
- the discovery-to-tracking identity gate passed all 14 controlled cases and
  correctly abstained after simultaneous loss of two identical objects;
- GLM 5.3 Flash works as asynchronous historical discovery, but not as a
  two-second synchronous control dependency;
- compact V3 GPT context matched rich context on all four frozen decisions while
  reducing prompt tokens by 19.3% and cost by 13.1%;
- base stop discrimination, endpoint/return mechanics, and empty-hand gripper
  aperture tracking work in the tested simulator regimes;
- Behavior-Skill survives a small classical-to-policy handoff without an obvious
  immediate competence collapse, but neither policy nor hybrid conditions complete
  the radio task;
- GraspGen-X produces geometrically useful proposals, but the sole retained
  candidate requires major base/torso staging through unobserved space.

No current result establishes reliable radio completion, strict navigation,
safe manipulation, a general motor policy, GPT task benefit, memory task benefit,
or held-out robustness.

## Experimental Boundaries

Controller-facing inputs are limited to onboard RGB, depth, proprioception,
legally estimated local pose, and state derived from those observations. Simulator
object poses, segmentation, collision state, scorer/task state, external cameras,
future evidence, and direct state mutation are excluded from control. Evaluator
truth may be used only after execution for scoring.

Unknown identity, pose, clearance, contact, or stopping state remains unknown.
Exploratory simulator motion is labeled as such and does not qualify strict motion.
Frozen policies retain their native camera/state preprocessing, normalization,
action codec, temporal ensemble or chunk recipe, reset semantics, and full 23-DoF
action interface. Only one actuator owner may run at a time.

## Phase Status: 0-14

| Phase | Status | What is established | What remains |
| --- | --- | --- | --- |
| 0. Reproducibility/preflight | Passed for current scope | Public validation, ownership checks, retained evidence checks, and private suites have repeatedly passed at recorded revisions. | Re-run preflight after material environment or code changes. |
| 1. Retained V3 replay | Complete | Six retained GLM packets, 67 sightings, and 64 causal checks passed with no future, stale, or cross-source evidence accepted. | No live semantic-accuracy or latency claim follows. |
| 2. Discovery-to-SAM identity | Complete for controlled 14-case gate | Safe continuous binding, loss invalidation, reset/session checks, stale-source rejection, and ambiguous identical-object reacquisition all pass. | Natural-rollout replication is useful robustness evidence, not a prerequisite for the contract result. |
| 3. Live shadow discovery | Complete as asynchronous discovery; fails synchronous gate | Frozen four-boundary GLM cohort matched semantic visibility 4/4; 3/4 strict packets entered historical inventory. | Zero of four calls met the two-second control window. Use results only for history and fresh reacquisition requests. |
| 4A. Discovery prompt study | Partial | V3 task-directed half achieved 2/2 radio recall, 0/2 false positives, and 3/4 strict packets. | Task-blind matched cohort stopped after one valid result, one unresolved timeout, and two unsent calls. A new declared continuation is required. |
| 4B. Executive context study | Complete for frozen four-boundary scope | Rich and compact GPT-6 Sol Flex decisions agreed 4/4. Compact reduced prompt tokens 19.3%, cost 13.1%, and mean latency 1.17 s. | Generalization and live causal benefit remain untested. Compact V3 is the default; rich is the comparator. |
| 5. Localization, clearance, stopping | Partial; default sensor search closed and clearance blocked | Tested base stop predicate separates all 392 moving intervals from four stationary windows. Robust RGB-D registration and source-bound stop mechanics work in retained regimes. A pinned source audit confirms there is no unused default R1Pro LiDAR/range/contact/active-camera channel in the challenge observation contract. | A materially different legal RGB-D/proprioceptive method or disclosed embodiment is required. Broader localization remains incomplete. |
| 6. Strict target-directed base transit | Blocked | Exploratory target-directed transits and braking were executed and measured. | No transit is strictly admitted because external clearance is unknown. |
| 7. Arm/torso planning and return | Partial mechanics; strict execution blocked | Native 10 cm outward endpoint, return endpoint, 60 holds, and 348 total actions passed. cuRobo construction and no-op planning work after adapter fixes. | Current legal observations do not cover the swept whole-body path. Qualified scene collision, wheel scope, and native planner execution remain open. |
| 8. Matched hybrid A/B/C | Exploratory handoff-preservation subquestion complete | Four starts in balanced `BA/AB/BA/AB` order completed equal policy exposure with no immediate post-handoff away action and persistent current SAM candidates. | Neither condition succeeded, acquisition diverged before treatment, and no causal benefit was shown. Strict A/B/C remains blocked by Phases 5-7. |
| 9A. Proposal and gripper readiness | Proposal scope complete; execution partial | Exact hand geometry audited, GraspGen-X proposal path pinned, one offline candidate retained, and native empty-hand close/reopen passed 35/35 actions. | Contact calibration, payload stability, release, closer staging, and safe execution are not established. |
| 9B-9D. Stage, grasp, verify/place | Blocked | No positive contact or task action has been qualified. | Requires Phases 5-7 plus contact/grasp verification. |
| 10. Recurrent GPT executive | Not meaningfully started | Compact V3 context and bounded semantic cycle infrastructure are ready. | Needs a useful execution path before causal task comparison. |
| 11. Event-driven recovery | Not started | Failure history and verifier contracts exist. | Needs a real recoverable physical failure and qualified actions. |
| 12. Memory in execution | Not started at task level | Causal memory representations and replay checks exist. | Needs an executable memory-sensitive episode; answer-only ablations are insufficient. |
| 13. Robustness/held-out expansion | Not started | Controlled identity cases and several simulator starts exist. | Requires a working base system before seeds, layouts, distractors, and tasks are meaningful. |
| 14. Efficiency optimization | Not started as end-to-end study | Compact context and two-rate perception evidence provide candidates. | Optimize only after competence is demonstrated. |

## Major Positive Results

### Causal semantic state and identity

Phase 1 replay admitted no stale, future, or cross-source evidence. Compact-context
generation, mandatory-fact retention, source dimensions, crop lineage, duplicate
handling, and historical/current separation all passed.

Phase 2 used native BEHAVIOR RGB-D with two identical pumpkins. Both disappeared
for three frames and reappeared on exchanged sides while SAM reused local IDs 0 and
1. The runtime retained category memory but denied executable identity bindings.
The evaluator later found the IDs happened to follow the same simulator instances;
that coincidence remained quarantined and did not alter runtime state. Local and
remote reports were byte-identical.

SAM 3.1 timing on this trace was 479 ms for initial acquisition and approximately
147 ms median / 149 ms p95 for warm propagation. This supports discovery at a low
rate and source-bound tracking at a higher rate, not SAM text prompting on every
frame.

### Discovery and model selection

GLM 5.3 Flash is the current occasional inventory candidate. On six retained views,
it produced 6/6 valid inventories, 37/39 synonym-joined category coverage, and a
4.53-second median practical latency. The local VLX-Seek pipeline produced 25/39
coverage and 6.03-second median latency including proposals. This was a small
single-room development comparison, not a general model ranking.

The prospective Phase 3 cohort exposed the operational limitation: GLM latency was
4.42-12.35 seconds, with zero results inside the two-second live-use window. Valid
results may update historical inventory and request a fresh current capture; they
must not refresh current geometry or directly authorize motion.

GPT-6 Sol Flex remains the default executive/verifier model. GPT-6 Astra should be
retained for a future matched diagnostic because external demonstrations suggested
it may be stronger for robotics, but that comparison has not been run. Luna was
tested and retired: only 4/6 valid inventories, 14.28-second median latency, and
17/39 original category coverage. Codex subscription transport is a separate
experimental condition and is not interchangeable with API inference.

### Executive context

The frozen Phase 4B comparison made eight GPT-6 Sol Flex calls. Rich and compact
contexts agreed on all four accepted decisions: approach twice, press once, then
stop blind pressing and request fresh unobstructed power-state evidence. Compact
used 10,087 prompt tokens versus 12,503, cost `$0.01582075` versus `$0.01821575`,
and reduced mean latency from 6.324 to 5.151 seconds. Use compact V3 by default.

### Native motion mechanics

The retained Phase 5D audit correctly rejected every one of 392 moving intervals
and accepted prehold/final five-interval windows for independent 6.4 cm and 45.1 cm
base transits. The tested command profile reached 0.049 m/s. This establishes the
simulator control-facing stop discriminator in that regime, not collision safety,
navigation, or physical-hardware braking distance.

Phase 7 endpoint/return validation completed all 348 actions for a 10 cm outward
EEF target and return, including 60 reserved holds. It establishes endpoint and
position-window mechanics only. cuRobo V2 can be constructed and return a no-op
trajectory; its singleton-leading 4-D trajectory output exposed and led to an
adapter compatibility fix.

The native empty-hand gripper probe closed from 49.999 mm to 0.00019 mm and reopened
to 49.999 mm over 35/35 actions. Maximum finger asymmetry was 1.315 micrometres and
maximum held-channel drift was 11.761 micrometres. This does not establish contact,
force, friction, attachment, payload stability, or release.

## Major Negative Results And Blockers

### No reliable general motor policy

The main tested candidates were:

| Candidate | Scope and outcome |
| --- | --- |
| Behavior-Skill `pi05-pt50-skill` | Best working reference interface. Approached and contacted the radio, but displaced or rotated it instead of activating it. One GPT-supervised radio run used 3,224 actions and 18 GPT calls and ended false/Q=0. |
| Corvid `backbone_foundation_100ep` | All-task candidate. It sometimes grasped/carried a bin, but did not complete trash; radio supervision ended false/Q=0. A crossover instruction test did not show convincing redirection. |
| Kmy GR00T N1.7 checkpoint238000 | Interface worked and navigation occurred, but no task completion was established; late trash views were markedly tilted. |

Official radio-only pi0.5/GR00T, RLinf PT50, Ryan all100, StarVLA, and related
artifacts were also inspected or briefly auditioned. None established a reliable
general motor. Several early trials were too short to count as full evaluations.
Behavior-Skill is frozen as a reference, not declared solved or general.

In the matched GPT comparison, Corvid and Behavior-Skill used the same start,
action cap, GPT-6 Astra executive/verifier protocol, skill menu, and current-only
evidence rules. Both failed. Corvid repositioned and reached toward the radio late;
Behavior-Skill repeatedly contacted it. This suggests both coarse planning/recovery
and fine contact control are limiting, not that GPT alone can repair the motor.

### Current whole-body clearance cannot be certified

The default R1Pro challenge configuration exposes three fixed onboard RGB-D cameras:
head, left wrist, and right wrist. It has no LiDAR links, no active camera controller,
no camera action indices, and no camera state in the submitted 61-D proprioception.
The world-fixed `external_sensor0` used in a general demo configuration is not an
admissible challenge control input. Simulator contact and collision APIs are
privileged state, not legal clearance authority.

Offline strict clearance searches rejected every tested 10 cm EEF direction. The
best alternative still left 97.1% of endpoint exposed vertices outside all retained
camera views. An exhaustive wrist-posture screen and a 228-pose fixed custom-camera
screen also failed. Even the union of all custom poses left 20 of 171 newly occupied
voxels unseen for a 5 mm segment. Do not repeat nearby camera-pose searches or treat
historical view unions as current free space.

This is a missing-evidence result, not evidence of a collision. It blocks strict
Phases 6-9 under the current rules.

### Hybrid intervention has no demonstrated task benefit

The counterbalanced Phase 8 cohort completed four starts in `BA/AB/BA/AB` order.
Each condition received 1,152 Behavior-Skill actions plus 92 intervention/control
actions. All eight runs retained a unique current SAM candidate at every sampled
boundary and had no immediate away action after handoff. This answers the narrow
question that a small intervention does not obviously destroy the frozen policy.

It does not show benefit. Neither condition succeeded, acquisition trajectories had
already diverged before treatment, and three of four full-window B-minus-A target
projections were nonpositive. Stop repeating nearby A/B diagnostics until strict
staging or a stronger branch protocol exists.

### Grasp proposals are not the bottleneck

The pinned GraspGen-X `sweep_volume_v2` path produced useful proposals with about
592 MiB peak allocated GPU memory. Numerical IK, endpoint, dense-target, closure,
and sampled-path screens leave candidate 0 as the sole offline survivor. Candidate
0 is about 1.225 m from the fixed shoulder, roughly 0.354 m beyond an optimistic
fixed-torso reach bound. Its path leaves 44,033 of 116,020 exposed samples outside
all retained camera views. More proposal batches will not resolve this.

## Important Fixes Made During Experiments

- Native scripted captures sometimes returned stale RTX/Fabric buffers. Capture
  collection now warms rendering, compares consecutive reads, and rejects frames
  whose final-read RGB mean absolute error exceeds `5/255`. Corrupted-looking
  images were simulator buffer failures, not generated world-model images.
- A standalone CLI initially could not discover the public package. Package
  discovery was corrected; local and remote identity replays then matched exactly.
- The original SAM incremental trace had an off-by-one source-frame bug. It was
  invalidated and replaced with corrected source-bound runs.
- cuRobo returned trajectories shaped `[1, 1, T, J]`; the adapter now accepts
  singleton-leading 2-D/3-D/4-D forms while rejecting multiple batches/goals.
- RGB-D base registration was made robust to outliers with a fixed Tukey loss and
  measured camera-FK initialization. Evaluator poses remain scoring-only.
- A first gripper launch failed before motion because its policy callback rejected
  keyword `obs`. The setup failure was retained; the corrected run completed.
- The initial GLM room inventory hit the 2,048-token ceiling and was rejected as
  truncated JSON. No silent repair or retry occurred.
- One early memory comparison contained future place-B identity information and is
  invalid for causal claims. It must not be reused.
- OmniGibson state serialization failed the frozen branch-equivalence gate: maximum
  state error was `2.62e-6` against `1e-6`, clock state was not restored, and fresh
  renders were not bit-identical. It was not used to claim matched branching.
- An automatic Ubuntu update temporarily mismatched loaded NVIDIA libraries. An
  approved reboot restored CUDA; no security update settings were disabled.

## Current Software And Artifact State

The evidence baseline was clean at `d81b134` and includes the phase-level reports.
The private lab contains raw captures, videos, receipts, model adapters, and scripts.
The public reports intentionally omit private assets and host credentials.

Key private Phase 9A evidence:

- `runs/native-gripper-aperture-20260925-r2/receipt.json`
  SHA-256 `b0c440c4c4f98353530aae51c3aeb297b56444b7b55965a8f614f7fb4254acdc`;
- retained setup failure `r1` SHA-256
  `676ad93accffbdc274c5c50f595ed1bfaae11e07fe0eee9a5560ea9c90c0bb69`;
- `scripts/probe_gripper_aperture.py` SHA-256
  `07f5c76ad00a62cd5a26aae410c9f37a28246f26583b44ab50a578ab78a73bd6`.

Paid-call accounting at this snapshot:

- reservations/cumulative count: `4,159`;
- confirmed cost: `$23.68785342140`;
- unresolved holds: `$34.965453822900`;
- total exposure: `$58.653307244300`;
- remaining under the campaign `$75` ceiling: `$16.346692755700`.

No new paid calls are authorized by this handoff. Failed or unresolved requests
must not be retried without a newly declared scope.

## Recommended Next Decision

The native sensor-authority audit is now closed as a phase-level result. The pinned
default challenge embodiment offers no unused legal LiDAR, range, contact,
active-camera or external-sensor channel capable of resolving the clearance gate.
Do not run another camera mount or wrist-pose search without a materially different
hypothesis.

Then choose one track explicitly:

1. **Strict qualification:** remain blocked until a challenge-legal current
   clearance authority or different disclosed embodiment is available. Do not
   weaken `known_space` or swept-collision checks.
2. **Benchmark-valid exploratory execution:** continue with allowed observations,
   label external clearance unknown, and use hidden collision/task truth only for
   retrospective scoring. This can measure policy/system outcomes, but it cannot be
   reported as strict motion qualification.

If the exploratory track is chosen, the next useful experiment is a bounded Phase 10
radio run through the actual recurrent runtime, not another fixed-menu supervisor or
10 cm stage/retract microdiagnostic. Integrate the existing native Behavior-Skill
backend with `EpisodeRunner`, compact V3, a separate verifier, legal current
observations, memory in shadow mode, fixed action/call budgets, no retries, and hidden
task truth used only after execution. Keep `clearance=unknown` and
`motion_qualified=false`; this is benchmark-valid exploratory evidence, not strict
motion qualification.

Run offline/doctor/native preflight before model calls. No paid GPT execution is
authorized by this handoff, so declare a new call and cost scope before the live run.
After a useful recurrent episode exists, continue in this order:

1. compact-V3 GPT executive versus the same frozen-policy control;
2. event-driven recovery from a predeclared failure;
3. M0/M1/routed-M2 memory comparison on the same executable episode;
4. seeds, placements, distractors, and a held-out task;
5. duty-cycle and model-cost optimization.

## What Not To Repeat

- broad checkpoint search without a concrete new compatibility hypothesis;
- more GraspGen-X proposal batches on the retained frame;
- generic SAM wording sweeps on the same radio images;
- another tiny base pulse only to prove bounded movement is possible;
- nearby wrist or fixed-camera pose searches;
- another one-pair or nearby Phase 8 A/B handoff diagnostic;
- answer-only memory ablations presented as embodied benefit;
- synthetic capability success presented as native qualification;
- any run that uses hidden simulator state for control.

The project has enough architecture. The next useful contribution is a clear
experimental choice about the unresolved sensing boundary, followed by one bounded
integration test or an explicit statement that strict execution is blocked by the
default embodiment.
