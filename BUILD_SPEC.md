# Physical Agent Harness — Build Specification v0.9
## Handoff for the coding/research agent

Date: 2026-09-19

## 1. Goal

Build the smallest reusable **physical-agent harness** needed to let a strong
executive model (initially GPT-6) solve one difficult BEHAVIOR task using a
swappable learned motor policy, persistent world state, conventional navigation,
tiered verification, and bounded direct control for recovery.

Current implementation decision (2026-09-19): no inspected general policy has a
verified training-free BEHAVIOR/R1Pro path. G0.5 pairing is deferred, GR00T lacks
a verified parallel-gripper R1Pro interface, and the official radio-trained
pi0.5 checkpoint is an integration fixture only. The held-out generalization
experiment remains deferred; no training is authorized.

v0.9 status: the offline contracts and prototypes below are implemented. The
radio fixture has closed one live semantic verification boundary with fresh
legal evidence, while its executive remains deterministic. Episodic memory is
wired into legal observations, runtime events, and decision cutoffs in shadow
mode; a retained native trace passed causal replay. Remaining work is live
service integration and empirical qualification, not another architecture pass.
An opt-in rich current-context profile is available for the GPT experiment;
historical memory remains excluded from live executive decisions until M0/M1/M2
replay is complete.

This is the robotics analogue of the environment around a coding agent:

```text
coding agent                       physical agent

filesystem                         world/entity state
grep/search                        find/query entity
shell                              skill execution
tests                              verification
git history                        episodic evidence
working tree                       current physical scene
IDE/navigation                     map + navigation service
tool calls                         motor / geometric primitives
```

The frontier model should not memorize the world, drive every control step, or
reconstruct seven minutes of history from images.

---

## 2. Architecture decision

Do **not** make any existing repository the monolithic base.

Use a thin custom harness as the stable integration layer and treat external
projects as replaceable services/code donors.

```text
                         GPT-6
                 sparse executive layer
                          │
                  Context Projector
                          │
        ┌─────────────────┼───────────────────┐
        │                 │                   │
   Task Ledger       Entity/World State   Evidence Store
        │                 │                   │
        │            RTSM initially           │
        │        + dynamic relation layer      │
        └─────────────────┼───────────────────┘
                          │
               Semantic Tool Runtime
          ┌───────────────┼───────────────────┐
          │               │                   │
   Navigation Service  Motor Skill        L3 Direct Control
      metric+topo      swappable backend     EEF/IK
          │               │                   │
          └───────────────┼───────────────────┘
                          │
                  BEHAVIOR R1Pro
                          │
                     observations
                          │
             perception/state/verifiers
```

The native BEHAVIOR scorer is out-of-band and must never become agent context.

---

## 3. Repository roles

### RPent — borrow the runtime pattern, don't depend on it yet

Repository: https://github.com/RLinf/RPent

Useful:
- planner abstraction;
- learned and scripted primitives behind one tool schema;
- environment/VLA server separation;
- session-aware policy clients;
- state capture after semantic primitives;
- transcript/dashboard infrastructure;
- retryable VLA primitive concept.

Why not use it wholesale now:
- no BEHAVIOR/R1Pro integration is currently the center of its released stack;
- its memory is not the persistent object-centric world model we need;
- adding our BEHAVIOR + navigation + state stack may be as much work as keeping
  a thin harness.

Decision:
- copy/adapt patterns and small permissively licensed utilities when valuable;
- optionally wrap RPent later as another runtime implementation;
- keep our public contracts independent of RPent classes.

### RTSM — v0 entity/spatial memory

Repository: https://github.com/calabi-inc/rtsm

Use first because it already exposes:
- RGB-D + pose input;
- stable object IDs;
- 3D locations;
- semantic labels/embeddings;
- view history;
- semantic/spatial query API.

Run it as a separate service/environment.

