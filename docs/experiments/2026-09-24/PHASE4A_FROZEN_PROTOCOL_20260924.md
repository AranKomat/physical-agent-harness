# Phase 4A Frozen Prompt-Comparison Protocol

## Status

The protocol is frozen before model output. No Phase 4A calls have been made and
Phase 4 is not complete.

Phase 3's four prospectively selected boundaries from the September 24 moving
trace form the held-out set. They were not used in the September 22-23 prompt
sweeps, and image-novelty selection was committed before semantic output.

```text
source trace:
d48ce0b11e19340325a9380e45f6c8e323f749cfa31625090738a95ba8ce71ab

prospective selection:
8233395222ef96a504c3abe2b41e29e1f48fefa397add736835eb8cdb4b9089a

frozen Phase 4A protocol:
8bb49fb34d3e47352b54ab661b74fc398af32b34324a4478accdb6b66148e735
```

## Held-Out Views

| Source index | Control sequence | Radio visibility | Frozen reference objects |
| ---: | ---: | --- | ---: |
| 0 | 0 | Absent | 4 |
| 8 | 256 | Absent | 6 |
| 10 | 320 | Clipped at left edge | 9 |
| 15 | 480 | Clear | 11 |

The 30 reference entries contain approximate human-reviewed pixel boxes,
visibility state, category aliases and a flag separating room objects from robot
embodiment. They were recorded before model output. They are audit references,
not pixel-perfect segmentation truth and never enter runtime state.

## Cohorts

The comparison is matched by source view and model:

- **Inventory:** existing task-blind inventory prompt, at most 12 objects, native
  720x720 pixel boxes.
- **V3 delta:** task-aware historical semantic delta, at most 4 updates and 2
  attention items, normalized boxes, no current geometry or action authority.

Both use `z-ai/glm-5.3-flash`, low reasoning, 2,048 maximum output tokens and a
strict JSON schema. Provider selection follows the frozen order Together,
Baseten FP8, Fireworks, Parasail FP8, CoreWeave NVFP4. One route is pinned before
each cohort; there is no fallback or retry after dispatch.

The prompts intentionally differ in task hint and output cap. That is the system
profile comparison specified by Phase 4A, not a claim of isolated prompt-token
causality.

## Scoring

Primary measures are:

- strict packet validity;
- radio recall on the clipped and clear positive views;
- radio false positives on both negative views;
- source receipt and box validity;
- supported versus unsupported semantic claims under frozen human review;
- useful attention without stale geometry authority.

Secondary measures are major-category coverage under the frozen alias list,
within-response and cross-view redundancy, accepted inventory growth, tokens,
latency and cost. A same-category box match uses approximate IoU at least 0.20.
No vocabulary aliases may be added after outputs are seen.

## Call Accounting

The V3 and inventory cohorts each require four calls. Authorization for one does
not authorize the other. The pending Phase 3 scope would supply the V3 cohort;
the inventory cohort requires a later independent approval. Neither has been
dispatched under this protocol.

This study does not establish a general perception ranking, persistent identity,
metric geometry, motion authority or task success.
