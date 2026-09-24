# Phase 3 Prospective Shadow Replay

## Scope

This zero-call experiment qualifies prospective discovery scheduling mechanics
over one retained moving BEHAVIOR/R1Pro trace. It does not evaluate semantic
accuracy, establish live-scene coverage, authorize motion, or complete Phase 3.

The frozen source contains 119 legal head RGB captures spanning 322.931 seconds
of recorded monotonic observation time, 768 frozen-policy actions and 92 later
exploratory transit actions. The transit moved the base 6.04 cm under its original
explicitly unknown-clearance scope. Discovery replay sent no robot or policy
actions and did not modify this action stream.

The source did not record native simulator time. The replay therefore uses:

- source `observed_at` deltas as a normalized fixture arrival clock;
- capture index as `fixture-order-v1`, explicitly not simulator time;
- the original content-addressed RGB bytes, calibration and evidence IDs;
- the production `SemanticKeyframes`, `AsyncDiscovery`,
  `DiscoveryCoordinator`, `SemanticInventory`, `ExecutiveCadence` and journal.

Deterministic delayed responses exercise queueing and publication only. They are
fixture data, not semantic-model evidence. The fixture's one attention item says
only to reacquire the current scene; it cannot provide current geometry or an
action.

## Source Integrity

```text
source receipt:
d48ce0b11e19340325a9380e45f6c8e323f749cfa31625090738a95ba8ce71ab

frozen action payload before/after replay:
dac85da2726da3333858f2227d750b057ec09af4d7587a14ac4b21066ffb03ec
```

Every selected image was decoded, dimension-checked against source calibration,
and verified against its content-addressed filename. Two pairs of captures share
control sequence 768 or 860 at command boundaries, but retain distinct increasing
sensor timestamps and image IDs. The loader permits this legitimate equality
while rejecting timestamp or sequence regression.

## Results

| Profile | Frames | Submitted | Invoked | Superseded | Delivered | Buffered non-current selections |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Production defaults, 9.4 s service tail | 119 | 4 | 4 | 0 | 4 | 1 |
| 0.03 novelty / 12 s queue stress | 119 | 13 | 10 | 3 | 10 | 4 |

The production profile selected:

| Source index | Control sequence | Mode | Reason | Images |
| ---: | ---: | --- | --- | ---: |
| 0 | 0 | `room_initial` | `initial_view` | 1 |
| 8 | 256 | `delta` | `image_novelty` | 2 |
| 10 | 320 | `delta` | `image_novelty` | 1 |
| 15 | 480 | `delta` | `image_novelty` | 1 |

At the observed 9.4-second latency tail, all four production jobs started without
queue delay. The lower-threshold stress profile exercised the designed
one-running/one-coalesced-pending behavior: three pending reservations were
explicitly journaled as superseded, ten were invoked, and all ten terminal
results were delivered. No silent retry or cancellation occurred.

The fixture kept one bounded historical inventory sighting and produced one
current-task `relevant_discovery` wake event. Publication remained
`historical_only`; no current geometry, situated identity, compiled action,
native action or policy action was written.

## Reproduction

The Mac and GPU host used the same pinned source receipt. Both detailed scenario
reports are byte-identical:

```text
production:
8233395222ef96a504c3abe2b41e29e1f48fefa397add736835eb8cdb4b9089a

queue stress:
43c8bf657d736ba03ffb3a9c8ffe583cd395bbbd3aee3119b932a0c13175f49b
```

Focused verification after the replay:

```text
private Phase 2/3/discovery tests: 18 passed
public keyframe/discovery/integration tests: 75 passed
targeted Ruff: passed
```

## Decision

The prospective selection, delayed publication, transient buffering and queue
coalescing mechanics gate is complete for this retained trace. This closes the
specific Phase 3 mechanics gap recorded in the prior handoff, but not semantic
usefulness or broad live coverage.

The next paid run is predeclared as exactly the four production-selected
boundaries above, with no retries. It requires separate call/cost authorization.
The real responses must then be scored for useful supported changes, duplicate
behavior, inventory growth, attention quality, latency and context consumption.
Phase 3 remains partial until that evidence passes.
