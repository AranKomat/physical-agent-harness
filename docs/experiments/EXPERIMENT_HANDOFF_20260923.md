# Experiment And Verification Handoff

As of 2026-09-23. Repository: https://github.com/AranKomat/physical-agent-harness.
This self-contained snapshot covers Embodied Runtime V3, responsibility-based
consolidation at `35bc2b6`, ownership cleanup at `4aa1b47`, the corrected Phase 1
retained replay, Phase 2 CPU contract replay, a fresh 25-frame SAM diagnostic,
and native sensor restoration on the new single-GPU host.
Use the commit containing this
file as the code snapshot. No new model inference or robot trials were run for
the Phase 0/1 follow-up; retained responses and pixels were replayed through code.
Historical results below retain their original limitations and evaluation scope.
The [seven-frame scripted SAM follow-up](2026-09-23/SCRIPTED_SAM_LOSS_20260923.md)
finds two pumpkin candidates, empty off-target frames and a returning local ID
across changed views. Identity remains unknown; this does not qualify natural
loss/reidentification. No new robot actions or paid calls; private suite 968 plus
one existing skip.
The latest [stationary SAM join](2026-09-23/STATIONARY_SAM_JOIN_20260923.md)
records a fresh-capture adapter failure and its bounded correction separately
from model quality and Phase 5 qualification.
The subsequent [native collision-settings inspection](2026-09-23/R1PRO_NATIVE_COLLISION_SETTINGS_20260923.md)
passes its runtime-filter scope after the approved GPU reboot: 14 symmetric
filters and 164 enabled collider approximations. Follow-up r4 measures effective
contact offsets of 1.36-5.04 mm and zero rest offsets, with self-collision enabled
and all 44 joint collision flags disabled. Cooked geometry and safe motion remain
unqualified. No planner exclusions changed; private suite: 901 passed, one skip.
The [native convex-representation follow-up](2026-09-23/R1PRO_NATIVE_CONVEX_20260923.md)
finds authored hulls conservatively contain all 161 returned native hulls, despite
only 2 matching bidirectionally at 10 micrometers. Keep the conservative geometry
for offline changed-posture/swept-path tests. Wheel/active-shape correspondence
and execution remain open. Latest private suite: 907 passed, one skip.
The [frozen single-joint path audit](2026-09-23/R1PRO_JOINT_PATHS_20260923.md)
now passes 28 paths using conservative geometric support/arc bounds. An initial
FCL-distance assumption failed endpoint consistency and is not promoted. Minimum
revised whole-path bound is 20.91 mm; external clearance, wheel geometry and
execution remain unqualified. Private suite: 917 passed, one skip.
The [arm depth-support audit](2026-09-23/ARM_DEPTH_SUPPORT_20260923.md) finds
96.44% of selected samples outside all views. An explicitly approved
[exploratory wrist probe](2026-09-23/WRIST_PROBE_20260923.md) followed +0.008 rad
accurately but failed sustained velocity-based stop checks, so return was not
attempted. It used 35 actions and was not retried. This is not Phase 7 completion;
external clearance and stop semantics remain open. Private suite: 931 plus one skip.
The [offline velocity follow-up](2026-09-23/WRIST_VELOCITY_ANALYSIS_20260923.md)
validates all 35 action intervals, but cannot distinguish substep oscillation
from readback behavior. No new motion or threshold changes; the proposed
physics-step hold-only diagnostic requires separate approval.
That approval subsequently arrived; the [30-action diagnostic](2026-09-23/WRIST_HOLD_SUBSTEP_20260923.md)
completed with 120 physics samples and no callback errors. Raw wrist velocity
differs substantially from both matching position-derived estimates. Final stop
still fails; moving/braking estimator validation and base stopping remain open.
The subsequent approved [instrumented motion diagnostic](2026-09-23/WRIST_MOTION_SUBSTEP_20260923.md)
completed 35 actions and 140 physics samples. Position-derived velocity detected
the commanded +0.006 rad motion, but sustained raw stop checks failed; no return
was attempted. Next is offline whole-window stop analysis, not another identical
probe. Base stopping, braking and external clearance remain unqualified.
The [offline stop-window replay](2026-09-23/WRIST_STOP_WINDOWS_20260923.md)
now distinguishes all 10 ramp windows from all 30 stationary windows using the
existing wrist threshold and position differences. Raw full-window speed rejects
all 30 stationary windows. This is diagnostic evidence, not a replacement stop
authority: independent base evidence and measurement uncertainty remain open.
The [stop-observation audit](2026-09-23/STOP_OBSERVATION_CONTRACT_20260923.md)
also found and removed unconditional stop acknowledgement in the legacy private
radio driver. Historical cleanup acknowledgements are not physical stopping
evidence. The next native protocol needs complete joint/base measurement and
uncertainty qualification, not an identical wrist-only repeat.
The approved [full-body hold calibration](2026-09-23/FULL_BODY_STOP_CALIBRATION_20260923.md)
completed 30 actions with legal joint telemetry and separately isolated evaluator
base poses. Maximum sampled base displacement was 1.192 micrometres despite two
raw base speed threshold crossings. Legal RGB-D/FK agreed with evaluator relative
base poses within 8.323 micrometres on this stationary trace. Original stop still
failed; deliberate-motion/braking accuracy and external clearance remain open.
The separately approved [base pulse calibration](2026-09-23/BASE_PULSE_CALIBRATION_20260923.md)
completed 30 actions but the 0.005 m/s command produced only 2.067 micrometres
forward displacement, not the nominal 1.667 mm. It therefore did not create a
useful moving/braking contrast. Next inspect applied control targets/drive
settings before attributing a dead zone or proposing a stronger pulse.
The [zero-command drive inspection](2026-09-23/BASE_DRIVE_INSPECTION_20260923.md)
confirmed native damping of 1e7 and sentinel-scale raw effort/velocity limits.
Joint-wrapper limits (100 effort, 1/15 velocity) are fallbacks, not measured
physical caps. One adapter error was corrected and retained as a failed attempt.
Audit the reset/limit lifecycle and applied targets before escalating motion.
The [instrumented base pulse](2026-09-23/BASE_DRIVE_PULSE_20260923.md) now
confirms finite limits become sentinel-scale across evaluator settings. Controller
output matches PhysX targets exactly, but the same tiny 2.067 micrometre response
recurs. Command delivery is observed; downstream native physical response remains
unresolved. No motion qualification or physics-parameter changes follow.
The expanded r2 pulse records virtual-base positions and reports no sleeping
samples: the joints themselves also barely move. This argues against sleeping
or body-pose-only stale readback. Further unchanged repeats are not warranted;
solver/contact response needs a specific experimental hypothesis.
The [four-iteration solver variant](2026-09-23/BASE_SOLVER_VARIANT_20260923.md)
failed the five-hold stop preflight with larger raw wrist-velocity discrepancies.
It issued no forward command, is not adopted, and cannot answer whether extra
iterations improve base motion. Original physics defaults and gates stay intact.

