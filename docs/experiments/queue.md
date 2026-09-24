# Current Experiment Queue

Updated 2026-09-24. Consolidation adds no capability and authorizes no new spend
or motion. The detailed [earlier qualification queue](qualification_queue.md)
and dated reports remain evidence; this page is the current entry point.
For a standalone account of completed trials, caveats and unperformed stages, read
the [experiment handoff](EXPERIMENT_HANDOFF_20260923.md).

## Current Decisions

This summary supersedes earlier next-step wording below; dated receipts remain
immutable evidence, including failed and subsequently invalidated attempts.

| Phase | Current scope and remaining work |
| --- | --- |
| 0-1 | Software and retained replay passed within their declared offline scope |
| 2 | Partial: 10/14 scenarios; genuine crossing, full loss/reappearance and motion gaps |
| 3 | Partial: live prospective inventory coverage incomplete; new paid calls need budget |
| 4 | Not completed; paid comparison needs budget |
| 5 | Partial: refreshed forward/reverse localization and shadow stop evidence; uncertainty/clearance unresolved |
| 6-7 | Live SAM exploratory transit completed (6.04 cm); strict base transit and arm staging/return unqualified |
| 8 | Exploratory comparisons only; no qualified causal benefit |
| 9 | One retained offline grasp candidate, no executed grasp/lift |
| 10-14 | No qualifying end-to-end studies completed |

1. Freeze the frame-704 grasp batch. [Dense-target path screening](2026-09-24/GRASP_CLOSURE_SUPPORT.md)
   leaves candidate 0 only. Candidate 1 overlaps at its open endpoint; candidate
   2 overlaps nine points at path fraction 0.9375. Do not revive coarse-depth passes.
2. Return the execution critical path to staging/sensing/stopping. The surviving
   target exceeds fixed-torso reach; current views cannot qualify whole-body motion.
   [Coverage/reach evidence](2026-09-24/GRASP_COVERAGE_STAGING.md) remains a blocker.
3. Keep the [reverse-stop result](2026-09-24/REVERSE_STOP_PROTOCOL.md) as directional
   validation only. Do not latch earlier raw passes across later failures or
   replace runtime authority with uncalibrated shadow output.
4. The user approved bounded exploratory task trials alongside strict qualification.
   Such trials do not complete strict phases. The first resumed attempt completed
   768 policy actions but zero classical actions: see
   [the preserved launch failures](2026-09-24/EXPLORATORY_TASK_RESTART.md).
   Connect current source-bound SAM geometry before another transit rollout;
   the legacy detection-only owner cannot supply the required metric masks.
   The [live SAM probe](2026-09-24/SAM_LIVE_TRANSIT.md) now completes acquisition,
   6.04 cm measured approach and experimental final stop, with 119 bound captures.
   Strict clearance remains unknown; no manipulation or task success. Continue
   toward useful reachable staging, not another identical short probe.
5. Do not repeat easy association tests, the blind observer sweep, identical
   calibration pulses, or more grasp batches. Phase 2 needs genuinely new causal
   hard-case evidence; paid stages need an explicit budget extension.

## Evidence History

Earlier follow-up: [Phase 0/1 retained V3 replay](2026-09-23/V3_RETAINED_REPLAY_20260923.md)
passes its declared offline integration scope after fixing future identity
projection, pixel-ROI roundoff and compact omission budgeting. GPU/live timing
preflight remains separate; hard association/loss replay is next.
The [Phase 2 CPU contract replay](2026-09-23/ASSOCIATION_CONTRACT_REPLAY_20260923.md)
exercises 10/14 frozen scenarios with 987 checks and zero identity bindings.
The [N11 displacement audit](2026-09-24/PHASE2_N11_DISPLACEMENT_AUDIT_20260924.md)
adds native image-space motion evidence, but its source observations have no
camera pose, so it does not close the continuous-motion scenario. This is not
physical association qualification; four cases still lack suitable evidence.
Three source/session/consumer validation gaps were fixed. The
[fresh SAM diagnostic](2026-09-23/FRESH_SAM_ASSOCIATION_DIAGNOSTIC_20260923.md)
now completes 25 steps after restoring the approved checkpoint: box tracking,
two resets and partial occlusion retain candidates; three negative frames stay
empty. All 1,589 learned parameters match the checkpoint. This does not establish
physical reidentification; natural full loss and crossings remain gaps.
The [scripted loss diagnostic](2026-09-23/SCRIPTED_SAM_LOSS_20260923.md) adds
seven fresh frames: two pumpkin candidates, two empty off-target views, then
local ID 0 reappearing across changed views. This does not establish physical
identity continuity or close the natural-loss gap. No actions or paid calls.
The [native sensor restoration](2026-09-23/NATIVE_SENSOR_RESTORATION_20260923.md)
also passed on the new 4090: three RGB-D cameras, 61-D proprioception, 23-D
action interface at 30 Hz, zero commanded actions. This is sensor readiness,
not localization, identity or motion qualification.
The [paused recapture diagnostic](2026-09-23/PAUSED_RECAPTURE_20260923.md)
restores numeric pins and passes three zero-action native captures. Identical
paused head depth registers consistently; public odometry rejects equal sim time.
Neither result qualifies moving localization. Private suite: 648 plus one skip.

