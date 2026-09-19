# v0.11 spatial-memory overlay: sparse views over permanent reconstruction

Base reviewed commit: `dd09b94fdbbfe0db1207ed6601d39a710a1d6cb8` (`Add executable experiment runner`).

## Decision

Do **not** add another permanent 3D world model before the first BEHAVIOR experiment.
The repository already has the pieces that should own current state:

- `WorldState` for evidence-backed object/task beliefs;
- `TaskLedger` / task bindings for what remains;
- RTSM adapter semantics for persistent objects and relation memory;
- metric occupancy + semantic topology for navigation;
- multimodal historical cards, crops/place views, causal cutoffs and bounded retrieval.

What is missing is a compact representation for **where a useful historical RGB-D view was taken** and whether an area was actually inspected. The existing legal BEHAVIOR boundary already carries RGB/depth references and, when available, a validated camera-to-`local_map` transform. v0.11 records that information instead of immediately fusing every observation into a permanent dense reconstruction.

## New contracts

`physical_harness/memory/spatial_views.py` adds:

- `PosedRGBDKeyframe`: historical RGB asset + depth reference + legal camera pose + provenance + entity/place tags;
- `CoverageObservation`: explicit region-observation coverage and occlusion, including cautious negative evidence;
- `SpatialViewIndex`: deterministic retrieval of a few relevant/diverse keyframes;
- `keyframes_from_legal_envelope`: projects an already validated `LegalObservation` envelope into a sparse posed view.

The key distinction is:

```text
WorldState = what we currently believe
SpatialViewIndex = historical evidence we can inspect/reconstruct from
```

A keyframe never updates an object's current location by itself.

### Why record only the pose camera initially?

`LegalObservation.estimated_pose` currently names one camera and provides one camera-to-local-map transform. v0.11 deliberately records only that camera. It does **not** invent extrinsics for other synchronized cameras. If calibration later supplies rigid transforms for wrist/head cameras, the BEHAVIOR adapter can compose those upstream and create additional posed views.

## Negative evidence

The repo already distinguishes disappearance from a new location claim. v0.11 makes another distinction explicit:

```text
"I have not looked there recently"
            !=
"I rescanned most of that region and did not observe the target"
```

`CoverageObservation.supports_negative_evidence()` requires a named target, an explicit `False` sighting result, enough measured coverage, and bounded occlusion. Even then it supports only:

> target not observed in this region under this observation

It does **not** infer where the target went.

## On-demand 3D scene artifacts

`physical_harness/spatial_scene.py` adds an interface for geometry-heavy moments without turning the whole episode into a dense reconstruction problem.

```text
WorldState + task
       |
       | geometry actually needed
       v
select 2-6 relevant posed RGB-D keyframes
       |
       v
SceneBuilder (future WetRobo/DynaMem/MuJoCo/TAMP adapter)
       |
       v
SceneArtifact
  DISPLAY -> COLLISION -> MOTION authority
```

This borrows one of the strongest WetRobo engineering ideas: a visually plausible reconstruction is not automatically safe for collision or motion planning. The three authority levels are separate. Motion authority additionally requires calibration provenance.

The overlay does **not** implement a scene builder. That is intentional. The next useful implementation should be chosen from real failure evidence:

- a simple point-cloud/local TSDF builder may be enough;
- WetRobo-style SAM-first object completion may help thin/contact tasks;
- DynaMem/RoboStream update ideas may help moved/disappeared objects;
- a heavier SLAM/4D system should wait until experiments show the sparse memory is inadequate.

## Why no Jev/reactive-language layer in this overlay

Jev is attractive in game environments where a compact textual/game-state description is available. A general real-world tactical layer would often need the image itself. Feeding only structured state risks making a fast model act on the exact visual evidence that was discarded.

For v0.11:

- continuous motor behavior stays in the motor policy/controller;
- cheap deterministic/executor-native feedback handles progress/stall/target loss;
- the Executive wakes at the existing semantic/runtime events;
- visual evidence remains available through current images and retrieved keyframes.

A future fast multimodal gate can fit above the same event interface if its value is demonstrated.

## Wiring into the existing memory sidecar

The repository integration keeps the feature opt-in. Attach one
`SpatialViewIndex` to the episode sidecar, then name the event-boundary reason
when ingesting an already validated legal envelope:

```python
spatial_index = SpatialViewIndex(episode_id)
sidecar = MemorySidecar(
    episode_id=episode_id,
    store=memory,
    decisions=cutoffs,
    resolve_rgb_ref=resolve_rgb_ref,
    spatial_index=spatial_index,
)
sidecar.ingest_observation(
    envelope,
    keyframe_reason="decision_required",
    keyframe_entity_ids=(...),
    keyframe_place_ids=(...),
)
sidecar.write_spatial_snapshot(run_dir / "spatial-memory.json")
```

Without `keyframe_reason`, ordinary memory behavior is unchanged. Without a
validated `estimated_pose`, the observation is retained normally but no posed
keyframe is invented. The snapshot is for offline replay and is not attached to
the live executive context.

Do this only on selected event boundaries / useful periodic fallback, not every camera frame.

Recommended initial boundary set:

- initial observation;
- `place_entered`;
- `object_sighting` when identity/location materially changes;
- `world_changed`;
- before/after important manipulation;
- skill failure/stall/target loss;
- verifier uncertainty;
- decision-required boundary;
- low-rate periodic fallback during long navigation.

The full native recording remains on disk. The Executive normally receives only current imagery + task state + a few selected historical views.

## WetRobo: what to borrow now vs later

Borrow now:

1. separate display/collision/motion authority;
2. deterministic/replayable artifacts with provenance;
3. coding agents can compile a repeatedly successful procedure into bounded deterministic tooling.

Do not copy now:

1. the evolved task-specific scene pipeline wholesale;
2. dozens of task scripts before BEHAVIOR failures justify them;
3. live self-modification of safety/control code.

The engineering-agent loop should remain research/offline: candidate changes -> tests/replay/simulation -> explicit promotion. Deployment consumes qualified artifacts.

## Acceptance tests before active use

1. `LegalObservation` pose remains the only source of keyframe pose.
2. A missing pose yields no posed keyframe; do not guess one.
3. Historical views never mutate `WorldState` directly.
4. Negative evidence is only emitted after explicit coverage accounting.
5. A local scene cannot claim collision authority without geometry.
6. A local scene cannot claim motion authority without collision readiness and calibration provenance.
7. No privileged BEHAVIOR scorer state, global pose, segmentation or target pose enters the records.
8. Keyframe retrieval remains bounded and causally timestamped.
