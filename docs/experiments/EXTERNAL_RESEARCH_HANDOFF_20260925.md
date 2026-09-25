# Physical Agent Experiment Handoff

**Prepared:** 2026-09-25

**Public repository:** `AranKomat/physical-agent-harness`

**Repository state before this handoff update:** `852e580` (`Close Phase 10 semantic execution comparison`)

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
- an explicitly non-benchmark soda-can fixture completed a real grasp and 5 cm
  lift; evaluator-only scoring and an independent legal RGB-D/proprio verifier
  both passed;
- GPT-6 Sol made all four bounded semantic motion choices correctly versus `2/4`
  for fixed routing, and a subsequent event-driven recovery converted a missing
  current-depth verification result from fixed `0/1` to GPT `1/1` through a fresh
  stationary recapture;
- a controlled memory-in-execution comparison produced verified progress of M0
  `0/1`, M1 `0/1`, and M2 `1/1`, with all three packet-bound decisions physically
  executed and independently verified;
- a legal RGB-D voxel gate failed even under an all-history, zero-pose-error upper
  bound, closing the remaining derived-state hypothesis for strict clearance;
- Behavior-Skill survives a small classical-to-policy handoff without an obvious
  immediate competence collapse, but neither policy nor hybrid conditions complete
  the radio task;
- GraspGen-X produces geometrically useful proposals, but the sole retained
  candidate requires major base/torso staging through unobserved space.
- the first prospective Sol-first/Astra-on-hold shadow cohort passed on a new
  strawberry category pair: Sol scored `2/2`, one correct negative hold triggered
  Astra, and Astra preserved it without a false correction.
- frozen active-workload accounting covers 9,216 Behavior-Skill actions and 1,048
  source-bound SAM invocations; policy warm chunks took about 157--160 ms median,
  sparse SAM scheduling avoided 89.48% of per-action-boundary invocations, and no
  unavailable frame read occurred.