Add our own layer for:
- relation predicates (`IN`, `ON`, `HELD_BY`, `OPEN`, `CLOSED`);
- action-conditioned transitions;
- confidence/provenance;
- task relevance;
- contradiction events.

### RoboStream — borrow dynamic scene-graph semantics

Repository: https://github.com/yu2hi13/RoboStream

Borrow:
- causal spatio-temporal scene-graph idea;
- object permanence;
- re-perception after action;
- relation updates.

Do not adopt:
- its VLM planner/control path for this experiment;
- any evaluator mode using privileged simulator perception.

### DynaMem / Stretch AI — borrow dynamic update + object-navigation patterns

Repository: https://github.com/hello-robot/stretch_ai
Project: https://dynamem.github.io/

Borrow:
- deleting stale spatial points when new depth proves they are gone;
- object appeared/disappeared/moved handling;
- semantic query → target → navigation;
- exploration when object location is unknown;
- operation/task abstraction.

Do not make Stretch-specific robot classes part of the harness contract.

### HomeRobot — borrow 2D navigation/state machine ideas

Repository: https://github.com/facebookresearch/home-robot

Very useful patterns:
- 2D semantic occupancy map;
- frontier exploration;
- `NAV_TO_OBJ → GAZE → PICK → NAV_TO_REC → PLACE`;
- `ObjectNavAgent` / `DiscretePlanner`;
- instance memory.

We need an R1Pro/BEHAVIOR observation adapter, not the whole HomeRobot stack.

### Khronos — later real-world long-term mapping backend

Repository: https://github.com/MIT-SPARK/Khronos

Khronos is powerful but too heavy for v0:
- C++ / ROS2;
- full spatio-temporal metric-semantic SLAM;
- short-term dynamic objects + long-term environmental changes.

Do **not** make it a first-run dependency.

Design the `WorldModelBackend` so Khronos/Spark-DSG can replace or complement
RTSM when moving to long-running real-world deployments.

### Cradle / game agents — design pattern only

Repository: https://github.com/BAAI-Agents/Cradle

Borrow the concept:
- atomic/composite skill registry;
- skill curation;
- environment-specific adapter;
- persistent memory;
- self-reflection around execution.

Do not import it into the robot runtime.

---

## 4. Navigation design

Navigation should have **three levels**.

### Level N0 — control
High-frequency base control, obstacle avoidance, velocity limits.

No LLM.

### Level N1 — metric navigation
`navigate_to_pose`, `navigate_to_entity`, `explore_frontier`.

Owns:
- online occupancy map;
- localization/odometry estimate;
- A*/D*/frontier planning;
- obstacle avoidance;
- replanning.

No GPT call unless a semantic exception occurs.

### Level N2 — semantic/topological navigation
A graph of places/gateways:

```text
room_A --door_17-- corridor_2 --door_31-- room_B
```

GPT can reason here.

Example:

```text
Goal: reach room_B

Harness:
  metric nav → door_17

door_17 closed
  → DOOR_BLOCKED event

GPT:
  open(door_17)

Harness:
  continue route → corridor_2 → door_31 → room_B
```

This captures the useful granularity the user identified:
GPT decides semantic transitions; normal navigation handles meters of movement.

### Scored BEHAVIOR restriction

The 2026 challenge allows RGB + depth + proprioception and disallows simulator
global pose, GT segmentation, target poses, full-scene point clouds, and other
privileged state.

Therefore:
- no OmniGibson scene traversal map as planner input in scored runs;
- no simulator room/object coordinates;
- build the map from legal observations;
- use an arbitrary local map origin;
- derive motion from odometry/SLAM, not global simulator pose.

A development-only oracle navigation mode may exist but must be impossible to
enable accidentally in scored runs.

---

## 5. Semantic place graph

Add a small graph above the metric map:

```text
PlaceNode:
  place_id
  kind: room | corridor | doorway | workcell | landmark
  label
  map_region
  confidence
  evidence

Gateway:
  entity_id
  connects(place_a, place_b)
  state: open | closed | unknown
  traversable
  evidence
```