## 1. Executive Summary

We are developing a sensor-grounded BEHAVIOR/R1Pro harness in which an executive
chooses bounded actions, independent verification updates task progress, and
structured state plus causal visual/event memory reduce repeated reasoning.
The direction now includes classical geometry/planning with an optional frozen
vision-language-action policy (VLA), rather than assuming a VLA solves every motor
problem. No policy was trained by this project.

**Software integration is substantially ahead of native task qualification.**
Bounded live semantic cycles, causal memory replays, several real policy interfaces,
small exploratory handoffs, and useful perception component tests have completed.
No reliable general motor, successful full radio task, or executed-task improvement
from GPT supervision or memory has been demonstrated in the reported trials.

Current working choices, not globally qualified winners:

- New GPT experiments default to Sol Flex; Luna is retired from active options
  by user decision. Its [inventory test](2026-09-23/SOL_LUNA_INVENTORY_20260923.md)
  remains archived: 4/6 valid versus Sol's 6/6; GLM remains the inventory candidate.
  Plan a later matched Sol/Astra executive comparison; public demos are a
  motivation, not local performance evidence. Historical cohorts stay distinct. See the
  [migration and proposed comparison](2026-09-23/GPT6_SOL_LUNA_MIGRATION_20260923.md).
- Behavior-Skill is the frozen reference motor for interpreting short handoffs.
  It approaches and contacts the radio but has not reliably activated it.
- GLM 5.3 Flash is the leading occasional scene-inventory candidate from a small
  matched-view test. Its new V3 delta prompt is still untested with the endpoint.
- The corrected local SAM 3.1 streaming worker tracks between discovery calls.
  Tracker IDs do not independently establish semantic or physical identity.
- Measured depth and legally estimated poses supply geometry. Semantic boxes,
  successful ICP fits, and planner outputs do not themselves authorize motion.
- GraspGenX and cuRobo have software interfaces, not qualified native R1Pro
  manipulation pipelines. All six compiled capability templates remain unpromoted.

The perception follow-up is **hard discovery-to-SAM association/loss replay**;
robot-only collision-model qualification is also in progress under the approved
isolated cuRobo preparation, without motion.
Retained discovery -> strict V3 contracts -> inventory -> compact context now
passes its declared offline scope. Do not restart policy searches or add another
framework first.

### Latest Progress And Full Remaining Sequence

This table uses the current 0-14 sequence, not the original eight-stage numbering.
"Not done" means the intended qualified experiment remains unperformed; related
historical diagnostics are described later in this document.

| Phase | Status at this snapshot | Remaining work |
| --- | --- | --- |
| 0. Preflight | Software/retained audit, SAM restoration, numeric pins and native sensor smoke passed | Restore policy environment; qualify live integration and recover missing provenance where possible |
| 1. Strict V3 retained replay | Passed bounded offline scope: six GLM packets, 67 sightings, 64 checks, 16 expected rejections | Native availability timing, delayed identity publication and live delta prompt are not qualified |
| 2. Hard discovery/SAM identity and loss | CPU contracts on 10/14 cases; fresh SAM inference on four bounded cases; physical association unqualified | Native loss/reappearance/crossings, independent association and live timing; basic simulator/sensors now restored |
| 3. Live shadow GLM discovery | Not done with V3 | Record real observation/publication clocks, current-source associations and asynchronous inventory updates |
| 4. Delta/inventory and compact/rich comparisons | Not done | Frozen causal boundaries, held-out views and separately authorized paid calls |
| 5. Native localization, clearance and stopping | Partial diagnostics; fresh paused recapture consistency passes | Positive live target fusion, independent motion accuracy, low-body coverage and whole-robot stop qualification |
| 6. Strict base transit | Not qualified | Small measured transit under strict gates; earlier unknown-clearance probes do not qualify it |
| 7. Free-space arm staging and return | Robot-only FK, native hull containment and 28 frozen joint-path bounds pass their scopes; exploratory wrist motion occurred but return failed its stop gate | External clearance, whole-robot stop qualification and a qualified native stage/return; exploratory motion is not completion |
| 8. Matched A/B/C | Exploratory A/B exists, not qualified comparison | Balanced starts/order and declared equal budgets after base/arm gates |
| 9. Compiler manipulation | Contracts and negative replay only | Positive sensor-grounded candidate, safe execution and independent outcome verification |
| 10. GPT benefit | Prior supervised failures, no benefit established | Matched current-wrapper controls with useful execution backend |
| 11. Recovery | Fixture support only | Native detected failure -> bounded recovery -> verified progress |
| 12. Executed memory benefit | Retained decisions only | Execute M0/M1/routed visual-memory conditions with one frozen backend |
| 13. Robustness | Component negatives only | End-to-end seeds, placements, distractors, delays and forced failures |
| 14. Efficiency | Component timings only | End-to-end latency/cost/duty-cycle comparison after correctness |

The [native sensor restoration](2026-09-23/NATIVE_SENSOR_RESTORATION_20260923.md)
passed on reserved development instance 301, with zero commanded actions/API
calls and clean process exit. Three RGB-D cameras and the 61-D/23-D/30-Hz robot
interface work. This does not qualify geometry, physical association or motion.
All sensor evidence is backed up locally; the old host remains stopped.

The [paused recapture follow-up](2026-09-23/PAUSED_RECAPTURE_20260923.md) adds
three live zero-action captures after restoring geometry numeric pins. Head-depth
pixels were identical and registered with zero displacement; this is not moving
accuracy. Public odometry rejected equal-time recaptures without guard changes.
The retained 33-pose replay matched prior output to numerical precision. New
private suite snapshot: 648 passed, one skip; public runtime remains unchanged.