The [base-yaw acquisition diagnostic](2026-09-24/PHASE5_BASE_YAW_ACQUISITION_20260924.md)
confirmed the audited `[vx, vy, wz]` action mapping and a successful measured
stop acknowledgement, but rejected command tracking and found no radio in the
initial or final head view. It does not advance Phase 2 or qualify Phase 5.
Do not rerun SAM on this trace; the next native run must deliberately establish
a target-bearing online acquisition view with legal pose/provenance evidence.

The later [interpolated sensing sweep](2026-09-24/SCAN_SERVO_RESPONSE_20260924.md)
completed its declared `r2` protocol: 20 preflight holds, 482 outbound actions,
and 60 reserved holds. All 562 actions completed, all reserved holds were
raw-settled, and fixed-stride depth analysis found improved low-body visual
support at the endpoint. This remains exploratory evidence with
`motion_qualified=false`, `stop_qualified=false`, and external clearance
unknown. The return-path and historical-coverage analyses show that existing
views do not support arm-return qualification; do not repeat the sweep solely
for more coverage samples.

The [expanded return-observer survey](2026-09-24/OBSERVER_SURVEY_512_20260924.md)
shows that the earlier 128-sample search was too narrow: candidate 384 has
6,545 unblocked sampled points. It still sees zero samples on proximal
left-arm links 1--4 and has no endpoint collision, reach-path, scene-occlusion,
or native-depth qualification. Candidate 384 merits offline validation, not a
native observer move.

The [candidate endpoint collision check](2026-09-24/OBSERVER_CANDIDATE_COLLISION_20260924.md)
found candidate 384 within joint limits with zero authored-hull collisions over
11,003 checked pairs and a 23.33 mm minimum FCL distance. This makes it a valid
offline follow-up candidate, not a motion authorization. Reach/path, optical
geometry, scene occlusion, and native stopping remain open.