No current result establishes reliable radio completion, strict navigation,
strictly safe manipulation, release/placement, a general motor policy, GPT
benchmark-task benefit, general memory benefit, or held-out robustness.

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
| 5. Localization, clearance, stopping | Partial; strict clearance branch closed for default cameras | Tested base stop predicate separates all 392 moving intervals from four stationary windows. Robust RGB-D registration and source-bound stop mechanics work in retained regimes. The final legal RGB-D voxel gate retained only 53.6% of newly occupied authored-vertex samples even under an all-history, zero-error upper bound. | A materially different legal sensing authority or disclosed embodiment is required. Broader localization remains incomplete. |
| 6. Strict target-directed base transit | Blocked | Exploratory target-directed transits and braking were executed and measured. | No transit is strictly admitted because external clearance is unknown. |
| 7. Arm/torso planning and return | Partial mechanics; strict execution blocked | Native 10 cm outward endpoint, return endpoint, 60 holds, and 348 total actions passed. cuRobo construction and no-op planning work after adapter fixes. | Current legal observations do not cover the swept whole-body path. Qualified scene collision, wheel scope, and native planner execution remain open. |
| 8. Matched hybrid A/B/C | Exploratory handoff-preservation subquestion complete | Four starts in balanced `BA/AB/BA/AB` order completed equal policy exposure with no immediate post-handoff away action and persistent current SAM candidates. | Neither condition succeeded, acquisition diverged before treatment, and no causal benefit was shown. Strict A/B/C remains blocked by Phases 5-7. |
| 9A. Proposal and gripper readiness | Proposal scope complete; execution partial | Exact hand geometry audited, GraspGen-X proposal path pinned, one offline candidate retained, and native empty-hand close/reopen passed 35/35 actions. | Contact calibration, payload stability, release, closer staging, and safe execution are not established. |
| 9B-9D. Stage, grasp, verify/place | Exploratory grasp/lift integration passed; strict path blocked | A scripted development fixture completed 30/30 normal actions, retained a soda can, and lifted it 5 cm. Evaluator-only and legal RGB-D/proprio verification both passed. | Initialization was scripted, clearance stayed unknown, and release/place plus benchmark-valid staging remain untested. Strict execution remains blocked by Phases 5-7. |
| 10. Recurrent GPT executive | Complete for frozen exploratory four-case scope | GPT-6 Sol scored `4/4` versus fixed routing's analytical `2/4`. All four packet-bound choices were executed for 30/30 actions and independently verified; both lifts rose 50.01 mm and both holds stayed within 0.011 mm. | Generalization beyond the scripted fixture remains untested. This is not benchmark success and strict clearance remains unknown. |
| 11. Event-driven recovery | Complete for one predeclared exploratory failure class | A first verification input deliberately lacked current left-wrist depth. The runtime independently detected it, GPT chose fresh recapture, six stationary actions executed, and fresh legal RGB-D/proprio verification passed. Fixed no-recovery scored `0/1`; GPT recovery scored `1/1`. | Natural failures, broader recovery classes, benchmark tasks, and strict motion remain untested. |
| 12. Memory in execution | Complete for one controlled visual-memory boundary | M0 and M1 held, while M2 used a labeled historical image to select and execute a verified 50.01 mm lift. Verified progress was `0/1`, `0/1`, and `1/1`; all conditions used the same current evidence and fixed motor. | Natural occlusion, more than one object/task, complete text summaries, and robustness remain untested. |
| 13. Robustness/held-out expansion | Controlled initial scope complete; broad scope open | Blue failed under Sol; orange passed at seed 71 and with a provenance-preserving composite distractor. Astra then corrected the exact frozen blue M2 packet, and its post-decision 50.014 mm lift verified. | Broad layouts/tasks remain untested. Preserve the mixed result; do not rewrite the original Sol failure. |
| 14. Efficiency optimization | Initial selective-review and active-duty scopes complete; broad scope open | Compact context remains default. The six-case frozen study scored Sol `5/6` and selective review `6/6`; the prospective strawberry pair scored `2/2` for both. Across eight Phase 8 runs, Behavior-Skill supplied 92.60% of action time, warm chunks took about 157--160 ms median, and sparse SAM scheduling avoided 89.48% of per-action-boundary invocations with zero unavailable frame reads. | Retain Sol as default and Astra as shadow-only review for M2 visual-memory holds. Cache hits, energy, broader false-correction risk, automatic authority, and efficiency while achieving task success remain untested. |

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

The subsequent explicitly non-benchmark development fixture established the first
positive contact-and-payload result. A soda can scripted into the open left gripper
was closed on, held, and lifted with 30/30 ordinary R1Pro actions. Evaluator-only
scoring measured a 50.015 mm height increase and only 0.003 mm change in relative
object-to-grasp-center distance during the lift. A separate verifier used retained
legal left-wrist RGB-D plus robot-only FK from legal proprioception: the grasp center
moved up 50.010 mm while the retained object surface had 0.9967 mask IoU, 0.452-pixel
centroid shift, and 0.014 mm median-depth change. See
[Development Grasp-And-Lift Gate](2026-09-25/DEVELOPMENT_GRASP_LIFT_20260925.md).

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

The final bounded derived-state check is documented in
[Phase 5E](2026-09-25/PHASE5E_LEGAL_VOXEL_GATE_20260925.md). Across 17 legal
capture transitions, the optimistic all-causal-history, zero-error variant marked
only 11,504 of 21,472 newly occupied authored-vertex samples free (53.6%) and 719
of 3,816 convex-hull voxel samples free (18.8%). The legal pose trajectory was
smooth enough to reject a gross odometry jump as the explanation. Do not build a
permanent 3-D mapping stack for this branch.

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

Key private Phase 9B exploratory evidence:

- `runs/development-grasp-lift-20260925-r1/receipt.json` SHA-256
  `275e0b2b3db2f7be4ff73f6a02ea9fe85865272e4571d01bb645a8d19baf28a9`;