The [cuRobo V2 FK diagnostic](2026-09-23/CUROBO_R1PRO_FK_20260923.md) now
validates real GPU kinematics against yourdfpy for 37 numerical configurations
and against one native measured posture. It explicitly composes missing tool
frames using generated asset offsets. Collision/planning remain unqualified;
the known sphere undercoverage is unresolved. A native-schema parser error in
attempt r1 was fixed before declared r2; both are retained. Latest private suite:
687 passed, one skip. No new robot actions or paid calls.

The subsequent [authored collision-envelope audit](2026-09-23/R1PRO_COLLISION_ENVELOPE_20260923.md)
encloses all 164 meshes / 9,639 vertices, but finds 128 non-exempt sphere overlaps
across 22 link pairs, all with disjoint authored-mesh AABBs. The candidate is not
adopted for planning. No exclusions changed; native cooked shapes remain
unqualified. Latest private suite: 730 passed, one existing skip. CPU-only work,
no motion or paid calls.

The [fixed sphere-chain follow-up](2026-09-23/R1PRO_COLLISION_CHAINS_20260923.md)
passes authored enclosure but retains 77/49/42 overlapping mesh pairs for
K=2/4/8; none is adopted for planning. Native collision and execution remain
unqualified. After this and the model-default update, full suites pass:
1,489 public tests, 818 private tests and one existing private skip.

Phase 0's private audit passed 641 checks. All 25 exported PNGs have the same
decoded pixels as native captures, and the six API image payloads match retained
inputs. Missing native simulation time, original GLM local publication time and
immutable endpoint weight revision remain explicit gaps, not reconstructed facts.

The authoritative Phase 1 run is `v3-retained-discovery-20260923-r4`. It exercises
the real parser, async worker, coordinator, inventory, delta projection and compact
context using retained callbacks. A declared fixture ordering clock and injected
delivery schedule substitute for unavailable live timing. All 67 crops match
original integer ROIs. Discovery does not write authoritative identity, geometry
or task truth. Earlier development runs are not final qualification evidence.

Three demonstrated runtime defects were fixed with 20 public regression tests:
future/foreign identity projection, one-pixel ROI roundoff, and compact-context
omission metadata exceeding its byte budget. Phase 1 validation: 1,471 public tests,
Ruff, five synthetic CLIs; private snapshot 581 passed/one existing skip; 194
embodied tests on the synchronized Linux host. No motion gates were relaxed.

Phase 2 protocol `phase2-association-protocol-20260923-r2` freezes 14 scenarios
and 670 files; 4,329 preparation checks pass. These are artifact/protocol checks,
**not association success results**. Scenarios include wrong labels/regions,
similar candidates, stale seeds, reset-ID reuse, camera/session mismatch, partial
hand occlusion and artificial scene switches. The 131-frame native sequence
contains actual partial hand occlusion at action 924 and clearer visibility at
956; repeated sequence IDs are preserved as distinct captures. Scripted pumpkin
images can test abstention but cannot qualify natural full disappearance or
physical reidentification. Evaluator labels and scripted identities are excluded
from model inputs; no independent physical association proof is established.

Follow-up CPU replay `phase2-association-contracts-20260923-r2` now exercises
10/14 cases: 987 checks (mostly provenance), 36 archive visits, 30 positive-mask
visits, zero identity bindings. Four scripted scenarios lack suitable mask or
association evidence and remain unexecuted. This is not a recognition accuracy
score. Existing candidates have no metric center, so their binding failures do
not test invalidation of previously valid geometry on loss. A separate strengthened
synthetic loss regression verifies valid-before/blocked-after binding and journal
reload, not native perception. A matched lineage
control accepts metadata for the recorded session and rejects a session-only
change, without establishing physical identity. See the
[Phase 2 report](2026-09-23/ASSOCIATION_CONTRACT_REPLAY_20260923.md).

Three more demonstrated gaps are fixed: proposed tracking session now reaches
the evidence-aware callback; discovery checks source/consumer robot, domain and
availability before writes; scoped region camera must match its source image.
Ten added public regressions pass. Latest validation is 1,481 public tests, Ruff,
five CLIs, 204 Linux embodied tests and 604 private tests with one existing skip.
Phase 1 r5 repeats all 64 successful checks against these fixes.

After local Hugging Face login, the approved SAM checkpoint was restored and its
hash verified. The fresh 25-frame run completed without retries: box-seeded radio
13/13 positive-mask frames, reset case 5/5, partial hand occlusion 4/4, negative
view 0/3. All 1,589 learned parameters exactly equal the checkpoint. Qualitative
mask review supports target alignment but finds some gripper-edge contamination;
these counts are not accuracy or physical identity scores. Warm SAM-only steps
were roughly 121-139 ms, excluding simulation/depth fusion/artifact publication.
Full private tests now pass 629 with one existing skip; the public runtime remains
the verified 1,481-test snapshot. See the
[fresh SAM report](2026-09-23/FRESH_SAM_ASSOCIATION_DIAGNOSTIC_20260923.md).

The current host has pinned SAM source, weights and all 59 recorded dependency
versions. Policy/simulator environments remain absent. Natural full loss,
similar-object crossing and live publication timing remain unqualified; none of
the scripted gaps is promoted to native success. The paid count ceiling is exhausted at 4,127.
Do not issue more paid requests or reuse consumed exploratory motion permission.

Detailed Phase 0/1 sources, hashes and reproduction command are in the
[retained replay report](2026-09-23/V3_RETAINED_REPLAY_20260923.md). The sections
below provide the historical context needed to interpret the remaining work.

## 2. How To Interpret Status

**Software-verified** means tests/fixtures passed, not that a robot capability works.
**Retained replay** uses saved evidence; it does not establish live timing.
**Native shadow** observes a real simulator rollout but does not control it.
**Exploratory motion** used explicitly bounded simulator-only permission with
clearance recorded as unknown; it is not strict motion qualification.
**Not qualified** can coexist with many completed diagnostic runs.

The source of truth for numerical results is the dated report and its private
receipts, not an old conversational stage number. Reports use different action
budgets, observation schedules and model recipes. Do not pool them as one benchmark.
An operational `passed` receipt can mean collection completed while its stop,
identity, geometry, or task-success field failed.