The [candidate 384 sampled path](2026-09-24/OBSERVER384_PATH.md) has zero
authored-hull intersections at 65 postures, but requires a 2.966-rad maximum
joint excursion and still lacks proximal-corridor visibility. This is not
continuous clearance. Establish useful proximal coverage before spending more
on this candidate's motion qualification; do not execute it on this evidence.
The corrected [all-candidate observer survey](2026-09-24/OBSERVER_SURVEY_ALL_512_20260924.md)
evaluated all 513 candidates rather than only the earlier top-three shortlist.
Candidate 384 remains best in total visibility (6,545 samples), while candidate
366 is the strongest proximal follow-up (1,462 samples, 1,239/2,459 proximal
samples). Neither covers the return corridor or supplies scene-depth,
continuous-clearance, pose-uncertainty, or stopping authority. Candidate 366's
65-posture offline path audit is recorded in
[its receipt](2026-09-24/OBSERVER366_PATH_RECEIPT.json); do not execute either
candidate on this evidence.
The [temporal observer analysis](2026-09-24/OBSERVER_TEMPORAL_COVERAGE.md)
now rules out the sampled set as complete return support: even all 513 poses
combined can see at most 2/88 sampled link-1 points. Stop individual-pose
qualification for this corridor; a different camera configuration or return
trajectory is needed. This is a sampled-model limitation, not physical
impossibility and not permission for exploratory motion.
The [GraspGen-X torso reach screen](2026-09-24/GRASP_TORSO_REACH_SCREEN.md)
has a corrected count of 1/8 within the radius, not 2/8; candidate 6 has a
positive excess. The subsequent 8/8 IK claim and both path-collision follow-ups
are **invalidated as grasp feasibility evidence**: the IK runner omitted the
source-camera-to-base transform and compared a TCP goal to gripper-link FK.
Those path tests describe unrelated endpoints, not the intended grasp poses.
See [the frame correction](2026-09-24/GRASP_FRAME_CORRECTION.md).
Keep all proposals shadow-only. No grasp, external-clearance, or execution gate
has passed on these invalidated results.
The separate [frame-704 proposal trial](2026-09-24/GRASP_VIEW704.md) now uses
a closer retained online view and new GraspGen-X proposals. Frame-corrected IK
and independent FK recomputation find 8/8 numerical pose matches on this new
set. No collision/contact/scene/path qualification transfers from the invalid
old runs. Next screen these source-bound endpoints before planning or motion;
the large torso changes particularly require review. Phase 9 remains partial.
The [cuRobo R1Pro FK check](2026-09-23/CUROBO_R1PRO_FK_20260923.md) now passes
37 numerical configurations on the pinned GPU backend. Tool offsets and native
schema mismatch are resolved for this diagnostic; collision/planning/execution
remain unqualified. Latest private suite: 687 passed, one skip.
The [authored collision-envelope audit](2026-09-23/R1PRO_COLLISION_ENVELOPE_20260923.md)
encloses all 164 meshes but finds 128 proxy overlaps with disjoint authored mesh
AABBs. This candidate is not adopted for planning; exclusions are unchanged.
Native cooking remains unqualified. Latest private suite: 730 passed, one skip.
The [fixed sphere-chain comparison](2026-09-23/R1PRO_COLLISION_CHAINS_20260923.md)
reduces proxy-overlapping mesh pairs to 77/49/42 for K=2/4/8, but none is adopted.
The [model-default update](2026-09-23/GPT6_SOL_LUNA_MIGRATION_20260923.md) uses Sol
Flex for new GPT runs. Luna was subsequently retired from active options by user
decision; retain its historical results. A matched Sol/Astra comparison remains
planned under a separate future call approval. No budget extensions were made.
Migration-time public/private suites:1,489 / 818 plus one skip.
The [stationary native SAM join](2026-09-23/STATIONARY_SAM_JOIN_20260923.md)
first failed before inference on a private NumPy scalar conversion. After the
adapter correction, a separately recorded zero-action attempt passes: one mask,
29,710 depth samples, 1.3032-second publication age. This does not qualify moving
or multi-view fusion. Latest private suite: 867 passed, one existing skip.

## Completed Software And Retained-Data Work

- [Sol/Luna inventory comparison](2026-09-23/SOL_LUNA_INVENTORY_20260923.md):
  approved 12 calls complete, $0.02703. Sol 6/6 valid, Luna 4/6; GLM retained
  as inventory candidate. Call ceiling 4,139 now reached; prior holds unchanged.
- The V3 overlay passed 1,408 actual-checkout tests before consolidation.
- [GLM/VLX inventory](2026-09-23/GLM_VLX_MATCHED_INVENTORY_20260923.md): small
  matched scene coverage comparison; not instance recall or general model ranking.
- [VLX-to-SAM tracking](2026-09-23/VLX_BLIND_SAM_HANDOFF_20260923.md): bounded
  causal handoff, with known semantic confusions and untested full occlusion.
- [LocateAnything](2026-09-23/LOCATEANYTHING_SMOKE_20260923.md): description grounding
  evaluated; not a replacement for category inventory.

## Decision History

The notes below record decisions at their respective times. The Current Decisions
section above takes precedence where later evidence changes admission or priority.

Latest grasp correction: [dense-target closure support](2026-09-24/GRASP_CLOSURE_SUPPORT.md)
rejects candidate 1, whose open finger overlaps two full-resolution target points
missed by stride-four scene sampling. The endpoint screen now always includes
the complete retained target cloud. Candidates 0/2 retain no endpoint intrusions
and have observed support on both fingers during a static closure sweep; no
physical contact/lift or dense-target path qualification follows.

The reverse-stop attribution reconstructs all 25 flags: braking 11-18 passed;
19/20 failed wrist raw velocity; 24/25 failed wrist and planar raw velocity.
Do not latch an earlier stop pass across later failures or repeat an identical
pulse. A user clarification is pending on adding bounded exploratory task trials
alongside strict qualification; no new task-motion scope is assumed meanwhile.