- `runs/development-grasp-lift-20260925-r1/legal-visual-verification.json`
  SHA-256
  `b9682781087a864f2798fa92c93a3b0324c9f686f0658083b443c3e5e9714af3`.

Paid-call accounting after the partial Phase 10 decision cohort:

- reservations/cumulative count: `4,165`;
- confirmed cost: `$23.69443742140`;
- unresolved holds: `$34.979327322900`;
- total exposure: `$58.673764744300`;
- remaining under the campaign `$75` ceiling: `$16.326235255700`.

The added `$0.0138735` reservation belongs to a GPT-6 Sol Flex request that
returned an upstream OpenRouter HTTP 429. The cohort stopped immediately, no
retry was attempted, no structured decision was accepted, and no robot action
occurred. Preserve the unresolved hold unless provider accounting establishes a
settlement.

The blue-rule/blue-can response that hit the 128-token cap remains rejected. Its
separately approved 256-token replacement completed cleanly; the merged decision
report records the discarded attempt and zero automatic retries. No additional
paid calls are authorized by this handoff.

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

The no-paid fixed-routing `EpisodeRunner` baseline has now completed one 256-action
Behavior-Skill radio run plus nine measured settling holds. The integration passed,
but the radio remained off and final Q was zero. That is enough fixed-routing radio
evidence for now.

The development physical-effect prerequisite is now satisfied by the bounded
soda-can grasp-and-lift fixture. It remains exploratory, with `clearance=unknown`
and `motion_qualified=false`; it is not BEHAVIOR benchmark success.

The frozen four-case compact-V3 recurrent GPT comparison is complete. The final
score is GPT `4/4` versus fixed routing `2/4`, with four valid physical cases.
The final score SHA-256 is
`e242cbb680706018d47cb540e22b23c21ed8fc8a3acff4f296efe1c827291635`.

Phase 11 is complete for the first predeclared failure class. A completed lift's
first verification input lacked required current left-wrist depth; GPT requested a
bounded stationary recapture, and fresh paired evidence closed recovery. See
[Phase 11 Event-Driven Recovery](2026-09-25/PHASE11_EVENT_DRIVEN_RECOVERY_20260925.md).

Phase 12 is complete for one controlled visual-memory boundary. M0 and M1 held;
M2 used the historical visual evidence and executed a verified lift. See
[Phase 12 Memory In Execution](2026-09-25/PHASE12_MEMORY_EXECUTION_20260925.md).

Phase 13 robustness now has two independent axes. The first attribute change,
orange to blue, failed at M2: the model held despite receiving the historical
blue image. All three physical holds were independently valid. See
[Phase 13 Blue-Attribute Replication](2026-09-25/PHASE13_BLUE_ATTRIBUTE_REPLICATION_20260925.md).
The original orange result then passed at simulator seed 71 with the expected
`hold/hold/lift` decisions and verified physical effects. See
[Phase 13 Orange Seed-71 Replication](2026-09-25/PHASE13_ORANGE_SEED71_REPLICATION_20260925.md).
The corrected-metadata composite distractor also passed; the raw three-image
transport attempt remained incomplete and is not a semantic result. See
[Phase 13 Composite Distractor](2026-09-25/PHASE13_COMPOSITE_DISTRACTOR_20260925.md).
Astra then selected the correct lift on the exact frozen blue M2 packet where Sol
held, and a disclosed post-decision execution verified a 50.014 mm lift. See
[Phase 13 Sol-Astra Blue Comparator](2026-09-25/PHASE13_SOL_ASTRA_BLUE_COMPARATOR_20260925.md).
The frozen negative control then reused the blue historical image while requiring
orange. Both Sol and Astra correctly held. Across the positive/negative pair, Sol
scored `1/2` and Astra `2/2`; this supports targeted Astra review but not automatic
routing. See
[Phase 14 Selective Model Gate](2026-09-25/PHASE14_SELECTIVE_MODEL_GATE_20260925.md).
The next broader object/task axis also passed. The fixture changed from a soda can
under `picking_up_trash` to an apple under the official `freeze_fruit` task while
retaining the fixed 5 cm grasp/lift trajectory. The source apple lift and the
category-memory `M0/M1/M2` executions all passed: Sol selected
`hold/hold/lift`, the legal verifier measured a 50.016 mm M2 lift, and the final
comparison scored `0/1, 0/1, 1/1`. See
[Phase 13 Apple Category And Task Replication](2026-09-25/PHASE13_APPLE_CATEGORY_TASK_REPLICATION_20260925.md).
This broadens object/category evidence but does not establish general motor or
`freeze_fruit` benchmark competence because initialization and trajectory remained
scripted.

