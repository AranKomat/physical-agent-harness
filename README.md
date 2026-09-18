# Physical Agent Harness

An experimental, model-agnostic runtime for connecting a sparse reasoning layer
to robot perception, world state, motor policies, verification, navigation, and
bounded recovery. The first integration target is BEHAVIOR with R1Pro.

## v0.6 implementation status

The offline core is implemented and tested. This is **not yet a qualified
BEHAVIOR robot runtime**. The original component overview below is retained
as architectural context; its implementation checklist is now a native
integration checklist.

```bash
python -m physical_harness demo --output runs/demo-new
python -m physical_harness doctor
```

Use a fresh demo output directory. The demo uses deterministic fixtures, not
real models or robot actions, and exercises executive decisions, chunked motor
execution, evidence, verification and task completion.

| Component | Implemented | Remaining integration |
| --- | --- | --- |
| Executive | Sparse semantic tool loop, bounded context and call budget | Model transport and accounting |
| World state | Episode-isolated beliefs, evidence, explicit task bindings, contradiction invalidation | Atomic sidecar snapshots and restart watermarks |
| Motor | Chunk/prefix execution, cancellation, deadlines, resource ownership | Qualified policy and calibrated R1Pro controller |
| Perception | Legal BEHAVIOR envelopes and RTSM translation | Live services and sensor calibration |
| Navigation | Depth occupancy, NetworkX routes, frontiers, semantic gateways | Pose estimator and qualified N0 controller |
| Verification | Evidence-bearing tier routing, GPT-6 role metadata and completion gates | Live GPT-6 transport and native evidence validator |
| Recovery | Evidence-bound, one-use translation previews | Native IK, collision checks and control |

### Limits

No paid API transport is enabled. Future GPT integrations should prefer Flex
when available and preserve approved budget limits. No training or held-out
evaluation is launched by this package.

Commands are not observations of success. Native inputs must exclude simulator
ground truth and scorer state. Synchronous callbacks must enforce their own
hard deadlines: post-call checks cannot preempt a hung service. Ambiguous motor
stops retain resource ownership until acknowledged.

Navigation assumes restricted camera geometry, not general SLAM. Its native
movement callback must enforce safety and shared resource ownership before
concurrent deployment. Strong verifiers must supply the evidence validator:
reference membership alone does not prove freshness or provenance.

Synthetic tests establish neither motor competence nor physical safety. No
inspected general policy currently has a verified training-free BEHAVIOR/R1Pro
path. G0.5 pairing is deferred, GR00T lacks a verified parallel-gripper R1Pro
interface, and no guessed action slicing or scaling is used.

See [adapter schemas](docs/ADAPTERS.md), [navigation assumptions](docs/NAVIGATION.md),
the [native replay contract](docs/NATIVE_REPLAY.md), and the
[integration results](docs/LIVE_RADIO_FIXTURE.md).
The [native recording bridge](docs/NATIVE_REPLAY.md) now validates the saved
16-frame sensor sequence; it intentionally does not invent simulation timestamps.
The opt-in [live radio fixture bridge](docs/LIVE_RADIO_FIXTURE.md) connects native
action prefixes to receipts, telemetry memory, conservative verification and
deterministic executive events. It is not a general-policy or GPT planning result.
The radio-trained pi0.5 checkpoint is an integration fixture only; held-out
generalization and general motor-policy selection are deferred.

A deliberately small, benchmark/model-agnostic core for the first
BEHAVIOR experiment.

It is **not** a complete robot stack. It provides:
- typed semantic skill / navigation / verification contracts;
- the previously tested evidence-backed `WorldState`;
- the previously tested stale-reply/resource `JobManager`;
- synchronous event routing;
- tiered verification routing;
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

The current suite contains 161 offline tests. They validate contracts and
failure handling; they do not establish robot competence or physical safety.

## Repository scope

This public repository contains only the reusable harness, tests, architecture
notes, and aggregate development results. It intentionally excludes model
weights, simulator assets, benchmark data, captured observations, videos,
credentials, billing ledgers, and private evaluation artifacts.

No software license has been selected yet. Public visibility does not grant
permission to copy, modify, or redistribute the code beyond applicable law.

## Native Integration Checklist

1. Implement `BehaviorAdapter` using only legal RGB/depth/proprioception.
2. Qualify a general motor backend with documented R1Pro action compatibility and training provenance.
3. Run RTSM as a separate service and translate snapshots into `WorldState`.
4. Add an online 2D metric occupancy map + local planner built from legal
   depth and odometry/SLAM estimates.
5. Add a semantic place graph (rooms/doors/corridors) above the metric map.
6. Wire the tier-3 GPT-6 semantic verifier at sparse semantic boundaries; tier 2 remains disabled.
7. Add bounded EEF/IK direct-control backend.
8. Wire GPT-6 tool calling to these contracts at semantic event boundaries.

See `BUILD_SPEC.md` for the detailed handoff.