Phase 5 [reverse-direction holdout](2026-09-24/REVERSE_STOP_PROTOCOL.md) completed
25 native actions and 26 paired captures. Refreshed legal RGB-D/FK max observed
translation error is 6.59 micrometres; all 5 moving and 15 braking intervals have
the expected 2 mm/s classification. Combined replay yields 11 stop candidates,
but raw stop acknowledgement stays false. This is directional evidence, not a
calibrated uncertainty guarantee, clearance certificate or phase completion.

Critical-path update: [candidate-2 coverage and reach](2026-09-24/GRASP_COVERAGE_STAGING.md)
show 44,033/116,020 exposed vertex samples outside all current views. Torso motion
carries the idle right arm into unseen space. Locking the torso cannot reach any
of the three surviving targets (0.327-0.354 m beyond the optimistic arm bound).
Retain these proposals and return to Phase 5-7 stopping/sensing/closer staging.
Do not spend another grasp batch or tighten path sampling before resolving this.

Latest Phase 9 [geometric feasibility screen](2026-09-24/GRASP_OBB_FEASIBILITY.md):
candidates 0/1/2 retain target support with no tested endpoint or 17-posture path
hits. Candidate 3 is rejected on-path; 4-7 at endpoints. Candidate 2 minimizes
maximum joint excursion among survivors. Next combine continuous self-separation
and coverage assessment; do not spend another grasp batch. No execution authority.

New Phase 9 candidate set: [reference geometric branch](2026-09-24/GRASP_REFERENCE_BRANCH.md)
produces 272 proposals; 176 have retained inner-box support and all eight highest
scores have support. Same hand/cloud, no fitted translation. Check numerical
reachability then endpoint feasibility; no motion authority or phase completion.

Latest Phase 9 result: [frame-704 endpoint/convention audit](2026-09-24/GRASP_ENDPOINTS704.md)
admits none of the eight proposals. All have zero retained inner-box support;
nearest target points miss the box by 28-41 mm despite consistent algebraic
transforms. Resolve the hand annotation/reference convention before another
proposal batch. No path or motion authorization; Phase 9 stays partial.

Infrastructure prerequisite: [automatic GPU driver update](2026-09-23/GPU_DRIVER_UPDATE_20260923.md)
was resolved by an approved reboot after package completion and verified backups.
CUDA smoke checks pass in all three environments. The new
[single-arm FK check](2026-09-23/CUROBO_SINGLE_ARM_FK_20260923.md) passes 870
upper-body comparisons with measured holds. Collision/planning remain open.
The [authored convex audit](2026-09-23/R1PRO_AUTHORED_CONVEX_20260923.md)
finds no intersections in 11,259 eligible mesh pairs, but finger/camera gaps are
only 0.46-0.51 mm. Native cooking/margins and swept-path checks remain required;
no geometry candidate is promoted to motion authority.
The [native collision-settings inspection](2026-09-23/R1PRO_NATIVE_COLLISION_SETTINGS_20260923.md)
now verifies 14 symmetric runtime filters, including both narrow finger/camera
pairs, and 164 enabled collider approximations. Follow-up r4 measures effective
contact offsets of 1.36-5.04 mm and zero rest offsets; no PhysxCollisionAPI instances
exist for the source's 1 mm assignment to update. All 25 legacy-only exclusions
are accounted for by disabled connected-joint collision flags. Cooked geometry,
changed postures and swept paths remain unqualified. No exclusions or motion
gates changed; all attempts are backed up locally. Private suite: 901 plus one skip.
The [native convex comparison](2026-09-23/R1PRO_NATIVE_CONVEX_20260923.md) now
returns all 161 hulls: only 2 match bidirectionally, but all returned hulls are
contained by the authored hulls to numerical precision. Keep those conservative
hulls for changed-posture/swept-path diagnostics; do not shrink them to force
equivalence. Three wheel spheres and active-shape correspondence remain open.
Private suite: 907 passed, one skip; no paid calls or commanded actions.
The [frozen joint-path audit](2026-09-23/R1PRO_JOINT_PATHS_20260923.md) passes
28 paths using explicit separating-axis/arc-displacement lower bounds, with
minimum 20.91 mm against an 11.07 mm diagnostic threshold. An initial FCL-distance
certificate was rejected after an endpoint contradiction; all attempts remain.
This is non-wheel self-separation only, not external clearance or execution.
Latest private suite: 917 passed, one skip. Next address external sensor coverage,
wheel/active-shape scope and native control/stop qualification.
The [retained arm depth audit](2026-09-23/ARM_DEPTH_SUPPORT_20260923.md) finds
96.44% of selected vertex samples outside all camera views; no strict external
clearance claim is available. The user-approved [one wrist probe](2026-09-23/WRIST_PROBE_20260923.md)
passed actuator/initial-stop checks and tracked +0.008 rad, but failed sustained
stop verification. It ended after 35 actions, with no return or automatic retry.
Next diagnose joint-velocity/substep behavior; do not loosen thresholds or
repeat motion under the consumed one-attempt scope. Private suite: 931 plus one skip.
The [offline velocity analysis](2026-09-23/WRIST_VELOCITY_ANALYSIS_20260923.md)
confirms position/raw-velocity disagreement at 30 Hz but cannot exclude substep
oscillation. A separately approved, physics-step stationary-hold diagnostic is
next; no threshold changes or new motion were made by the offline analysis.
The separately approved [30-action hold diagnostic](2026-09-23/WRIST_HOLD_SUBSTEP_20260923.md)
is now complete: 120 physics samples confirm raw-versus-position-derived wrist
velocity disagreement, but final stop acknowledgement still fails. No thresholds
changed. Moving/braking estimator validation and base stopping remain open.