## 3. Original Eight-Stage Plan

| Original stage | What actually completed | What remains |
| --- | --- | --- |
| 1. Live semantic cycle | Bounded native observations, GPT executive/verifier, ledger and causal-boundary checks | A robust task-solving integrated loop; V3 is not yet a qualified live replacement |
| 2. Prospective shadow routing | Four scripted traces, 32 shadow boundaries; 12 model route declarations before selected-tier answers on three traces | Prospective routing during diverse autonomous episodes |
| 3. Multi-trace memory ablation | M0/M1/M2 answer comparisons on three scripted traces; 12 corrected executive-choice calls over two traces | Executing those decisions and measuring task benefit |
| 4. Policy bake-off | Multiple compatible checkpoints, native screens and targeted follow-ups | Reliable broad motor competence; no clear task-success winner |
| 5. Radio pilot | Bounded integration and matched GPT-supervised Corvid/Behavior-Skill pair | Native radio success, matched supervision-benefit controls, full memory-enabled pilot |
| 6. Hard Halloween pilot | Not conducted as a full harness episode; short atomic probes are not this stage | Useful motor/execution capability and a frozen evaluation protocol |
| 7. Robustness replication | Some component/reset/negative tests only | End-to-end seeds, placements, distractors, stale memory and forced-failure study |
| 8. Final system comparison | Not conducted | Policy-only vs supervised vs routed-memory systems with matched budgets and replication |

Stages 6-8 are deferred, not proved impossible or dependent only on waiting for
new weights. Classical execution is an active alternative, but still needs native
qualification. The current ordered queue in section 10 supersedes treating these
eight stages as an immediately executable linear checklist.

## 4. Semantic Cycle And Memory

Completed evidence:

- A stationary native fireplace diagnostic completed a three-call semantic loop
  with zero motion after a separate rerun fixed an invalid `finish` argument.
  The first failure was retained. This was not radio-task completion.
- Five short moving GPT/harness pilots executed 16, 96, 16, 16 and 16 actions.
  Verifiers remained uncertain and termination was unresolved. At 30 Hz these
  span only 0.53-3.2 simulated seconds, not task success-rate evaluations.
- Legal images, events and posed RGB-D keyframes entered shadow memory. Earlier
  cutoffs excluded later verifier events; memory did not change live motor inputs.
- Four controlled scripted multi-object/multi-place traces provided eight
  boundaries each, including failed pickup, displacement, occlusion/non-detection,
  recovery, place transition and revisit. These are protocol tests, not autonomous
  or zero-shot benchmark episodes. Three received full M0/M1/M2 answer ablations;
  the fourth was retained structurally without another paid full matrix.
- On three traces, four M0-only routing declarations preceded four selected-tier
  answers. Each selected M2/M1/M2/M0; all 12 answers completed. Shared questions
  and manual review limit independence and statistical conclusions.
- Corrected executive-choice tests used M0=current context, M1=plus event/text
  history, M2=plus historical pixels. Across two traces, M0 requested missing
  history; M1/M2 used a dated place-B search lead; only M2 selected the supported
  opposite left/right scan directions after opposite displacements. All 12 calls
  completed and citations resolved. These were proposed actions, not executed ones.

Important invalidation: an early consequential-memory comparison exposed a future
place-B identity limitation in current metadata. Its comparative scores are invalid.
Phase-gated metadata repair preserved source RGB/events and evaluator labels;
corrected traces passed cutoff/future-fact audits. Never reuse the invalid run as
evidence of memory benefit.

Not done: memory-sensitive autonomous task benefit, restart-safe depth-backed 3D
reconstruction, or a full posed-keyframe memory system comparison. Historical
experiments often use M2 to mean historical pixels, not a qualified geometric map.
Posed keyframes retain RGB durably but native depth references need a durable
resolver or archival copy before restart-safe reconstruction can be claimed.

Source: [early experiment report](2026-09-21/EXPERIMENT_PROGRESS_20260921.md).
Private details: `docs/MULTI_TRACE_MEMORY_RESULTS.md` and
`docs/CONSEQUENTIAL_MEMORY_DECISION_RESULT.md` in the private lab.

## 5. Policy Trials And GPT Supervision

The robot is BEHAVIOR's R1Pro with a native finite 23-dimensional action interface.
Compatibility requires the checkpoint's camera, proprioception, normalization,
action codec and temporal execution recipe, not merely accepting a language string.
Training overlap is disclosed: these trials are not held-out motor generalization.

| Checkpoint family | Evidence and outcome |
| --- | --- |
| Official radio pi0.5 / GR00T | Earlier bounded auditions; did not establish reliable task success or a general motor |
| RLinf PT50 / Comet PT50 | Short probes insufficient for full-task evaluation; Comet weights matched the tested RLinf artifact, not an independent checkpoint |
| Ryan all100 step5000 / StarVLA all-task | Auditioned; no qualified reliable motor. Ryan step10000 was reviewed, not locally executed |
| G0.5 | Recorded-input/interface work; complete native action interface not qualified |
| Kmy GR00T N1.7 multitask | Working native interface; radio/trash screens had no success; navigation and late tilted trash views observed |
| Corvid pi0.5 all-task foundation backbone | Working native interface; carried/repositioned a bin in one trash run, wrong-appliance interactions in others; no task success |
| Behavior-Skill pi05-pt50-skill | Working reference; approaches/reaches/contacts radio but displaces or rotates it without activation; not a reliable general policy |

Pins for the main recent candidates:

| Model repository / selection | Checkpoint revision |
| --- | --- |
| `mafangniu/Behavior-Skill-VLA-Checkpoints`, `pi05-pt50-skill` | `98941096c94b0f978391d8a0accc699c32ec8b2a` |
| `0Corvid0/pi05-b1k-families`, `backbone_foundation_100ep` | `b627f22777d9babc6d4b06d7f088266dc484dd8c` |
| `kmy17518/gr00t-n1.7-b1k-multitask`, checkpoint238000 | `5831e9dc0ec1212e9aaa3d96c8e27d2548718a82` |

The BEHAVIOR source pin for these trials is
`b1979916ec1549b10a4e65e630bc6504a9af1b00`. Corvid/Kmy report all-100-task
training; Behavior-Skill reports 50-task skill training. No Corvid family experts
were used. Behavior-Skill can be called without adopting its own high-level planner;
that does not prove arbitrary instructions are in-distribution or followed well.

