# Rich executive context — v0.9 experiment profile

## Purpose

The v0.8 harness proved bounded context and causal historical memory. Its default
context projection is intentionally conservative: 4 current images, 5 recent
state events, and 12 KB of metadata. That is useful as a safety/regression
profile, but it is probably too restrictive for a GPT-class multimodal executive.

For the next experiment, the harness should **organize information without
making a strong relevance decision on GPT's behalf**.

v0.9 therefore adds an opt-in `RichContextBuilder`. It does not replace the
existing `ContextProjector`.

## Context model

The builder exposes five kinds of information:

1. **Core task state**
   - full task ledger
   - current images
   - current navigation/executor summary

2. **Detailed focus state**
   - all current predicates for the objects/containers explicitly involved in
     the current action

3. **Broad entity roster**
   - compact current state for many known entities, not just the current target
   - identity candidates and inferred/not-observed fields remain visible
   - this lets GPT notice that a ball was subsequently moved elsewhere instead
     of sending the robot back to an obsolete room

4. **Short histories and semantic events**
   - several recent state transitions for focus entities
   - up to ~24 semantic runtime events
   - failure/recovery history is intentionally retained

5. **Spatial context**
   - current place
   - semantic topology (places, doors, gateway state)
   - optional observation-coverage notes

Historical episodic memory remains source-backed and separate. `BroadMemorySelector`
unions focus-entity history, current-place history, goal-query hits, and recent
history. It does not use a weaker LLM to decide which single memory GPT may see.
For offline M1/M2 replay, `attach_rich_memory` adds the resulting packet without
pruning M0 and enforces the combined metadata and image guards below. It does
not wire historical memory into the live executive path.

## Experiment defaults

The opt-in profile is deliberately more generous:

```text
current images                8
state events                 20
semantic runtime events      24
known-entity roster          96
detailed entity histories    16 entities, up to 4 changes per predicate
metadata bound               64 KB

historical cards             24
historical images             6
historical image pixels       3 MP total
historical metadata          28 KB

combined metadata            96 KB
combined images              14
```

These numbers are **engineering guards, not token budgets**. Before a paid GPT
call, the provider adapter must still compute actual text/vision usage and reject
a request that exceeds the episode budget.

Do not optimize these numbers down before the first measured GPT experiment.
Log actual context size, image count, latency, token usage and cost, then tune
empirically.

## Identity and object permanence

For visually similar objects, do not force an identity. A roster entry may say:

```yaml
id: ball_2
label: tennis ball
visibility: not_observed
identity_candidates: [ball_2, ball_4]
location:
  place: living_room
  support: coffee_table
inferred_fields: [visibility]
last_update: 104.2
```

GPT should see ambiguity rather than a fabricated stable ID.

A new `CoverageNote` is intentionally advisory:

```yaml
scope_id: coffee_table_surface
observed_at: 110.4
coverage: high
result: not_seen
evidence_ids: [frame_110]
note: ball_2 was not detected during a broad rescan
```

This is **negative evidence about a region**, not proof of the object's new
location. Do not write `ball_2 -> hallway` merely because it disappeared from
the table.

## Maps and place memory

Keep three representations:

- metric occupancy/localization for normal navigation;
- semantic topology for room/door reasoning;
- historical place images/descriptions in episodic memory.

The topology presented to GPT should be simple:

```text
living_room --door_04(open)--> hallway --door_07(unknown)--> kitchen
```

A place card can separately carry a representative wide image and a short
description such as “narrow corridor; blue sofa on left.” Do not turn a VLM
place caption into metric geometry.

## Crops

Object crops remain useful for appearance/re-identification and are already
supported by `make_crop`. Always retain the parent wide image. A crop can answer
“which orange candle is this?” but usually cannot answer “is the candle inside
the cabinet?”

For BEHAVIOR v0, prioritize:
- source image;
- object crop;
- parent/wide scene;
- state/history.

Keep video clips out of normal context. Use a short storyboard only when the
question genuinely depends on motion.

## Recommended next experiment

Use `RichContextBuilder` only for the GPT executive experiment. Keep episodic
memory in shadow mode during the first live run.

Then run the offline memory ablation with the saved causal cutoffs:

- M0: rich current context only;
- M1: M0 + historical event/text cards;
- M2: M1 + source images/crops.

Do not add M3 motion video unless M2 fails on a question that demonstrably
requires temporal motion evidence.

## Cost policy

The expensive operations should remain sparse:

- GPT executive: semantic event boundaries only;
- GPT verifier: ambiguous/consequential semantic outcomes only;
- diary writer: Qwen/local or deterministic templates, asynchronous;
- object tracking, mapping, retrieval, crops: local/deterministic when possible.

The harness is responsible for organizing and grounding evidence. GPT remains
responsible for the difficult semantic choice.
