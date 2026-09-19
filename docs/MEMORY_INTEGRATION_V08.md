# Physical Agent Harness integration handoff — v0.8
## What to do after merging the v0.7 multimodal-memory package

**Reviewed repository:** `AranKomat/physical-agent-harness` at
`adfcc9161d5bef4c2079cd5e48b73c0cc0055d93`.

## Answer to the immediate question

Merging the v0.7 ZIP was **not the full implementation of the memory idea**. It
was intentionally an additive, authority-safe substrate: schemas, store, media
handling, optional background writer, retrieval, tests and documentation.

That corresponds to work package **A — merge and validate** in the v0.7 handoff.

The actual research/engineering work begins with work package **B — shadow
capture**. Until observations and runtime events feed the sidecar, the memory
package is effectively a well-tested library sitting unused in the repository.

This update supplies the missing glue for that next step without enabling memory
to influence robot actions by default.

## Files in this v0.8 overlay

```text
physical_harness/memory/integration.py
tests/memory/test_integration.py
examples/memory_shadow_integration.py
docs/HARNESS_GAP_ANALYSIS_V08.md
docs/MEMORY_INTEGRATION_V08.md
```

It also requires the tiny accompanying patch to
`physical_harness/memory/selection.py` so every existing `RuntimeEvent` value is
recordable (`verifier_uncertain`, `precondition_violated`, `plan_exhausted`,
`path_blocked` were missing from the v0.7 boundary allow-list).

## 1. Concrete native wiring

### 1.1 Observation drain

Use the existing `BehaviorAdapter.logger` to feed **already accepted legal
observations** to `MemorySidecar.ingest_observation`.

The native sensor process should already have written RGB bytes through
`EvidenceStore.put`. If the legal envelope contains opaque native references,
provide `resolve_rgb_ref(ref) -> hash-named EvidenceStore filename`.

```python
blobs = EvidenceStore(run_dir / "evidence")
memory = MemoryStore(run_dir / "episodic.sqlite", episode_id, blobs.read)
decisions = DecisionCutoffLog(run_dir / "memory-decisions.sqlite", episode_id)
sidecar = MemorySidecar(
    episode_id=episode_id,
    store=memory,
    decisions=decisions,
    resolve_rgb_ref=native_ref_to_evidence_filename,
)

behavior = BehaviorAdapter(
    source,
    episode_id=episode_id,
    action_bounds=...,
    pose_estimator=...,
    logger=sidecar.ingest_observation,
)
```

Do not call a VLM here. This path should only add source-backed image handles to
the bounded recent buffer.

### 1.2 Semantic event drain

Subscribe after creating the runtime event bus:

```python
event_bus.subscribe(lambda event: sidecar.record_event(event))
```

Before `run_skill`, bind trusted IDs already known by the planner/tracker:

```python
sidecar.bind_skill(
    request.skill_id,
    entity_ids=request.target_entities,
    place_ids=(current_place_id,) if current_place_id else (),
)
```

Do not parse a diary sentence to invent entity IDs.

### 1.3 Shadow decision packet

At every executive boundary, build the base context normally. Then generate a
historical packet under a saved causal cutoff:

```python
base = projector.build(...)
shadow_context, memory_decision, packet = sidecar.prepare_decision(
    decision_id=decision_id,
    event_id=event.event_id,
    observed_through=event.sim_time,
    base_context=base,
    query=base["goal"],
    entity_id=current_target_id,
    place_id=current_place_id,
    active=False,                 # IMPORTANT
)
assert shadow_context == base
save(packet)                      # evaluate later
```

The decision log persists both physical observation time and knowledge
watermark. If a background caption finishes one second later while simulator
time is paused, replay of this decision cannot see it.

### 1.4 First shadow-mode run

Use the radio fixture because the native bridge already exists. This run is only
checking:

- every legal image is source/hash/timestamp bound;
- every semantic boundary creates one idempotent historical card;
- event/entity/place associations are correct;
- no memory packet enters the executive;
- no extra paid model call occurs;
- exact cutoffs can be replayed.

The radio trace is insufficient for evaluating useful long-term recall.

### 1.5 Integration result

The retained one-boundary native radio trace was replayed through this path.
It registered six genuine camera artifacts, recorded `decision_required` and
`verifier_uncertain` cards with `radio` / `radio-room` bindings, and finalized
two decision cutoffs. The executive base context remained unchanged. Replaying
the first cutoff reproduced its packet exactly and excluded the later terminal
card. No robot action, model call, or paid API call was made during the replay.