The common radio/trash screen used seed 0, ordinary starts, no GPT/memory, and a
3,224-action or 1,200-wall-second cap. Every trial ended success=false/Q=0.
Kmy and Corvid reached approximately 1,720-1,908 actions before the wall cap;
Behavior-Skill reached 3,224. Their different replanning recipes invalidate a
simple equal-horizon performance ranking from that screen.

Corvid's longer trash follow-ups reached 6,000 actions/200 simulated seconds at
two starts, still success=false/Q=0. A separate two-order instruction crossover
switched radio/refrigerator requests after 20 seconds; no convincing redirection
was observed. Those tests had no GPT and do not prove universal language blindness.

The later **matched GPT radio pair** completed without wall censoring:

| Frozen policy + GPT | Actions / simulated time | Policy calls | Executive + verifier calls | Wall time | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| Corvid | 3,224 / 107.47 s | 3,224 | 9 + 9 | 2,372.55 s | false / Q0 |
| Behavior-Skill | 3,224 / 107.47 s | 101 | 9 + 9 | 583.55 s | false / Q0 |

Same start/seed, GPT-6 Astra medium Flex, prompts, schemas, current-image/proprio
rules and 384-action decision intervals; distinct upstream policy recipes retained.
No historical memory, retries or provider fallback. All 18 verifier outcomes were
power-uncertain. Corvid chose approach seven times/press twice; Behavior-Skill chose
approach twice/press seven times. Neither won on task success. Total 36-call cost
was $0.72168375, not a general API pricing estimate. Exact initial proprioception,
prompt fields, finite action traces and fresh verifier evidence were audited.

Still missing: matched current-wrapper no-GPT controls and replication for any
supervision-benefit claim. Poorly visible radio-power cues, fine contact control,
instruction conditioning and absent failure-history context are plausible separate
limitations; no experiment has isolated one as the sole cause.

Source and exact upstream recipes: [policy and supervised results](2026-09-21/EXPERIMENT_PROGRESS_20260921.md).

## 6. Geometry, Stopping And Hybrid Motion

| Completed experiment | Supported result | Not established |
| --- | --- | --- |
| Native hold-codec/stationary tests | Codec equivalence; short stationary settling and sustained native radio hold | General moving localization or full-body clearance |
| Empty-scene calibration | Collected failed baseline/cross-axis behavior | A valid general base calibration; native radio results do not erase this failure |
| Native response pulses | Bounded forward response/braking reproduced; reverse/yaw checks failed | Arbitrary base motion or strict navigation |
| Motion-measurement diagnosis | Per-tick odometry/instantaneous feedback problems identified; fixed-reference depth checks improved bounded evidence | Independent drift truth or qualified full robot stopping |
| Tiny A-short/B-short | 384 policy actions per condition; no obvious immediate disruption, no task success | Target-directed staging or causal task benefit |
| Compiler replay | 78 legal RGB-D views; zero qualified contact candidates; 78 INSPECT contract probes remained blocked | Native compiler execution, valid button/grasp semantics |
| Depth/robot coverage audits | Upper-body depth support improves with views; low space remains unseen; old planning spheres fail full enclosure | Continuous swept clearance, known-free low corridors |
| Post-policy feedback diagnostics | Native position/velocity disagreement persisted even with 240 physics-substep samples | Root cause resolved or native whole-robot stop qualified |
| Joint position-window shadow | 0/379 moving-policy windows and 55/55 hold windows accepted in a fresh trace | Independent accuracy, base stopping, or permission to replace strict stop gates |
| Authorized target-directed probe | 8 cm commanded, 6.67 cm estimated path, 1.11 cm lateral deviation; experimental stops passed | Strict clearance; authorization for additional or longer probes |
| Matched target-directed A/B | Each completed 1,152 policy + 92 classical actions; fresh-reset handoff resumed approach without obvious retreat | Causal intervention benefit or task success |

The matched target-directed pair's acquisition trajectories differed before the
intervention, despite equal seed and initial proprioception. B started its handoff
about 15.6 cm farther from the observed target surface. Initial RGB differed while
depth/proprioception matched; retained-input policy replay reproduced within process
with small cross-host differences. This does not isolate the render divergence's
cause. A/B's final visible-surface distances of 0.693/0.650 m are not proof B helped.
Future comparisons need repeated balanced-order starts and handoff-state reporting.

Radio geometry work found no obvious optical-Z depth convention mismatch. Masks
included deep background through handle openings/edges. SAM 2.1 Large recovered
parts but did not eliminate that contamination. Whole-radio masks failed tight
planar contact tests (0/12 accepted on later online masks). Depth-connected patches
separate observed surfaces without asserting the removed pieces are background.
Retained adjacent body patches had approximately 4-7 mm p95 neighbor distances;
this is internal consistency, not millimeter absolute accuracy or button geometry.

Dense observations improved depth-fit/step checks: 32/32 short-step pairs passed,
versus 0/4 sparse pairs in the same window. Uncached live pose estimates were all
computed but only 14/33 fresh within two seconds. Exact-input cloud-preparation
caching achieved 33/33 fresh, maximum age 1.428 s, without changing fit gates.
Independent drift and a qualified base transform remain missing.

Crucially, the subsequent live mask/depth/pose consumer returned **five timely but
empty target joins**. SAM acquired the radio after the fixed pose window. Later
positive retained replays do not retroactively qualify positive live fusion.

Readiness audits: GraspGenX needs the actual simulated hand assets, calibrated
grasp-to-TCP transform, closure geometry, fingerprints and qualified review inputs.
The cuRobo port needs R1Pro/tool config, a current collision world, independent
FK/collision checks and measured execution/stop tests. Neither has demonstrated
native arm staging, press, grasp or pick/place completion through this harness.

Sources: [qualification history and 15 gates](qualification_queue.md),
[compiler replay](2026-09-22/ACTION_COMPILER_REPLAY_20260922.md),
[matched handoff](2026-09-22/MATCHED_TARGET_HANDOFF_20260922.md),
[coverage](2026-09-22/EXTENDED_VIEW_CLEARANCE_20260922.md),
[joint stop](2026-09-22/JOINT_STOP_SHADOW_20260922.md),
[pose timing](2026-09-22/LIVE_POSE_SHADOW_20260922.md),
[fusion](2026-09-22/LIVE_SURFACE_FUSION_20260922.md), and
[gripper audit](2026-09-22/GRASPGENX_READINESS_20260922.md).

