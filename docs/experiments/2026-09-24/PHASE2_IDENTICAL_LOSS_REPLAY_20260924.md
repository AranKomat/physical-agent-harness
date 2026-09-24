# Phase 2 Identical-Object Loss And Reacquisition

## Decision

Phase 2's controlled discovery-to-SAM identity contract gate is complete. The
combined frozen matrix now has evidence for all 14 predeclared scenarios. This
does not qualify natural benchmark behavior, manipulation, motion authority or
task success: the new hard case uses native BEHAVIOR RGB-D with scripted
evaluator-side object-pose interventions and a stationary, script-pinned robot.

The key result is safe abstention, not tracker reidentification accuracy. Two
identical pumpkins had valid current bindings through five visible frames, both
fully disappeared for three frames, and both reappeared on exchanged sides.
SAM 3.1 reused local IDs `0` and `1`; the runtime retained the category
`pumpkin` but refused both executable identity bindings. A quarantined scorer
later found that the reused IDs happened to follow the same physical simulator
instances. That evaluator-only coincidence did not change the runtime result.

## Protocol

- Task fixture: `putting_away_Halloween_decorations`, native instance 302,
  fixture mode `loss-reappearance`.
- Inputs allowed to runtime: source-bound head RGB-D, observation-bound camera
  intrinsics, causal capture/simulator times, SAM masks and mask-local IDs.
- Inputs denied to runtime: simulator object names, object poses, scripted
  identity mapping and evaluator outcome labels.
- Frozen prompt: `pumpkin`; exactly 13 arrived-frame calls; no retries.
- Local model: SAM 3.1 multiplex checkpoint SHA-256
  `0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`,
  source revision `2345a4ad109ac29c569da749c91d84f10dc08c40`, clean at audit.
- Runtime association: anonymous entities on frame 0; minimum-cost camera-frame
  metric continuity through frame 4; complete loss on frames 5-7; deliberately
  non-established proofs with explicit alternatives on frames 8-12.
- Budgets: zero robot actions, zero policy actions, zero paid calls, zero retries.
- Evaluator scoring ran only after the runtime journal was closed. Its output was
  never available to the identity replay.

## Capture Integrity

Early attempts exposed stale RTX/Fabric camera buffers after scripted teleports.
These were raw simulator render failures, not world-model output. The collector
was hardened to warm the renderer, compare consecutive captures and reject a
frame unless final-read RGB mean absolute error was at most `5/255`.

| Attempt | Retained outcome |
| --- | --- |
| Crossing fixture r1-r6 | Preserved setup, viewpoint and robot-drift failures |
| Crossing fixture r7 | 13/13 clean frames, 78 verified RGB-D references, zero robot drift |
| Loss fixture r1 | Rejected after manual review found a stale first frame |
| Loss fixture r2 | New render gate rejected the unstable first frame automatically |
| Loss fixture r3 | 13/13 clean frames, 78 verified references, final-read MAE 0.13-0.46/255 |
| Runtime replay local r1 | Failed before evidence access because standalone public-package discovery was missing |
| Runtime replay local r2 | Complete; package discovery fixed in the CLI, no contract relaxation |
| Runtime replay remote r1 | Complete and byte-identical to local r2 |

## Results

- Frames 0-4: SAM emitted both candidates. The largest per-frame matched
  camera-centroid step was 5.85 cm. The smallest margin over the alternative
  assignment was 86.89 cm. Both current bindings were available.
- Frames 5-7: SAM emitted no masks or IDs. `IdentityLedger.mark_not_observed`
  invalidated both bindings while preserving remembered category semantics.
- Frames 8-12: SAM emitted IDs `[0, 1]` again. Because both identical objects
  disappeared together, proofs used `unique=False`, `temporal_support=None`,
  current geometry support only, and the other entity as an explicit alternative.
  Both bindings remained unavailable on every frame.
- Reopening the durable `Journal` reproduced exactly the same final states and
  binding denials.
