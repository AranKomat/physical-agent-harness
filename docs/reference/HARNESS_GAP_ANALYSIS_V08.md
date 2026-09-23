# Physical Agent Harness gap analysis — v0.8
## Reviewed repository
`AranKomat/physical-agent-harness` at `adfcc9161d5bef4c2079cd5e48b73c0cc0055d93`
(2026-09-19).

## Bottom line

The repository contains most of the **offline architectural skeleton** that we
previously designed. It does **not** yet contain the full live physical-agent
system. The memory v0.7 merge completed only the first work package: contracts,
storage, retrieval, tests and docs. It did not connect episodic memory to native
observations, runtime events or executive decisions.

Treat three levels separately:

1. **Implemented contracts/offline logic** — largely present.
2. **Native service wiring** — partially present.
3. **Qualified closed-loop behavior** — mostly still outstanding.

## Status matrix

| Layer | Current repository | What is still required |
|---|---|---|
| Legal observation boundary | Implemented `BehaviorAdapter`; strict schema | Native BEHAVIOR sensor/artifact process, explicit simulation clock and calibration qualification |
| Localization | Open3D RGB-D odometry implemented | Qualify on native BEHAVIOR sequences; recovery/relocalization beyond the current fail-latched odometry |
| World/entity state | `WorldState`, RTSM adapter, relation memory and action provenance | Launch a real RTSM/perception sidecar; calibrate identity/relations; measure object-permanence errors |
| Task ledger | Implemented and evidence-gated | Populate a real task decomposition from the executive / benchmark goal |
| Historical memory | v0.7 storage/retrieval plus v0.8 logger/event wiring, decision cutoffs, fixture bridge and one recorded-native shadow replay | Run live shadow capture, collect multi-object traces, compare M0/M1/M2, then consider context use |
| Evidence | Immutable content-addressed `EvidenceStore` | Native artifact writer mapping legal refs to the store, including exact capture times |
| Verification | Tier router, evidence validator hooks, GPT-6 role and visual verifier wrapper | Live GPT-6 transport and cost accounting; broader verifier qualification on real held-out frames |
| Semantic boundary | Runtime has fresh `after_observer` and `on_verified` hooks | Wire live perception + verifier + task ledger in one actual autonomous cycle |
| Motor runtime | Multi-chunk, stale-response rejection, deadlines/resource ownership | Qualified R1Pro motor policy/action codec; general policy still unresolved |
| Navigation N2/N1 | Topological + metric prototype, frontiers/gateway events | Native N0 base controller, odometry accuracy, real target resolver/place graph |
| Recovery L3 | Bounded preview/execute contracts | Native IK/trajectory/collision implementation using only legal geometry |
| Executive | Sparse semantic tool loop and context budget | Live GPT-6 model transport, prompt/tool schema, accounting, failure policy |
| Process isolation | Interfaces are service-friendly | Actual supervised IPC/processes, timeouts, restart/watermark semantics |
| Evaluation | Radio integration fixture and native scorer isolation | One end-to-end autonomous semantic loop; then hard-task episodes |
| CI / packaging | pytest/ruff config | Public CI is still advisable; repository intentionally has no license yet |

## What “fully incorporated” means

The earlier physical-agent idea is **architecturally represented** but not
operationally complete. The repository has the key interfaces:

```text
legal observations
  -> localization / perception
  -> current WorldState
  -> TaskLedger
  -> bounded ContextProjector
  -> sparse ExecutiveLoop
  -> navigation / chunked motor / L3 recovery
  -> fresh post-action observation
  -> verifier
  -> event
```

and now:

```text
source evidence + events
  -> historical MemoryStore
  -> retrieval
  -> optional context attachment
```

The missing milestone is to make those arrows use real native services rather
than fixtures.

## Priority order

### P0 — close one real semantic loop
Use the existing radio-trained π0.5 fixture only as a motor integration fixture.

1. Native BEHAVIOR artifact writer -> `BehaviorAdapter`.
2. `RGBDOdometry` or another legal pose estimator on those artifacts.
3. Live perception/world update after each semantic boundary.
4. Live GPT-6 semantic verifier.
5. `on_verified` updates the task ledger.
6. A real executive turn consumes the resulting event.

This establishes the harness, not motor generalization.

### P0 — memory in shadow mode

The retained radio trace now passes the bounded version of this gate: six
native images, two cards, trusted entity/place bindings, two finalized cutoffs,
and no future-card leakage. The private pilot is wired for an opt-in live run.
The remaining P0 work is to exercise that path during the next native episode.
Run concurrently with the same loop:

1. Every accepted legal RGB frame becomes a historical `Asset`.
2. Semantic-boundary events become deterministic cards.
3. Bind existing RTSM entity IDs and navigation place IDs.
4. Save the exact memory cutoff for every executive decision.
5. Build retrieval packets but **do not attach them to the executive yet**.
6. Score retrieval on replay.

### P1 — make memory useful
After shadow-mode checks:

1. Add entity crops from the tracker (source-linked, not freshened).
2. Add place/landmark views on `ARRIVED` / `place_entered`.
3. Add failure storyboards from ordered source frames.
4. Add one bounded background narrator (cheap VLM is acceptable because it has no authority).
5. Compare M0 recent-only vs M1 text vs M2 text+images under equal budgets.
6. Turn on context attachment only if M1/M2 actually improve historical questions without unacceptable false memories.

### P1 — native navigation and L3
Qualify the N0 base controller, place resolver, and bounded IK recovery. These
matter more to a hard multi-room BEHAVIOR task than another storage abstraction.

### P2 — external memory/backend audition
Only if local retrieval is inadequate, compare ReflectWorld on frozen prefixes
and normalize its outputs to the same historical-memory authority/cutoff rules.

### P2 — general motor policy
Resume the G0.5/GR00T/Xiaomi/DM/π0.5 search only after the harness itself can
close semantic loops with the known radio fixture.

## Stop adding abstractions

Do not add another world model, vector database, trained memory agent, or policy
before the P0 loops run. The current codebase is already architecturally rich.
The next useful work is **wiring and measurement**.