## 7. Perception And Discovery Comparisons

These mostly use correlated retained 720x720 views from one room, not held-out
multi-room recognition benchmarks. Good boxes do not prove correct identity;
strict JSON does not prove correct boxes. Early SAM-reference IoUs measure model
agreement; later approximate manual boxes are still not pixel-perfect ground truth.

### Segmentation, Tracking And Latency

- SAM 2.1 Large was tested on 18 boxes: approximately 48 ms warm radio inference
  and 2.5 GiB end-of-run GPU use. Live co-residency/moving shadow completed, but
  masks and observation cadence still needed work. GrabCut was removed from the
  live worker; it is not the current segmentation baseline.
- SAM 3 and then SAM 3.1 were tested locally. Official-path/preprocessing audits
  reproduced acquisition failures; image/video admission thresholds differ.
  Exact adapter masks/IDs matched upstream video on the audited pairs.
- An early incremental adapter had an off-by-one source-frame bug. Its drifting
  mask/freshness results are invalidated. The corrected live shadow completed
  768 policy actions, 25 captures, zero queue drops, and 50/50 current-frame reads.
  Warm tracking median was 252 ms; observation-to-result median/p95 483/540 ms.
  These are sparse 32-action boundaries, not continuous high-rate video.
- Source-preserving PNG delivery and optional level-1 lossless compression reduced
  capture costs. A single-4090 three-prompt test peaked at 23,482 MiB versus its
  23,552 MiB cutoff: fit was tight, not comfortable spare capacity. No controlled
  one-versus-two-GPU end-to-end speedup study exists.
- CPU cloud/normal preparation, not only SAM, caused pose backlog. Caching improved
  the bounded live pose trial as described above. No measured 300 ms full
  capture-to-qualified-geometry pipeline or Meta-cloud latency comparison exists.
- Acquisition wording matters: the 117-case audit admitted `red radio` and
  `a red radio` on all ten positive views and rejected wrong colors, while
  `a portable radio` missed all ten. BPE bytes/truncation and FP32 text checks
  did not explain away the sensitivity. This is not a full numerical model audit.
- Acquire-once/track replays improved early retention. Fixed-category controls
  passed two resets and easy scene switches; another forced reset lost a visible
  target that uninterrupted tracking retained. A 131-frame replay survived four
  capacity resets and partial hand occlusion. These do not qualify complete
  disappearance, identical-instance crossings or semantic reidentification.
- A six-case full-description verifier accepted three matching descriptions and
  rejected wrong colors/non-radio control. Crop verification is not live identity.
- VLX-box -> SAM replay maintained one visually supported track on overlapping
  4- and 13-frame sequences, with zero future reads and approximately 159 ms
  subsequent steps. Source pixels and box conversion were checked. This excludes
  simulator capture, depth fusion, artifact writing and co-residency costs.

### VLM / Grounding Screens

| Candidate / experiment | Result and limitation |
| --- | --- |
| GPT-6 Astra, initial blind discovery | 3/3 structurally valid packets, two radio labels and one uncertain/unknown; 6.35-7.49 s. Not a broad baseline ranking |
| Qwen3.8 27B | Two usable packets, category error and one unusable answer; 23.53-57.60 s |
| Qwen3-VL Thinking / Instruct | Thinking first call violated the output ceiling; Instruct 0/3 usable packets. User stopped Qwen; no further testing planned |
| MiMo v2.6 Flash, low / disabled reasoning | Useful boxes and valid packets in the bounded test, inconsistent category/attribute semantics; not qualified identity |
| Muse Glimmer | Useful descriptions but copied placeholder labels and loose boxes; 9.91-11.39 s |
| Moondream3 preview | Native target boxes worked, but red radio also matched `blue radio` 3/3; JSON inventory failed. Warm encode+detection roughly 0.72-0.75 s; standalone memory about 18.7 GiB |
| DeepSeek V4.1 Flash | One low-effort call exhausted 2,048 tokens on reasoning after 45.3 s; no answer. A transport/output-budget result, not visual incapability |
| VLX-Seek-1.5-10B target selection | Located 5/5 visible targets, abstained on absent view; about 2 s including proposals. Omitted requested uncertainty/descriptions; some wrong-category distractor matches |
| VLX blind inventory | 25/39 category/view checklist coverage, radio called speaker in three full views; 6.03 s median including proposal cost |
| GLM 5.3 Flash blind inventory | 37/39 checklist coverage with ordinary synonyms (30/39 under narrower aliases), radio named in 3/3 full views; 4.53 s median; 6/6 strict packets |
| LocateAnything-3B | Fast phrase grounding, not useful blind category inventory. Radio tight in two full views, table-sized false localization in the third; about 0.34 s median native radio query, including no-matches |

There was **no GLM medium-effort comparison** in this discovery series; low was
requested from the first run onward. Earlier pseudo-JSON placeholders were copied
by several models and confound intrinsic model comparisons.

GLM's 18-call, six-view strict-schema sweep compared general, goal-directed and
direct detection prompts. All packets were structurally valid; normalized-coordinate
boxes often mixed units or missed the target. Median latencies were 6.50/8.98/3.07 s.
An explicit-pixel follow-up stopped after two answers and an HTTP 429; remaining
requests were not silently retried. A later **separate six-view blind inventory**
test used explicit pixels and yielded radio-box IoUs 0.804/0.742/0.853 on three full
views. That improves evidence for usable localization, but does not finish the
original pixel-B sweep or isolate coordinate wording as the causal fix.

The matched GLM/VLX inventory used the same six views and 12-object request.
Coverage is category-presence checklist coverage, not instance recall/mAP or a
false-positive-penalized score. GLM still mislabeled grippers; VLX confused radio
with camera and artwork with television in distractor queries. Neither may write
authoritative identities or authorize movement directly.

LocateAnything used its pinned official model, clean loading-key checks and SDPA
after a failed default attention backend. Its 22 requests included four negative
queries with no matches, but one sample per query does not qualify rejection.
GLM-description -> LocateAnything grounding has **not** been tested. The model's
non-commercial research license is not a general deployment permission.