- The evaluator sidecar confirms both objects were behind the robot during all
  three hidden frames and that their fixed-camera lateral ordering exchanged
  across the hidden interval.
- The evaluator-only rank scorer maps local ID 0 to `fixture-a` and local ID 1
  to `fixture-b` both before and after loss. This 2/2 coincidence is not runtime
  evidence and does not retroactively establish physical identity.
- SAM timing: 479 ms initial acquisition; 147 ms median warm frame; 149 ms warm
  p95 on this 13-frame trace.

## Association Matrix

| Frozen scenario | Result |
| --- | --- |
| S01 positive continuous tracking | Pass: source-bound current geometry and unique continuity established |
| S02 wrong label, correct region | Pass from prior frozen replay: no identity promotion |
| S03 correct label, wrong region | Pass from prior frozen replay: proposal alone rejected |
| S04 two similar/identical objects | Pass: two simultaneous identical pumpkin entities |
| S05 complete disappearance | Pass: no masks for three native RGB-D captures; bindings invalidated |
| S06 reappearance after disappearance | Pass: category retained, association ambiguous, bindings blocked |
| S07 tracker reset | Pass from prior frozen replay: generation scope enforced |
| S08 local ID reuse | Pass: actual IDs reused after simultaneous loss without identity authority |
| S09 camera/session mismatch | Pass from prior frozen replay: rejected |
| S10 stale box | Pass from prior frozen replay: rejected on changed capture |
| S11 object motion relative to background | Pass in controlled fixture: stationary camera/robot, source-bound object displacement |
| S12 hand/gripper occlusion | Pass from prior retained native replay |
| S13 negative/no-target sequence | Pass from prior replay and current empty-loss frames |
| S14 artificial scene switch | Pass from prior replay: regressed ordering rejected |

S11 is a controlled cross-frame intervention, not a natural physics trajectory.
Natural task-rollout replication remains useful robustness evidence, but is not
required to keep validating the already-demonstrated fail-closed contract.

## Receipts

Private retained runs:

- `phase2-crossing-loss-fixture-20260924-r3`
- `phase2-crossing-loss-sam31-20260924-r1`
- `phase2-crossing-loss-identity-replay-20260924-r2` (local)
- `phase2-crossing-loss-identity-replay-20260924-r1` (remote reproduction)
- `phase2-crossing-loss-identity-score-20260924-r2` (local)
- `phase2-crossing-loss-identity-score-20260924-r1` (remote reproduction)

| Artifact | SHA-256 |
| --- | --- |
| Fixture receipt | `8bc969b4c21188d915d05da6179f12bbf5021ca255743e17d8b9b75958a9456b` |
| Quarantined evaluator sidecar | `ac9af0058331396e3549ff80b794604d04e6d9f332999b6b894e67130f2f714d` |
| SAM report | `0bf9119c98889a2c43719e4c0856a67d940ddce41b2968d40ce8f086e7f9060a` |
| Runtime identity report, local and remote | `c85fb2ae932d1adc4c345515cd93a82e13f9c2639b9d73952b56e3247c78fd6e` |
| Evaluator score, local and remote | `d66f49453179eb0db8d59b09db6ad2c778e69b44573116e76114e8c5f06aaca7` |

## Interpretation

Directly established: current anonymous instances can acquire source-bound
metric bindings; real mask loss removes executable geometry; simultaneous loss
of identical objects makes reacquisition ambiguous; tracker-local IDs do not
restore identity; durable replay preserves the blocked state.

Not established: benchmark success, natural occlusion robustness, semantic
discovery recall, globally calibrated object pose, manipulation safety, or any
right to use the quarantined evaluator mapping during execution.

The next phase-level work is Phase 3 prospective live shadow discovery, followed
by Phase 4 frozen-boundary context comparisons under a separately authorized
paid-call budget. Phase 2 should not receive more easy tracker demonstrations.