`NativeFixtureBridge` now also accepts an optional memory sidecar and asserts
that shadow preparation did not alter executive context. The private native
pilot has an opt-in memory-shadow path for the next GPU-backed run. This is an
integration result, not evidence that memory improves decision quality.

## 2. Collect the first real memory-evaluation traces

Record 5–10 minute legal episodes containing:

1. the same object seen, occluded, moved, and later revisited;
2. two similar objects whose identities can be confused;
3. at least two places / a doorway or corridor transition;
4. one failed manipulation followed by recovery;
5. one motion where a single endpoint frame is insufficient.

These can be teleoperated/scripted/development traces. They do not need a
general autonomous motor policy.

Keep evaluation-only labels outside the harness.

## 3. Add entity and place memories

The v0.7 package has the primitives; the live tracker must supply the bindings.

### Entity views
When RTSM (or another tracker) has a high-confidence visible entity:

- register the wide source image;
- create a source-preserving crop via `make_crop`;
- keep the parent frame for relational reasoning;
- create an `object_sighting` boundary with that stable entity ID.

Never force identity when the tracker reports candidates/ambiguity.

### Place views
On `ARRIVED` or a topological `place_entered` transition:

- select a wide head-camera frame;
- bind the existing place ID;
- store a `place_view` card;
- optionally keep another view if it points toward an important gateway.

No VLM-generated place name should become a metric coordinate.

### Motion
For a failed/ambiguous manipulation, retain a few ordered source frames or an
existing recorded clip handle. Do not create fake continuous video from sparse
images.

## 4. Optional background narrator

Only after deterministic shadow capture works, connect one approved VLM to
`AsyncAnnotator`.

A small Qwen-class VLM is acceptable because the writer has **zero authority**.
The output is an untrusted search annotation tied to source assets.

Requirements:

- timeout is enforced by the transport/process, not just Python thread code;
- low call budget per episode;
- no retries after ambiguous provider failures;
- writer queue cannot block motor/runtime callbacks;
- no outcome hallucination is promoted into `WorldState`.

Measure unsupported claims explicitly. If narration is not better than
deterministic event templates, disable it.

## 5. Replay experiment before live context use

Build a small held-out memory QA set from recorded episodes.

Run:

- **M0:** current state + recent frames only;
- **M1:** M0 + historical text cards;
- **M2:** M1 + retrieved source images/crops;
- **M3:** M2 + storyboards/clips only for temporal-motion questions.

Ask questions such as:

- Where was object X last observed?
- Which cabinet/place was already inspected?
- What changed after the failed attempt?
- Which of these similar objects matches the earlier sighting?
- What evidence supports that claim?
- Is the requested outcome actually observable?

Score against human/out-of-band labels, not against GPT agreement.

Keep total context budgets equal.

## 6. When to enable memory for the executive

Only after replay shows useful recall without unacceptable wrong-memory rates:

```python
context, decision, packet = sidecar.prepare_decision(
    ...,
    active=True,
    provider_check=provider_budget_preflight,
)
```

Start with event-driven retrieval:

- `TARGET_LOST` -> entity history;
- `PATH_BLOCKED` / `DOOR_BLOCKED` -> place/gateway history;
- repeated failed skill -> recent attempts for the target entity;
- explicit executive inspection -> relevant event/source evidence.

Do not dump all memories into every turn.

## 7. What remains from the original physical-agent plan

Read `docs/HARNESS_GAP_ANALYSIS_V08.md`.

The architecture is largely represented in code, but several live components
remain unqualified:

- actual BEHAVIOR artifact/source process;
- live RTSM/perception relation service;
- GPT-6 executive transport;
- live GPT-6 verifier transport;
- qualified R1Pro motor policy;
- native N0 navigation controller;
- native L3 IK/collision recovery;
- supervised IPC/restart behavior.

The known radio fixture has closed one live semantic boundary and the retained
trace has passed memory shadow replay. The next milestone is a live shadow run
followed by a multi-object/multi-place replay set, not another framework or
model.

## 8. Immediate researcher instruction

> Keep memory in shadow mode and narration disabled. Exercise the opt-in sidecar
> during the next native fixture run and verify its result against the completed
> recorded-native replay. Then collect a small multi-object/multi-place trace set
> and run M0/M1/M2 recall before allowing historical memory to influence actions.