Sources: [initial comparison](2026-09-22/VLM_DISCOVERY_SMOKE_20260922.md),
[reasoning modes](2026-09-22/VLM_DISCOVERY_MODES_20260922.md),
[Muse/Moondream](2026-09-22/MUSE_MOONDREAM_SMOKE_20260922.md),
[DeepSeek](2026-09-22/DEEPSEEK41_DISCOVERY_SMOKE_20260922.md),
[GLM sweep](2026-09-23/GLM_PROMPT_VIEW_SWEEP_20260923.md),
[pixel/VLX](2026-09-23/GLM_PIXEL_VLX_GOAL_20260923.md),
[matched inventory](2026-09-23/GLM_VLX_MATCHED_INVENTORY_20260923.md),
[VLX/SAM handoff](2026-09-23/VLX_BLIND_SAM_HANDOFF_20260923.md),
[LocateAnything](2026-09-23/LOCATEANYTHING_SMOKE_20260923.md), and
[latency](2026-09-22/PERCEPTION_LATENCY_PATH_20260922.md).
Additional SAM diagnostics are linked chronologically in the
[qualification history](qualification_queue.md).

## 8. What The Current Code Has Actually Verified

The successive memory, hybrid, action compiler, Situated V2 and Embodied V3 overlays
are integrated software, not separate claims of robot competence. Canonical domains
are `core`, `perception`, `world`, `planning`, `execution`, `reasoning`, `integrations`.
Experiments live outside runtime ownership. Historical milestone import paths are
retired; use the migration inventory rather than reapplying old installers.

| Verification | Latest established result |
| --- | --- |
| V3 before consolidation | 174 new V3 tests; 1,408 full-checkout tests; 22 separate installer tests |
| Initial consolidation | 1,418 repository tests on Mac/Linux; Ruff; isolated wheel imports, packaged config and synthetic demo |
| Ownership follow-up | 1,451 repository tests on Mac/Linux, including 33 boundary tests; Ruff; five local synthetic CLIs |
| Private lab after import migration | 563 passed, one existing skip |
| Corrected Phase 1 follow-up | 1,471 public tests, Ruff, five synthetic CLIs; 194 embodied Linux tests; private snapshot 581 passed, one existing skip |
| Phase 2 boundary follow-up | 1,481 public tests, Ruff, five synthetic CLIs; 204 embodied Linux tests; private 604 passed, one existing skip; Phase 1 replay still passes |
| Relocated coordinator behavior | Five definitions AST-identical to originals |
| Repository hygiene | Ownership/local-link checker and whitespace checks passed |

Counts are snapshots, not additive experiment counts. The isolated wheel check
belongs to the initial consolidation; it was not rerun for the ownership follow-up.
No software check above made paid calls or native robot actions.

Core now has no upward domain imports. AST checks cover ordinary/relative,
function-local, TYPE_CHECKING and supported literal dynamic imports, reject retired
namespaces, and prevent runtime imports through research/tooling backdoors. Twelve
exact non-core symbol-level bridges remain frozen debt: the entire repository is
not a strict DAG. Computed dynamic imports are not a security-sandbox guarantee.

WorldState, IdentityLedger, SemanticInventory and episodic MemoryStore remain
separate authorities/views. No new session framework or EntityView abstraction was
added. Existing root convenience exports, receipt formats, action gates and budget
guards remain. The corrected private SAM worker was preserved through V3 integration.

V3's discovery regions use normalized 0..1 xyxy, whereas the successful GLM inventory
test returned native pixel boxes. Conversion must use recorded source dimensions
and retain exact frame/camera/session lineage. The integration did not test the new
delta prompt, live GLM publication, full V3 runtime wiring, cuRobo execution or
capability promotion. Mock adapters and synthetic CLIs are not those experiments.

Sources: [V3 integration](../reference/EMBODIED_RUNTIME_V3_INTEGRATION.md),
[50-item delivery/gating inventory](../reference/EMBODIED_RUNTIME_V3_COVERAGE.md),
[consolidation](../architecture/consolidation.md), and
[current architecture](../architecture/overview.md).

## 9. Explicitly Unfinished Hybrid Stages

The detailed 15-stage roadmap is not fifteen experiments that must all run now.
Its present state, by experiment name rather than ambiguous historical numbering:

| Hybrid stages | Current state |
| --- | --- |
| 1. Software integration | Complete |
| 2. Retained geometry/catalog replay | Completed, with zero qualified contact actions |
| 3. Online acquisition | Several native shadow trials completed; identity/metric/multi-view qualification incomplete |
| 4. Strict target-directed transit | Not qualified; only bounded unknown-clearance exploratory motion completed |
| 5. Target-directed short A/B | Exploratory pair completed; strict and causally interpretable comparison still missing |
| 6. Equal-total-action A/B radio | Not conducted under qualified hybrid protocol |
| 7. Arm/torso free-space staging/return | Not qualified or completed as the intended experiment |
| 8. C-short then A/B/C | Not conducted |
| 9. Positive compiler candidate/execution test | Contract/replay work only; native positive execution not done |
| 10. Classical contact/press | Not done under qualified grounded-contact protocol |
| 11. Other-task hybrid screen | Not done; earlier policy-only trash screens are different experiments |
| 12. GPT selects useful compiled actions | Software/fixture support, not native competence demonstration |
| 13. Event-driven compiled-action recovery | Not demonstrated as a native task experiment |
| 14. Current state vs causal memory in execution | Retained decision ablations only; online task benefit not done |
| 15. Neural duty-cycle optimization | Deferred; no energy-efficiency claim |

## 10. Next Experiments And Pass Evidence

1. **Strict V3 retained replay: completed within fixture-clock scope.** Preserve
   frozen r4 evidence and its 64 passing checks. Do not repeat this as if unstarted
   or treat it as a live timing/model-quality result. Delayed identity-claim
   publication remains unqualified; observation-time guards cannot reconstruct it.
2. **Discovery-to-SAM association/loss test.** Restore only the required local GPU
   environment. Include mismatched semantics, similar objects, full disappearance,
   reset, reappearance and source/session mismatches, not another easy continuous
   radio track. Require current-source provenance, safe rejection/abstention and no
   identity transfer merely because a tracker reused a number. Start with replay.
