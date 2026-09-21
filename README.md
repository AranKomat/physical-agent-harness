# Physical Agent Harness

An experimental, model-agnostic runtime for connecting a sparse reasoning layer
to robot perception, world state, motor policies, verification, navigation, and
bounded recovery. The first integration target is BEHAVIOR with R1Pro.

## Implementation status

The offline core, bounded experiment runner, and sparse posed-view memory
contracts are implemented and tested. This is **not yet a qualified BEHAVIOR
robot runtime**. The original component overview below is retained as
architectural context; its implementation checklist is now a set of native
qualification and integration gates.

### Research status, 2026-09-21

Private native experiments have closed bounded live GPT executive/verifier
cycles, recorded live memory shadow evidence, and completed controlled causal
memory ablations. Several released multitask BEHAVIOR policies now have working
native interfaces, but **no reliable general motor or task-success improvement
from supervision/memory has been demonstrated**. See the
[experiment progress report](docs/EXPERIMENT_PROGRESS_20260921.md) for measured
results, checkpoint pins, failed attempts, limitations and remaining stages.
The matched radio driver has an offline-tested public port under
[`experiments/behavior`](experiments/behavior/README.md); other private drivers
and licensed observations remain excluded.

The opt-in [Geometry and Action Compiler V1](docs/ACTION_COMPILER_V1.md) adds
evidence-bound geometry, candidate/action catalogs, bounded primitive execution,
and control-duty accounting. See the [integration validation](docs/ACTION_COMPILER_V1_INTEGRATION.md)
for actual-checkout tests and merge corrections. It does not enable native
motion, install GraspGenX weights, or replace the current experiment controller.

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
| Executive | Sparse semantic tool loop, bounded context/call budget, image-bearing model transports and durable accounting; bounded live GPT cycles tested privately | Task-level progress/recovery qualification and deployment-specific endpoint/budget checks |
| World state | Episode-isolated beliefs, evidence, explicit task bindings, contradiction invalidation | Atomic sidecar snapshots and restart watermarks |
| Motor | Chunk/prefix execution, cancellation, deadlines, resource ownership and bounded simulator subprocess IPC; several private native policy adapters exercised | Performance-qualified frozen motor and reproducible deployment of native drivers |
| Perception | Legal BEHAVIOR envelopes, Open3D RGB-D odometry, RTSM translation and relation memory | Live artifact store, services and sensor calibration |
| Navigation | Depth occupancy, NetworkX routes, frontiers, semantic gateways | Native odometry qualification and qualified N0 controller |
| Verification | Evidence-bearing tier routing, image-bearing semantic verifier transport and completion gates; bounded live semantic checks | Positive manipulation-state recognition and broader native evidence qualification |
| Historical memory | Episode-local cards/media, causal cutoffs, shadow decision packets, frozen replay, and opt-in posed RGB-D keyframes; private native shadow and controlled replay tested | Live decision/task benefit beyond controlled scripted traces |
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

[Hybrid V0](docs/HYBRID_V0.md) adds an opt-in sequential motor backend: local
classical navigation, optional joint staging, the unchanged frozen policy, and
optional guarded retreat. It reuses native bindings and the experiment journal,
with evidence-bound handoffs and whole-robot ownership. Its numerical fixture
passes offline; native R1Pro codecs, legal target localization, collision checks
and measured handoffs still need qualification. It is not enabled in the matched
radio runner and does not change the executive, verifier or memory defaults.
The first [native hybrid qualification](docs/HYBRID_NATIVE_QUALIFICATION_20260921.md)
passed hold-command equivalence and a five-tick stationary settling diagnostic;
nonzero base movement, swept clearance and policy handoffs remain unqualified.
The [Hybrid V0.1 experiment utilities](docs/HYBRID_V01_EXPERIMENT_TOOLS.md) add
depth-supported staging proposals, handoff telemetry, equal-policy-exposure
diagnostics and a paused-world comparison that does not bypass stale-state gates.
The [ordered experiment queue](docs/HYBRID_EXPERIMENT_SEQUENCE.md) starts with
native base qualification, then no-GPT Behavior-Skill A-short/B-short trials.