Latest paid-call accounting after the apple decisions is 4,187 cumulative calls,
`$23.77952692140` confirmed, `$34.979327322900` unresolved,
`$58.758854244300` total exposure, and `$16.241145755700` available under the
retained `$75` ceiling. The three apple decisions cost `$0.0087415`; physical
execution made no additional paid calls.

Phase 14 now also has a six-case executive model-duty comparison. All-Sol scored
`5/6` for `$0.02258675`; all-Astra scored `6/6` for `$0.10857125`; and the
predeclared selective Sol-to-Astra review rule scored `6/6` for `$0.05694175`
using two Astra calls. This reduced Astra duty by 66.7% and cost by 47.6% versus
all-Astra, at the expense of two extra calls and higher sequential latency. See
[Phase 14 Model-Duty Comparison](2026-09-25/PHASE14_MODEL_DUTY_COMPARISON_20260925.md).
The rule remains shadow/advisory because the six cases were accumulated and only
one negative review case was initially available.

The first prospective cohort is now complete on a new strawberry category pair.
Sol correctly lifted for strawberry and correctly held when the identical evidence
was asked to establish apple. The correct hold triggered Astra, which also held.
All-Sol and selective review both scored `2/2`; selective review used one extra
call, cost `$0.02345975` total, and produced no false correction. The source
strawberry lift rose 49.931 mm by evaluator scoring and 50.023 mm by legal RGB-D
plus robot-only FK. See
[Phase 14 Prospective Selective Review](2026-09-25/PHASE14_PROSPECTIVE_SELECTIVE_REVIEW_20260925.md).
Latest accounting is 4,194 cumulative calls, `$23.87720292140` confirmed,
`$34.979327322900` unresolved, `$58.856530244300` exposure, and
`$16.143469755700` available under `$75`.

Frozen active-workload neural-duty accounting is also complete for the eight-run
Phase 8 Behavior-Skill/SAM cohort. It validates 9,216 policy actions, 288 policy
inference chunks, and 1,048 source-bound SAM results. Behavior-Skill supplied
92.60% of native action time; policy warm-chunk medians were 156.6--160.2 ms, while
each separately launched run paid a 39.73--42.02 s cold start. Sparse SAM
scheduling reduced invocations by 89.48% versus every action boundary, with zero
unavailable frame reads. See
[Phase 14 Active Neural Duty](2026-09-25/PHASE14_ACTIVE_NEURAL_DUTY_20260925.md).
The cohort had zero task successes and retained neither cache-hit nor energy
telemetry, so it does not establish an efficiency/competence frontier.
Do not rerun or prompt-tune blue. Keep the same evidence contract, current
boundary, motor backend, and verifier. Continue in this order:

1. retain Sol as default and keep Astra review shadow-only while collecting broader natural M2 holds;
2. treat the passed apple/category axis as broader fixture evidence, not general motor competence;
3. retain the Sol failure, Astra correction, negative control, passed seed, and passed distractor together;
4. preserve persistent policy residency and sparse SAM scheduling in the next
   successful workload, while prospectively recording cache hits and device power.

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
