# Physical Agent Harness

An experimental, model-agnostic runtime for connecting a sparse reasoning layer
to robot perception, world state, motor policies, verification, navigation, and
bounded recovery. The first integration target is BEHAVIOR with R1Pro.

## v0.11.1 implementation status

The offline core, bounded experiment runner, and sparse posed-view memory
contracts are implemented and tested. This is **not yet a qualified BEHAVIOR
robot runtime**. The original component overview below is retained as
architectural context; its implementation checklist is now a set of native
qualification and integration gates.

```bash
python -m physical_harness demo --output runs/demo-new
python -m physical_harness doctor
python -m physical_harness.experiment demo --output /tmp/physical-demo-new
python -m physical_harness.experiment doctor \
  --config configs/experiment_v010/doctor.fixture.json
```

Use a fresh demo output directory. The demo uses deterministic fixtures, not
real models or robot actions, and exercises executive decisions, chunked motor
execution, evidence, verification and task completion.

| Component | Implemented | Remaining integration |
| --- | --- | --- |
| Executive | Sparse semantic tool loop, bounded context/call budget, image-bearing model transports and durable accounting | Real model IDs, rates, endpoint qualification and approved budget |
| World state | Episode-isolated beliefs, evidence, explicit task bindings, contradiction invalidation | Atomic sidecar snapshots and restart watermarks |
| Motor | Chunk/prefix execution, cancellation, deadlines, resource ownership and bounded simulator subprocess IPC | Qualified policy, native driver wiring and calibrated R1Pro controller |
| Perception | Legal BEHAVIOR envelopes, Open3D RGB-D odometry, RTSM translation and relation memory | Live artifact store, services and sensor calibration |
| Navigation | Depth occupancy, NetworkX routes, frontiers, semantic gateways | Native odometry qualification and qualified N0 controller |
| Verification | Evidence-bearing tier routing, image-bearing semantic verifier transport and completion gates | Live GPT-6 qualification and native evidence validator |
| Historical memory | Episode-local cards/media, causal cutoffs, shadow decision packets, frozen replay, and opt-in posed RGB-D keyframes | Native posed-view capture and multi-object held-out replay before active use |
| Local scene | Bounded scene-build requests with separate display, collision, and motion authority | Select and qualify a builder only after a real geometry failure |
| Recovery | Evidence-bound, one-use translation previews | Native IK, collision checks and control |

The opt-in [rich current-context profile](docs/RICH_CONTEXT_V09.md) preserves the
full task ledger, a broad entity roster, detailed focus history, semantic events,
spatial context, and measured negative evidence for the next GPT experiment. It
does not replace the conservative projector or enable historical memory in live
decisions. `BroadMemorySelector` and `attach_rich_memory` support causal M1/M2
replay after the shadow trace has been recorded.

The [v0.10 experiment runner](docs/EXPERIMENT_RUNNER_V010.md) connects legal
image observations, rich current context, predeclared semantic actions, fresh
verification, task-ledger updates, shadow memory, conservative cost accounting,
and frozen replay export. Network access, paid calls, and simulated motion each
require a separate command-line opt-in. The shipped fixture remains synthetic.

The [v0.11 spatial-memory layer](docs/SPATIAL_MEMORY_V011.md) adds sparse posed
RGB-D keyframes, explicit coverage/negative-evidence records, and on-demand
local-scene contracts. Recording is opt-in at the legal-envelope sidecar and
remains outside live executive context. It does not add a permanent dense map,
scene builder, or motion authority from visual plausibility.
v0.11.1 keeps broad OR matching for ordinary history but requires entity/place
conjunction for local-scene requests, preserves metric viewpoint diversity from
the same moving camera, and allows up to 256 entity tags per shadow keyframe.

### Limits

No paid API transport is enabled by default. Live transport requires explicit
network and payment opt-ins. Future GPT integrations should prefer Flex when
available and preserve approved budget limits. No training or held-out
evaluation is launched by this package.

For development and sparse simulator-paused experiments, the optional
ChatGPT-authenticated
[`codex exec` transport](docs/CODEX_EXEC_EXPERIMENT_TRANSPORT.md) provides a
separate, schema-validated path without replacing the deployment API adapter.

Commands are not observations of success. Native inputs must exclude simulator
ground truth and scorer state. Synchronous callbacks must enforce their own
hard deadlines: post-call checks cannot preempt a hung service. Ambiguous motor
stops retain resource ownership until acknowledged.

Navigation assumes restricted camera geometry, not general SLAM. Its native
movement callback must enforce safety and shared resource ownership before
concurrent deployment. Strong verifiers must supply the evidence validator:
reference membership alone does not prove freshness or provenance.

The optional RGB-D odometry backend is an implemented local-pose estimator, not
a localization-accuracy claim. It rejects large jumps, low-information updates,
frame gaps and cross-episode input, and latches loss rather than silently
resetting the map origin. Install it with `pip install -e ".[localization]"`.

Synthetic tests establish neither motor competence nor physical safety. No
inspected general policy currently has a verified training-free BEHAVIOR/R1Pro
path. G0.5 pairing is deferred, GR00T lacks a verified parallel-gripper R1Pro
interface, and no guessed action slicing or scaling is used.