For the first BEHAVIOR task this can be simple and mostly one-room.

The abstraction becomes much more valuable when moving to multi-room tasks.

---

## 6. Entity/world state

Use the previously written evidence-backed `WorldState` as the policy-facing
source of truth.

Keep:
- episode isolation;
- immutable evidence;
- stale-evidence rejection;
- commands separated from beliefs;
- belief history/provenance;
- bounded context projection.

Extend entity representation gradually:

```text
entity_id
label hypotheses
appearance embeddings
last-seen geometry
current region/place
visibility
confidence
relations
attribute beliefs
evidence history
```

Rules:
1. Command is not state.
2. Missing detection is not disappearance.
3. New evidence can invalidate old task completion.
4. Hidden contents retain uncertain containment beliefs.
5. Identical objects can remain identity-ambiguous.
6. State updates always carry evidence/provenance.

---

## 7. Task ledger

Task state is separate from world state.

```text
TaskPredicate:
  id
  expression
  dependencies
  status:
    planned
    running
    needs_verification
    observed_complete
    invalidated
  evidence
```

For Halloween example:

```text
pumpkin_1 IN cabinet_A
pumpkin_2 IN cabinet_A
candle_1 IN cabinet_A
candle_2 IN cabinet_A
candle_3 IN cabinet_A
all relevant cabinets CLOSED
cauldron NEXT_TO table
```

GPT should never reconstruct this from the full transcript.

---

## 8. Evidence store

Persist:
- current RGB/depth;
- skill-boundary keyframes;
- before/after verification pairs;
- short action clips on failure;
- motor receipts;
- verifier outputs;
- object-state transitions.

Large artifacts live by content hash / path; model context carries references.

Suggested retention:
- current camera frames;
- 3–5 recent semantic-boundary keyframes;
- retrieved older frames only when task/entity relevant.

---

## 9. Skill service / policy backends

Stable interface:

```text
run_skill(SkillRequest) -> SkillReceipt
```

A skill call is semantic, not a single action chunk.

Examples:

```text
pick(candle_1)
place(candle_1, cabinet_A)
open(cabinet_A)
close(cabinet_A)
```

Inside one skill:

```text
observe
→ policy inference
→ execute chunk prefix
→ observe
→ policy inference
→ execute
...
→ success / stall / timeout / target loss
```

GPT does not wake between chunks.

Current backend status:
1. Official radio-trained pi0.5: bounded wiring/integration fixture only.
2. G0.5: native R1Pro observations produce gripper output, but BEHAVIOR pairing
   and action compatibility are not qualified.
3. GR00T N1.7: no verified parallel-gripper R1Pro interface.
4. Xiaomi-Robotics-1 and DM0.5: no verified training-free BEHAVIOR/R1Pro path.

Do not claim motor generalization from the radio fixture and do not train or
adapt a policy without a separate explicit decision.

Keep backend-specific action codecs entirely inside adapters.

---

## 10. Direct L3 recovery

Provide bounded tools:

```text
inspect(target)
back_project(pixel)
preview_eef_pose(...)
preview_trajectory(...)
move_eef(...)
open_gripper()
close_gripper()
```

Use direct control only for:
- repeated policy failure;
- precision correction;
- policy out-of-distribution interaction;
- explicit recovery.

No raw torque generation by GPT.

For scored BEHAVIOR:
- target geometry must come from legal perception/depth;
- robot kinematics can be known;
- collision information must not come from hidden simulator scene geometry.

---

## 11. Verification

Tiered router:

### Tier 0 — receipt/telemetry
Examples:
- controller reached pose;
- gripper contact;
- joint target reached.

### Tier 1 — world predicates
Examples:
- `HELD_BY(candle_1, robot)`;
- `IN(candle_1, cabinet_A)`;
- `CLOSED(cabinet_A)`.