3. **Bounded paid prompt/context study, separately authorized.** Compare V3 delta
   versus inventory prompts on held-out views; compare compact versus rich GPT
   context on frozen causal boundaries. Predeclare accuracy/abstention, box/schema
   validity, identity errors, tokens, cost and end-to-end latency. Do not assume the
   older inventory accuracy applies to the untested delta prompt.
4. **Native geometry, localization, clearance and stop qualification.** Reestablish
   fresh sensor/pose/feedback bindings and positive target-bearing fusion. Resolve
   low-body unknown coverage and conservative swept geometry. Exercise moving and
   stopped cases plus failures. Keep strict gates; old exploratory authorization
   is not open-ended. A timing pass alone is not an accuracy pass.
5. **Small useful execution and matched handoff.** Once relevant gates pass, test
   a measured free-space endpoint/stop before contact; qualify robot/collision/TCP
   assets for any planner. Use one frozen motor, balanced starts/order, equal
   declared action budgets and independent verification. Report rejected/censored
   runs and acquisition distributions. Then consider equal-total-action A/B/C.
6. **Task-level GPT and memory benefit.** Use visibly verifiable tasks with useful
   motor competence; compare current-context supervision, event memory and routed
   visual memory. Keep one execution backend fixed across conditions. Separate
   executive decision-time evidence from fresh post-action verifier evidence.
7. **Broaden only after a complete useful run.** Seeds, placements, distractors,
   forced failures, then held-out tasks and the final system comparison. No claim
   of zero-shot target-task motor learning when the checkpoint trained on that task.

CPU retained replay, protocol review and artifact audits can proceed independently.
Do not share a mutable simulator across motion trials or overload a nearly full
24 GiB GPU and then interpret contention as model latency. Parallelize isolated
workloads only while preserving frozen sources, budgets and resource accounting.

## 11. Reproduction, Artifacts And Operational Boundaries

Public repo contains code, synthetic fixtures, tests and aggregate reports. The
private sibling workspace is `internal/physical-ai-lab`, with `scripts`, `tests`,
`docs`, `runs`, `backups`, dependency lockfiles and provisioning records. Native
RGB-D/video, checkpoints, licensed simulator assets, credentials and billing
journals are not committed. A Git clone alone cannot reproduce every native result.

Private result directories worth locating before resuming:

| Evidence family | Retained location / record |
| --- | --- |
| Early memory and policy work | Lab docs named in sections 4/5, especially `RESEARCH_PROGRESS_HANDOFF_20260921.md`; they link exact runs and pins |
| Compiler replay | `runs/compiler_replay_20260922/` |
| Target-directed exploratory pair | `runs/matched-target-handoff-20260922-r1/` |
| Positive retained pose source | `runs/sam31-live-pose-cache-20260922-r1/` |
| Timely empty live fusion source | `runs/sam31-live-fusion-20260922-r1/` |
| Blind GLM inventory | `runs/glm-blind-inventory-20260923-r1/` and `runs/glm-vlx-inventory-comparison-20260923-r1/` |
| Box-seeded SAM | `runs/sam-box-handoff-20260923-r1/` |
| LocateAnything success / failed startup | `runs/locateanything-inventory-20260923-r2/` / `r1/` |
| Ownership validation / final pre-commit rerun | `runs/ownership-validation-20260923-r2/` / `runs/ownership-handoff-validation-20260923-r1/` |
| Phase 0 source/accounting audit | `runs/phase0-evidence-20260923-r1/` |
| Authoritative Phase 1 replay / software validation | `runs/v3-retained-discovery-20260923-r4/` / `runs/phase1-fixed-validation-20260923-r1/` |
| Phase 2 protocol only, not execution | `runs/phase2-association-protocol-20260923-r2/`; r1 preserved as superseded draft |
| Phase 2 CPU contract replay, not inference | `runs/phase2-association-contracts-20260923-r2/`; r1 retained with superseded explanatory wording |
| SAM runtime and official checkpoint restored | `runs/sam31-runtime-restore-20260923-r2/`; r1 preserves the earlier missing-weight state |
| Fresh SAM inference / qualitative mask review | `runs/phase2-fresh-sam-20260923-r1/` / `runs/phase2-fresh-sam-analysis-20260923-r1/` |

The latest host was bootstrapped with code, CPU environment and selected
checksum-verified evidence, not all GPU weights, simulator assets or policy runtimes.
See private `docs/HOST_BOOTSTRAP_20260923.md` for connection/provisioning details.
Mac/Linux follow-up tests passed after source synchronization. The later SAM
runtime/weight restoration is described above; the simulator is still absent.
Some full historical every-action sensor traces are not local; do not
assume any old stopped disk is disposable based on Git or summary reports alone.

From the public repo root in the existing parent workspace, software-only checks:

```sh
../internal/physical-ai-lab/.venv/bin/python tools/validate.py --output /tmp/harness-validation-fresh
../internal/physical-ai-lab/.venv/bin/python tools/check_repository.py
git diff --check
```

Use a fresh output directory. For a standalone clone, install the repo's declared
development dependencies first and use that environment's Python. Private tests
also require the lab source/scripts and are not included in the public test count.

Before new paid work, inspect the actual guarded campaign ledger. The last explicit
count authorization in this series was 4,127 calls under a $75 cumulative ceiling,
with unresolved reservations retained, including HTTP 429 and token-contract
failures. This document grants no further calls or retries and is not a live balance
report. Do not clear holds or substitute providers to make an experiment run.
The normal API transport remains the deployment path; subscription-backed minimal
Codex transport is development-only and not assumed behaviorally equivalent.

Before motion, preserve online-only evidence and explicit authority boundaries:
no privileged object poses, hidden task truth, simulator segmentation, future frames,
pre-mapped target locations or direct simulator state mutation as control inputs.
Out-of-band evaluator scores remain unavailable to the controller. Scripted memory
fixtures must stay labeled scripted. Preserve rejected trials and uncertainty.
Honor checkpoint/source/data licenses; an experimental license confirmation is not
permission to redistribute assets or deploy commercially.

The architecture is sufficient for the next tests. New abstractions, lower
thresholds, favorable prompt-only views and more model auditions are not substitutes
for demonstrating useful, causally valid, independently verified task execution.