See [adapter schemas](docs/ADAPTERS.md), [navigation assumptions](docs/NAVIGATION.md),
the [closed semantic boundary](docs/SEMANTIC_CYCLE.md), the
[native replay contract](docs/NATIVE_REPLAY.md), and the
[integration results](docs/LIVE_RADIO_FIXTURE.md).
The [native recording bridge](docs/NATIVE_REPLAY.md) now validates the saved
16-frame sensor sequence; it intentionally does not invent simulation timestamps.
The opt-in [live radio fixture bridge](docs/LIVE_RADIO_FIXTURE.md) connects native
action prefixes to receipts, telemetry memory, conservative verification and
deterministic executive events. It is not a general-policy or GPT planning result.
The radio-trained pi0.5 checkpoint is an integration fixture only; held-out
generalization and general motor-policy selection are deferred.
The additive [multimodal memory prototype](docs/MULTIMODAL_MEMORY_V07.md) now has
an opt-in [shadow integration](docs/MEMORY_INTEGRATION_V08.md) for legal
observations, runtime events and durable decision cutoffs. Shadow mode returns
the unchanged executive context; it cannot affect actions, verification, or task
completion. A recorded native radio cycle confirmed source/card coverage and
causal replay, but is too narrow to establish useful long-term recall. See the
[research ledger](docs/MEMORY_RESEARCH_LEDGER.md) and
[gap analysis](docs/HARNESS_GAP_ANALYSIS_V08.md).
The runtime exposes closed-boundary hooks for fresh post-skill observation,
verification, ledger update and event publication in that order. The native
radio fixture still needs its live perception and GPT-6 transports wired into
those hooks before it constitutes an autonomous semantic cycle.

A deliberately small, benchmark/model-agnostic core for the first
BEHAVIOR experiment.

It is **not** a complete robot stack. It provides:
- typed semantic skill / navigation / verification contracts;
- the previously tested evidence-backed `WorldState`;
- the previously tested stale-reply/resource `JobManager`;
- synchronous event routing;
- tiered verification routing;
- legal RGB-D odometry with explicit loss semantics;
- action-conditioned relation provenance and occlusion-safe relation memory;
- source-backed historical event, entity, place and motion memory;
- a minimal semantic topological map;
- adapter boundaries for BEHAVIOR and RTSM;
- a swappable `MotorBackend` protocol.

## Intended external components

- **BEHAVIOR-1K v3.9.2**: simulator/evaluator, outside policy process.
- **Motor backend**: swappable contract; no general R1Pro policy is qualified yet.
- **Official radio pi0.5**: bounded native integration fixture, not generalization evidence.
- **RTSM**: v0 object memory.
- **RoboStream/DynaMem ideas**: action-conditioned relation updates and
  dynamic object disappearance/relocation behavior.
- **HomeRobot / Stretch AI ideas**: metric navigation, exploration, semantic
  object navigation, finite-state skill decomposition.
- **RPent**: execution/tool-runtime code donor; use directly only if its
  BEHAVIOR integration is cheaper than the thin custom adapter.
- **Khronos**: later real-world 4D SLAM / long-term change backend, not a
  dependency of the first simulation experiment.

## Run tests

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Run the synthetic shadow wiring example with:

```bash
python examples/memory_shadow_integration.py --output /tmp/memory-shadow-new
```

Render the synthetic rich current context with:

```bash
python examples/rich_context_example.py
```

Exercise sparse posed-view selection with:

```bash
python examples/spatial_memory_v011_demo.py
```

The current suite contains 332 offline tests. They validate contracts and
failure handling; they do not establish robot competence or physical safety.

The core historical store and retriever use only the standard library. Install
`.[memory]` when creating source-preserving image crops or running the memory
replay example; `.[dev]` includes that image dependency for the complete suite.

## Repository scope

This public repository contains only the reusable harness, tests, architecture
notes, and aggregate development results. It intentionally excludes model
weights, simulator assets, benchmark data, captured observations, videos,
credentials, billing ledgers, and private evaluation artifacts.

No software license has been selected yet. Public visibility does not grant
permission to copy, modify, or redistribute the code beyond applicable law.

## Qualification And Integration Gates

1. Wire the reviewed native BEHAVIOR driver into the v0.10 subprocess bridge,
   then close one live radio-fixture cycle from legal perception through GPT-6
   verification and ledger update into a real GPT-6 executive turn.
2. Exercise episodic memory concurrently in live shadow mode and verify timing,
   source lineage, backpressure, and causal cutoffs without changing actions.
3. Collect a multi-object, multi-place development trace and compare current,
   episodic, and posed-keyframe conditions under equal context budgets before
   enabling historical context.
4. Launch and qualify the RTSM/perception service against native artifacts,
   including identity, relation, and object-permanence errors.
5. Qualify RGB-D odometry, occupancy planning, place/gateway resolution, and
   the N0 base controller on native sequences.
6. Qualify bounded native IK, trajectory, and collision recovery before enabling L3.
7. Qualify a general motor backend with documented R1Pro interfaces and training
   provenance; the radio-trained pi0.5 checkpoint remains a fixture only.
8. Add supervised IPC, hard service timeouts, restart watermarks, and end-to-end
   accounting before longer autonomous episodes.

See `BUILD_SPEC.md` for the detailed handoff.