### Tier 2 — cheap VLM
Input:
- expected predicate;
- before/after images;
- small state slice.

Strict output:
```json
{
  "verdict": "verified|rejected|uncertain",
  "confidence": 0.0,
  "evidence": "..."
}
```

Tier 2 remains a supported router extension, but it is disabled for the v0
radio pilot. The tested Qwen diagnostic produced a high-confidence false
positive and is not qualified to complete tasks.

### Tier 3 — GPT-6
Use for:
- disagreement;
- low confidence;
- major milestones;
- repeated failure;
- semantically complex verification.

Do not use GPT-6 on every policy chunk.

For v0, GPT-6 Astra medium Flex is the selected semantic verifier. It runs only
at semantic boundaries, must cite supplied fresh evidence, and must abstain when
the claimed state is not observable. World/controller evidence is evaluated
before model escalation.

---

## 12. Executive interface

GPT-6 receives bounded context:

```text
goal
pending/completed task predicates
relevant entity beliefs
semantic navigation state
last skill receipt/event
current images
one retrieved keyframe if useful
available tools
remaining budgets
```

GPT outputs only a semantic decision:

```text
inspect(...)
navigate_to(...)
run_skill(...)
execute_l3(...)
request_verification(...)
finish(...)
```

Use the actual model API for scored comparisons. Codex can remain a development
convenience but should be labeled as a different agent runtime if measured.

---

## 13. Event model

Start deterministic:

```text
SKILL_VERIFIED
SKILL_FAILED
SKILL_STALLED
TARGET_LOST
STATE_CONTRADICTION
VERIFIER_UNCERTAIN
PRECONDITION_VIOLATED
ARRIVED
PATH_BLOCKED
DOOR_BLOCKED
WORLD_CHANGED
PLAN_EXHAUSTED
DECISION_REQUIRED
EXECUTION_TIMEOUT
```

GPT wakes on these events, not at a fixed frame rate.

---

## 14. Process layout

Keep incompatible dependencies separate:

```text
behavior_env process
    └─ Isaac Sim / OmniGibson

motor server
    └─ radio pi0.5 fixture / future qualified policy

world-state service
    └─ RTSM + relation adapter

navigation service
    └─ mapper + planner

verifier service
    └─ GPT-6 semantic verifier (sparse tier 3)

executive process
    └─ GPT API + context projector + task ledger

optional L3 service
    └─ IK / trajectory tooling
```

Use versioned JSON/msgpack/protobuf-like messages. Avoid pickle across process
boundaries.

---

## 15. Build order

### Phase A — contracts (offline complete)
The typed contracts and failure invariants are implemented and tested.

Do not let individual integrations leak their native types into the executive.

### Phase B — legal BEHAVIOR observation adapter (implemented; native qualification pending)
Implemented:
- reset/step;
- RGB/depth refs;
- proprio;
- camera intrinsics/frames;
- action conversion;
- episode/video logging.

Explicitly test absence of privileged state.

### Phase C — motor integration fixture (completed, qualification unresolved)
Use the official radio-trained pi0.5 checkpoint only to validate the native
bridge, action-prefix execution, receipts and fresh observations. General motor
qualification is a separate deferred workstream.

### Phase D — RTSM adapter (offline implementation complete; native service pending)
Feed RGB-D + legal pose estimate. Persist entities and observed semantic
relations to WorldState. Retain action-conditioned relation provenance and
occlusion-safe memory without treating remembered state as fresh verification.

Replay tests:
- moving camera / stationary object;
- occlusion;
- object moved by robot;
- identical objects;
- stale perception results.

### Phase E — navigation (prototype complete; native qualification pending)
Start simple:
- depth → local occupancy;
- implemented Open3D RGB-D odometry/localization;
- A*;
- target/entity goal;
- frontier exploration;
- semantic place/gateway graph.

Borrow HomeRobot/Stretch AI algorithms aggressively.

