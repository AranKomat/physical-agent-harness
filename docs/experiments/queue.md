# Current Experiment Queue

Updated 2026-09-23. Consolidation adds no capability and authorizes no new spend
or motion. The detailed [earlier qualification queue](qualification_queue.md)
and dated reports remain evidence; this page is the current entry point.
For a standalone account of completed trials, caveats and unperformed stages, read
the [experiment handoff](EXPERIMENT_HANDOFF_20260923.md).

Latest follow-up: [Phase 0/1 retained V3 replay](2026-09-23/V3_RETAINED_REPLAY_20260923.md)
passes its declared offline integration scope after fixing future identity
projection, pixel-ROI roundoff and compact omission budgeting. GPU/live timing
preflight remains separate; hard association/loss replay is next.
The [Phase 2 CPU contract replay](2026-09-23/ASSOCIATION_CONTRACT_REPLAY_20260923.md)
exercises 10/14 frozen scenarios with 987 checks and zero identity bindings.
This is not physical association qualification; four cases lack suitable evidence.
Three source/session/consumer validation gaps were fixed. The
[fresh SAM diagnostic](2026-09-23/FRESH_SAM_ASSOCIATION_DIAGNOSTIC_20260923.md)
now completes 25 steps after restoring the approved checkpoint: box tracking,
two resets and partial occlusion retain candidates; three negative frames stay
empty. All 1,589 learned parameters match the checkpoint. This does not establish
physical reidentification; natural full loss and crossings remain gaps.
The [native sensor restoration](2026-09-23/NATIVE_SENSOR_RESTORATION_20260923.md)
also passed on the new 4090: three RGB-D cameras, 61-D proprioception, 23-D
action interface at 30 Hz, zero commanded actions. This is sensor readiness,
not localization, identity or motion qualification.
The [paused recapture diagnostic](2026-09-23/PAUSED_RECAPTURE_20260923.md)
restores numeric pins and passes three zero-action native captures. Identical
paused head depth registers consistently; public odometry rejects equal sim time.
Neither result qualifies moving localization. Private suite: 648 plus one skip.

## Completed Software And Retained-Data Work

- The V3 overlay passed 1,408 actual-checkout tests before consolidation.
- [GLM/VLX inventory](2026-09-23/GLM_VLX_MATCHED_INVENTORY_20260923.md): small
  matched scene coverage comparison; not instance recall or general model ranking.
- [VLX-to-SAM tracking](2026-09-23/VLX_BLIND_SAM_HANDOFF_20260923.md): bounded
  causal handoff, with known semantic confusions and untested full occlusion.
- [LocateAnything](2026-09-23/LOCATEANYTHING_SMOKE_20260923.md): description grounding
  evaluated; not a replacement for category inventory.

## Next, In Order

1. Consolidation and ownership checks complete: 1,451 repository tests on
   Mac/Linux, Ruff, five fixture CLIs and source-link checks; private suite
   563 passed, one existing skip. The initial 1,418-test consolidation also
   passed an isolated wheel check; that check was not rerun after the ownership
   follow-up. No model calls.
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
   public suite: 1,481 tests; Linux embodied subset: 204; private: 648 plus one skip.
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