### Limits

No paid API transport is enabled by default. Live transport requires explicit
network and payment opt-ins. Future GPT integrations should prefer Flex when
available and preserve approved budget limits. No training or held-out
evaluation is launched by this package.

For development and sparse simulator-paused experiments, the optional
ChatGPT-authenticated
[`codex exec` transport](docs/CODEX_EXEC_EXPERIMENT_TRANSPORT.md) provides a
separate, schema-validated path without replacing the deployment API adapter.
Its agent prefix is reduced but not eliminated, so it is not an API-equivalent
baseline for model-quality comparisons.

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

Synthetic tests establish neither motor competence nor physical safety.
Behavior-Skill, Corvid and Kmy multitask GR00T have working native R1Pro paths
in private experiments without training by us. These are BEHAVIOR-adapted
checkpoints, not zero-shot base-model transfers, and none is performance-qualified.
G0.5/base-policy pairing remains unqualified; no guessed action slicing or scaling
is used. Known benchmark training overlap must be disclosed.

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
generalization is deferred and final multitask motor selection remains unresolved.
The additive [multimodal memory prototype](docs/MULTIMODAL_MEMORY_V07.md) now has
an opt-in [shadow integration](docs/MEMORY_INTEGRATION_V08.md) for legal
observations, runtime events and durable decision cutoffs. Shadow mode returns
the unchanged executive context; it cannot affect actions, verification, or task
completion. A recorded native radio cycle confirmed source/card coverage and
causal replay, but is too narrow to establish useful long-term recall. See the
[research ledger](docs/MEMORY_RESEARCH_LEDGER.md) and
[gap analysis](docs/HARNESS_GAP_ANALYSIS_V08.md).
The runtime exposes closed-boundary hooks for fresh post-skill observation,
verification, ledger update and event publication in that order. Private native
pilots have exercised real GPT calls across these boundaries. They do not yet
qualify autonomous perception, navigation, manipulation or long-horizon success.

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

The current suite contains 580 offline tests. They validate contracts and
failure handling; they do not establish robot competence or physical safety.

The core historical store and retriever use only the standard library. Install
`.[memory]` when creating source-preserving image crops or running the memory
replay example; `.[dev]` includes that image dependency for the complete suite.

## Repository scope

This public repository contains the reusable harness, tests, architecture
notes, aggregate development results, and a portable
[matched BEHAVIOR experiment runner](experiments/behavior/README.md).
The runner is an offline-tested port of the private radio driver; it has not
yet been requalified on a live simulator. It intentionally excludes model
weights, simulator assets, benchmark data, captured observations, videos,
credentials, billing ledgers, and private evaluation artifacts.

No software license has been selected yet. Public visibility does not grant
permission to copy, modify, or redistribute the code beyond applicable law.

## Qualification And Integration Gates

1. Extend the completed bounded native/GPT semantic cycle to task-relevant
   progress, recovery and supported completion, rather than treating integration
   success as physical task success.
2. Extend live memory-shadow checks to longer episodes, restart behavior and
   durable RGB-D retention without changing actions prematurely.
3. Move beyond the completed controlled multi-place memory replays to a live
   memory-sensitive decision comparison. Scripted interventions and proposed
   actions do not establish autonomous task benefit.
4. Launch and qualify the RTSM/perception service against native artifacts,
   including identity, relation, and object-permanence errors.
5. Qualify RGB-D odometry, occupancy planning, place/gateway resolution, and
   the N0 base controller on native sequences.
6. Qualify bounded native IK, trajectory, and collision recovery before enabling L3.
7. Performance-qualify a frozen multitask motor under matched task/horizon and
   supervision conditions. Preserve each published control recipe and disclose
   training overlap; the official radio checkpoint remains a fixture only.
8. Qualify existing supervised IPC, hard service timeouts and accounting under
   failures and restarts; close remaining snapshot/watermark gaps before longer
   autonomous episodes.

See `BUILD_SPEC.md` for the detailed handoff.