The odometry implementation rejects unsafe updates and never consumes simulator
pose. Native calibration, accuracy and N0 control remain unqualified.

### Phase F — task ledger/context (offline complete)
The evidence-gated task ledger and bounded current-context projector are
implemented. Historical memory remains shadow-only until replay qualification.

### Phase G — verification (one live boundary complete; broader qualification pending)
World predicates run before sparse GPT-6 semantic verification. One retained
radio cycle used GPT-6 medium Flex and correctly remained uncertain. Do not
enable a cheap tier-2 verifier until it passes an independent qualification set.

### Phase H — L3 recovery (contracts complete; native backend pending)
Preview/execute contracts enforce strict bounds and evidence. Native EEF/IK,
trajectory, and collision implementations remain unqualified.

### Phase I — live integration and one full task
First close a real GPT-6 executive cycle and run memory live in shadow mode.
Then run one difficult BEHAVIOR task with complete instrumentation.

---

## 16. Parallel workstreams

Do not serialize the whole project on the motor backend.

P0 workstreams:
- live perception/world update + GPT-6 verifier + GPT-6 executive cycle;
- live memory shadow capture and causal replay checks;
- multi-object/multi-place trace collection and M0/M1/M2 evaluation.

P1 workstreams:
- native RTSM relation/identity qualification;
- native odometry, N0 navigation, and place/gateway qualification;
- bounded native L3 recovery.

General motor-policy qualification remains separate and must not block proving
the harness with the known radio fixture.

The stable contracts allow these to merge.

---

## 17. Acceptance tests before first full episode

Harness:
- stale policy reply rejected;
- episode state cannot leak;
- command does not mutate world belief;
- conflicting evidence raises event;
- task completion requires evidence.

Perception:
- object identity persists across viewpoint;
- occlusion doesn't delete;
- relocation updates old location;
- no GT state is visible.

Navigation:
- reaches visible waypoint;
- replans around obstacle;
- closed doorway produces semantic event instead of oscillating;
- target-not-found can trigger exploration.

Motor:
- semantic skill can span multiple policy chunks;
- timeout/cancel produces receipt;
- policy backend can be swapped with no executive changes.

Verification:
- high-confidence world predicate avoids a model call;
- GPT escalation occurs only when required and cites fresh evidence;
- unobservable outcomes remain uncertain;
- tier 2 remains disabled until independently qualified.

---

## 18. Metrics

Per episode:

Capability:
- native Q score;
- full success;
- predicates verified.

Executive:
- GPT calls;
- images;
- text/vision tokens;
- cost;
- latency.

Motor:
- policy calls;
- chunks;
- executed actions;
- idle gaps;
- skill success by type.

Navigation:
- distance;
- replans;
- blocked-gateway events;
- exploration time.

World state:
- identity swaps;
- stale belief rejections;
- contradictions;
- lost targets.

Verification:
- calls by tier;
- later-discovered false positives/negatives.

Recovery:
- L2→L3 escalations;
- L3 successes;
- return-to-policy rate.

---

## 19. What not to build

Not now:
- universal ROS replacement;
- learned planner/router;
- new VLA;
- custom SLAM research;
- Khronos integration;
- long-term fleet memory;
- Physical Analysis website;
- all-policy × all-executive matrix;
- task-specific training.

The goal is one strong, inspectable BEHAVIOR run and a reusable architecture.

---

## 20. Current implementation decision

Keep the thin harness stable while live qualification proceeds.

The immediate code path should be:

```text
BEHAVIOR legal obs
→ RTSM/world state
→ task/context
→ GPT-6 semantic decision
→ navigation OR motor skill
→ tiered verification
→ event
→ GPT-6
```

Use the task-trained radio pi0.5 checkpoint only as an integration fixture. Do
not choose G0.5, GR00T, or another general policy until its R1Pro interface and
training provenance are verified. The harness must remain backend-agnostic.