1. Consolidation and ownership checks complete: 1,451 repository tests on
   Mac/Linux, Ruff, five fixture CLIs and source-link checks; private suite
   563 passed, one existing skip. The initial 1,418-test consolidation also
   passed an isolated wheel check; that check was not rerun after the ownership
   follow-up. No model calls.

**Next phase-level capture requirements.** There are now two distinct queues:

- For Phase 2, do not rerun the retained `run_phase2_fresh_sam.py` queue or
  another easy continuous track. A future native hard-case trace must contain,
  at every selected boundary, source-bound RGB/depth, a legal contemporaneous
  camera pose, and provenance sufficient to distinguish camera motion from
  object motion. It should target full disappearance/reappearance and genuine
  similar-object ambiguity/crossing if the simulator scene permits.
- For Phase 5/7, do not repeat the completed sensing sweep. A new motion run
  requires a changed authority source: calibrated pose uncertainty plus
  external clearance/stop evidence, or a specifically justified observer-camera
  strategy. Existing final-view and historical coverage are insufficient for
  arm return.

Without the respective evidence, another GPU rollout would produce another
descriptive or exploratory result rather than advance a phase.
2. Retained replay complete in its declared fixture-clock scope: six saved GLM
   inventories, 67 sightings, 64 checks, no new calls/motion. Corrected public
   suite: 1,471 tests; private snapshot: 581 passed, one skip. The new GLM delta
   prompt and native availability timestamps are not qualified by this replay.
3. Restore only the GPU environments needed for the next bounded SAM handoff.
   Test source binding, distractors, loss and reacquisition before motion.
   Qualify delayed identity-claim availability explicitly; observation-time guards
   do not reconstruct publication-time history. Restore the approved SAM weights
   or authenticated download access before fresh GPU inference. This restoration
   and the first 25-step inference diagnostic are now complete; do not repeat them
   as if unstarted. Basic simulator/sensor restoration now passes; frozen-policy
   restoration remains pending; numeric pins are now restored. Latest
   public suite: 1,481 tests; Linux embodied subset: 204; private: 730 plus one skip.
   The strengthened synthetic loss test checks previously valid geometry and journal
   reload. Native loss remains unqualified: retained no-center candidates do not
   exercise that transition.
4. With a separately approved call budget, compare delta versus inventory prompts
   on held-out views and compact versus rich executive context on frozen boundaries.
5. Resume native localization/clearance/stopping qualification. Preserve strict
   gates and labeled exploratory exceptions; neither maps nor memory completes them.
6. Only after those gates, run matched frozen-policy/planner comparisons with the
   same action budgets and independent verifier. Promote macros only after review.
7. Evaluate memory on a genuinely memory-sensitive task after useful motor
   competence; then broaden seeds, layouts and held-out tasks.

Perception naming is not the only bottleneck. Reliable manipulation and native
qualification remain unresolved; more architectural code is not evidence of
progress on them. Budget holds and existing authorization ceilings remain intact.
