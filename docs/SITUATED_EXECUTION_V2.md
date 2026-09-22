# Situated Execution V2 — research-agent implementation handoff

**Prepared:** 2026-09-22. **Repository:** `AranKomat/physical-agent-harness`.
**Reviewed base:** `1531ac983ebf142b4aca0b790538fff89330e3ef`.
**Original delivery:** additive overlay; no native campaign launch, paid call, model download, or policy training.
**Integration:** applied to `a4a2246` on 2026-09-22; all pinned reused interfaces matched.
See [actual-checkout validation](SITUATED_EXECUTION_V2_INTEGRATION.md).

This document is self-contained. It explains what is implemented, where to connect it, what remains unqualified, and the experiment order. The package combines the useful recent ideas without replacing the Action Compiler, WorldState, JobManager, verifier, model-accounting layer, or frozen-policy recipe.

## 1. Read this before integrating

The bundle was reviewed against Hybrid V0/V0.1, Geometry and Action Compiler V1, native acquisition/handoff diagnostics, causal memory, and the SAM 3 image-only retained-frame experiment [S1]. The integration checkout is newer: **SAM 3.1 is already the local tracking baseline**, with a corrected live shadow run [S9]. Keep both the earlier evidence and that corrected worker intact. V2's optional prefix-replay adapter is a separate offline tool, not a replacement or qualification of live tracking, identity association, or native motion.

The corrected run completed 768 frozen-policy actions and 25 captures with zero drops; all 50 raw-image reads used the current frame. Warm tracking was 252 ms median / 284 ms p95; observation ingress to mask/depth ready was 483 ms median / 540 ms p95. These are sparse 32-action boundary samples, not video-rate qualification. Earlier mask-freshness claims were invalidated by an adapter frame-index bug and remain explicitly superseded in the report. V2 does not undo that correction or restart policy/model selection.

The native reports distinguish exploratory simulator interventions with **unknown clearance** from strict qualified motion. Do not use this new software to expand that envelope. The earlier paired acquisition differed before intervention; a single pair is operational evidence, not a causal improvement estimate. Approach-only instructions are not requests to activate the radio. Preserve completed reports, model recipes, hashes, and every failed/rejected run [S2].

**What is implemented:** evidence-bound object semantics, inspection goals and camera-view proposals, bounded semantic graphs and node-local repair, causal monitor packets and conservative result handling, text-only branching contracts, exact-dependency representation caching, optional bounded keypose proposals, and an actual SAM 3/3.1 prefix-replay API adapter.

**What is not claimed:** solved cross-view identity association, a live causal streaming SAM service, qualified R1Pro view-motion/IK/collision/contact control, reliable model-generated keyposes, trained completion-monitor transfer, zero-shot arbitrary-environment competence, or measured task/energy improvement.

## 2. Architectural boundary

```text
Existing legal RGB-D / proprioception and retained evidence
             |
       sparse recognition + instance tracking observations
             |
       IdentityLedger projection onto existing Journal / WorldState
       remembered semantics + current measured geometry + explicit ambiguity
             |
       information goal / outcome goal / semantic task graph
             |
       late-bound current entity/part and current Action Compiler catalog
             |
       existing ActionExecutor + shared JobManager + native reviewed Driver
             |
       causal monitor observations -> advisory event / external verifier
             |
       existing independent task ledger
```

A graph stores **roles and skill dependencies**, not a meter coordinate copied from an old scene. Geometry is recomputed or retrieved under exact current dependencies at node execution. No accurate simulator of a new environment is assumed. Robot calibration, relevant observed geometry, competent primitives, and truthful uncertainty handling are still required. A partial map is not a license to treat unseen space as empty.

The model-facing responsibilities are separate:

- The main executive authors a bounded semantic graph, selects existing action IDs, or proposes a bounded repair.
- An optional fast selector chooses among branches supported by complete, current structured facts. It cannot decide away missing visual evidence.
- An optional Astra-style proposal call supplies a few **anchor-relative** TCP keyposes. This is not the normal action-selection schema and carries no execution authority.
- Native reviewers, controllers and the independent verifier retain their existing responsibilities.

No model weights are loaded by importing `physical_harness.situated`. No provider client, tracker model, simulator, or actuator is started on import.

## 3. New package inventory

All code is under `physical_harness/situated/`. Existing setuptools discovery already covers it; there are no required edits to upstream source or dependency declarations. Numerical view/keypose helpers use NumPy and SAM-prefix image checks use Pillow, already present in the repository development/geometry environments; no heavy model dependency is added to the core.

| Module | Implemented function |
|---|---|
| `contracts.py` | Current evidence-bound facts, semantic bindings, explicit capability effects/qualification, scope budgets. Reuses Action Compiler `Basis`. |
| `identity.py` | Bounded journal-backed identity/semantic history, ambiguous/contradictory evidence, current-geometry admission, geometric association-candidate filtering, optional WorldState projection. |
| `visual.py` | Distinct observed assets, command anchors, outcome references, hypothetical references; causal monitor windows and explicitly granted external demonstrations. |
| `inspection.py` | Camera-orbit view proposals with explicit up calibration; ranking of assessed inspection candidates; existing stage/navigation plus passive-capture programs. |
| `motion.py` | Strict bounded anchor-relative keypose schema; SE(3) composition; path/offset checks; gripper changes disabled by default; compilation into existing Programs. |
| `programs.py` | Custom Program -> existing Catalog bridge and mandatory additional per-step review wrapper. |
| `graph.py` | Strict graph parsing, no scripts/coordinates in node schema, explicit branches, bounded cycles, registered skill authoring context. |
| `graph_runtime.py` | Sequential durable orchestration, late role/fact binding, node budgets, receipt validation, suspension/fault handling, one-node repair at quiescent boundaries. |
| `integration.py` | Existing ActionExecutor adapter, current identity-role binding, advisory EventBus bridge. No nested actuator owner. |
| `monitor.py` | Observed-only cited progress judgments, unknown state, command/time binding, durable debounce and independently confirmed advisory completion. |
| `decision.py` | Fresh sufficient-facts packets and exact offered-ID replies for a model-neutral text-only branch selector. |
| `perception.py` | Advisory recognition/tracking/geometry scheduling for relevant objects; separates missing category evidence from stable tracked identity. |
| `reuse.py` | Bounded exact-dependency TTL/LRU representation cache. Explicitly excludes executable catalogs, poses and collision approvals. |
| `sam_replay.py` | Explicitly provisioned SAM 3 or 3.1 loader plus point-seeded, forward-only, bounded causal-prefix replay, tail publication and session cleanup. |
| `evaluation.py` | CPU monitor-label and trace accounting. No automatic success/energy claims. |
| `fixture.py`, `__main__.py` | Synthetic end-to-end software example using the existing real catalog, executor, JobManager and Journal contracts. |

Existing RGB-D deprojection, partial point clouds, grasp generation, classical contact templates, policy adapters and control-duty metrics remain in `action_compiler`. V2 does not duplicate them.

## 4. Object permanence: persist meaning, not unobserved geometry

The immediate motivating case is the radio seen clearly from the front and ambiguously from the side.

```text
canonical recognition:       object_17 -> radio, source frontal frame
later side view:             current category ambiguous
established same-instance:   object_17 still associated with this measured mask
result:                     remembered radio label + current side-view geometry
```

`Tracklet` keys include episode, camera, tracker session and local ID. **SAM's local ID is not a globally stable physical identity.** The same integer on another camera or in a restarted session is not automatically the same object.

`IdentityLedger.new_entity(track, claim)` creates an episode-local identity. `observe` requires an `AssociationProof` bound to both the prior entity revision and the exact new track fingerprint. The proof explicitly records temporal and geometric support, unique association, method, and evidence. All three statuses must be established, not merely high model confidence. `geometric_candidates` narrows a search by time/frame/geometry bounds but does not grant an association.

A nondiscriminative/ambiguous side view does not erase the last supported canonical label or refresh its age. Strong conflicting semantics record a conflict that blocks normal action binding. `mark_not_observed` retains history but removes current action eligibility. Explicit semantic resolution needs new discriminating evidence; it does not silently rewrite the history.

`ledger.binding(entity, current_basis)` requires the current track and evidence basis, an established association, and no unresolved semantic conflict. It exposes the canonical recognition source separately from current geometry. Historical semantics may be useful; a historical object pose is not current grasp clearance.

The matcher is still an integration responsibility. Feed it temporal mask continuity, calibrated cross-view geometry, appearance evidence where useful, and competing-instance hypotheses. Do not supply an all-true proof based only on the name `radio`, nearest center, tracker confidence, or a matching crop. Two similar objects crossing or reappearing after occlusion must be allowed to remain ambiguous.

Persistence uses new record kinds in the **existing Journal**, not a new database. `project_world` is an optional derived/inferred projection with separate predicate names; it does not overwrite RTSM's raw per-view `label` or claim to fix the perception service's own association logic. Only one reviewed writer should project those fields into WorldState.

## 5. Three different uses of images

`VisualGoal` distinguishes outcome and information goals. Assets separately distinguish observed images, a command-start reference, a desired-outcome reference, and a hypothetical desired outcome.

1. **Visual memory:** “This was a clear view of the radio earlier.” Historical recognition evidence, not current appearance or pose.
2. **Outcome reference:** “A drawer in this open state is the desired result.” Can guide a model/monitor; it is not evidence that the current drawer is open.
3. **Information goal:** “Acquire enough evidence to distinguish the radio from a box, or locate its control.” Success is reduced task-relevant uncertainty, not merely reaching a camera pose.

A hypothetical/generated image can be a reference, never observed evidence. A reference from another demonstration/episode requires an explicit `ReferenceGrant` tying its exact content hash to this episode and a reviewed availability time. Ordinary observations from a different episode remain forbidden.

The code does not implement pi0.7's trained visual-goal-conditioned action model or learned world-model subgoal generator. It provides a runtime reference contract inspired by that distinction [S6]. Do not inject new image tokens or modalities into an unchanged frozen checkpoint that was not trained to accept them.

## 6. Active inspection without invented visibility or motion authority

`orbit_views` proposes bounded **camera** poses around an observed target, using a calibrated up direction and current camera pose. It does not infer that a particular face of an unknown object is its front. It does not solve the robot configuration, guarantee increased information, or check collision.

A native geometry provider must map a camera proposal to a feasible robot base/arm pose, assess the expected view, and bind evidence. `InspectionCandidate` records both camera and robot poses. `rank_inspections` ranks the supplied heuristic value and travel cost; the score is not a calibrated probability or a motion permission.

`inspection_program` composes the existing stage/navigation program with a passive current capture. The resulting program additionally requires:

```text
situated_view_kinematics
situated_information_target
situated_camera_calibration
```

It also retains every ordinary compiler/driver check: freshness, calibration, full-body swept clearance, limits, native command encoding, payload and measured stopping. Reaching a viewpoint is not proof that identity is resolved; the following observer/monitor evaluates the information criterion.

If no view is qualified, return blocked/unknown and request an operator or stronger reasoner. Do not reinterpret passive `inspect` as permission for a 20 cm base move. That would bypass the current native qualification sequence.

## 7. Late-bound graphs: orchestration, not another robotics framework

The graph is a strict JSON artifact containing registered capability IDs, semantic roles, required fact names, labeled edges and budgets. There is no node field for executable Python, a simulator handle, arbitrary source paths, coordinates or gate overrides. Generated text is data.

Node kinds are `observe`, `monitor`, `decide`, `reason`, `act`, and `done`. `done` only uses `existing_task_ledger`. A monitor's word “complete” cannot finish the task unless the independent `finish_allowed` callback confirms the current ledger. The included `identify-target.graph.json` is an information-task example, not a complete radio-activation workflow or an authorized native run.

`GraphSession.advance` runs one node. The caller supplies a fresh `Basis`, `FactPacket`, and role bindings obtained at that point. Missing or unknown branch-critical facts route to `unknown` without dispatching the node. False is known information, not unknown. Conflicting or absent role bindings do not trigger guessed motion.

The session uses explicit capability effects and domain qualification. Operator-declared capability roles and required facts cannot be omitted by the generated graph. Operator `budget_limit` is separate from the graph's requested budget; a generated graph cannot enlarge it. Per-node and total visits/time are bounded. Graph cycles therefore cannot silently retry forever.

Execution is **sequential** in this delivery. Read/reason callbacks may not advance physics. Act callbacks delegate to the existing ActionExecutor; they must return counted motion plus an existing execution-receipt reference. The graph uses the shared ownership/quiescence check instead of reserving the same limbs a second time. No parallel actuator writes, speculative physical execution, or runtime code generation is introduced.

Each invocation is reserved durably before the handler runs. Unknown interrupted work and faults block reuse even under a new graph-session ID in the same journal. A process exit or timeout is not a physical stop acknowledgement. Native callbacks still require their own hard watchdogs or supervised worker boundary: Python cannot preempt a stuck control call safely.

`repair_current` allows a bounded replacement of the suspended node after an acknowledged, quiescent outcome. It requires the exact graph/failure revision, preserves the node ID, effect, roles and existing required facts, and cannot expand budgets. It is **node-local repair**, not arbitrary subgraph editing, safety-code rewriting or a full reproduction of GaP's simulation-rehearsal system [S7].

## 8. Sparse progress monitors and a restricted fast selector

A `MonitorPacket` uses an actual sequence of chronological observed front frames, a command-start anchor, and the current wrist view if available. Early episodes use fewer distinct frames instead of padding copies and calling them independent observations. Packet construction and direct dataclass construction both enforce causal/role rules.

The model-neutral response is one of `progress`, `complete`, `unknown`, `target_lost`, or `failed`, with observed-asset citations and the exact packet fingerprint. A result must cite current evidence; a command anchor or desired goal cannot support completion. Provider/model revision is supplied by the trusted transport, not the response.

`ProgressMonitor` defaults to **shadow**. A learned `complete` becomes `completion_candidate`. Promotion to an advisory `subgoal_complete` requires an explicitly qualified monitor revision, distinct advancing windows, and a separate independent check. It still does not write a task predicate. Repeated correlated windows are debounce inputs, not independent trials or statistical proof.

This borrows the command-reference and recent-observation pattern from RoboMME, not its task-specific trained LoRA or its reported accuracy [S8]. Controller-rate collision/stop checks remain local and deterministic. A VLM monitor is not a safety system.

`publish_monitor_event` emits advisory existing events for relevant exceptional outcomes. It never creates `SKILL_VERIFIED` from a learned completion. Do not wire every low-information frame into a paid executive call; apply the existing wake budget and active-subgoal policy.

The optional fast selector is only an interface, not a Jev dependency. `branch_packet` requires the full declared decision-relevant fact set, all current and non-unknown, and a trusted assertion that unresolved pixels are not needed. Branch predicates filter the options. The reply is only `{packet_id, choice_id}`, and resolution checks the current basis and fact revisions again. A structured state with missing evidence must escalate with images rather than have a text model invent the missing fact.

## 9. Astra-style keyposes: a separate proposal surface

Normal GPT action selection remains `{catalog_id, action_id}`. The optional motion-proposal surface accepts:

```json
{
  "basis_fingerprint": "exact current basis fingerprint",
  "arm": "right_arm",
  "waypoints": [
    {"anchor_id": "offered_current_anchor", "offset_m": [0.01, 0, 0],
     "rotvec_rad": [0, 0, 0], "gripper": "hold"}
  ]
}
```

Anchors are supplied by reviewed geometry, not by the model. Offsets and rotation vectors are in the **anchor TCP frame**. The parser enforces finite vectors, current basis, object identity, named arm, bounded waypoint count, offset/rotation bounds and cumulative translation length from the measured start. Configured limits are engineering envelopes, not automatically safe distances.

The implementation compiles into existing `MOVE_EEF` steps with full original review requirements, plus:

```text
situated_direct_motion
situated_whole_path
situated_anchor_grounding
```

Gripper changes are disabled by default. Explicit enablement adds measured grasp/release checks and a `situated_gripper_transition` review. A close is followed by a measured grasp check before subsequent movement.

This is not high-rate model control, a force controller, or general contact manipulation. Use the existing guarded press/pull/grasp primitives for contact. A collision-free waypoint sequence may still be semantically wrong. Evaluate semantic intent, whole-path feasibility and actual progress separately.

**Slow model call caveat:** V2 does not waive Action Compiler freshness or change a source timestamp to make a reply executable. The graph may carry a semantic intent across time and bind it to a new current catalog. A metric proposal is bound to its actual capture and must be regenerated/re-grounded under a separately reviewed protocol when stale. A paused simulator does not make an old image newly captured. Establish paused-world dispatch semantics before claiming live Astra-direct execution works.

## 10. Stateful inference without unsafe reuse

`RepresentationCache` implements bounded TTL/LRU caching with explicit dependencies such as episode, model revision, preprocessing and content hash. Supported values are image encodings, reference descriptors and graph templates. A disposer callback permits releasing GPU resources.

It refuses executable action catalogs, metric poses, collision approvals and policy actions. Similar-looking frames do not hit an exact-content cache. Approximate visual-feature reuse, policy-state caching, cross-frame scene caching and GPU scheduling are not implemented by this module.

`perception.schedule_perception` is an advisory scheduler: relevant stable tracks do not require category re-recognition at every frame; changed/ambiguous identities request recognition or inspection; geometry work is requested when the task needs it. It does not reduce safety sensing, bypass raw current RGB to the executive, or change the frozen policy's observation cadence. Candidate compute savings must be measured end to end, not inferred from an illustrative redundancy percentage.

Use the existing Action Compiler usage and duty-cycle measurements. Log monitor/SAM/grasp/executive inference separately from VLA-controlled action seconds. Zero VLA duty is not zero neural compute; a system that abstains from every action is not efficient task completion.

## 11. SAM 3 / 3.1 replay: actual API, deliberately limited deployment

The adapter is written against Meta source commit `2345a4ad109ac29c569da749c91d84f10dc08c40`, which has a shared `build_sam3_predictor` and request API for SAM3 and multiplex SAM3.1 [S3–S5]. It uses an explicit known-instance point prompt; it does not assume multiplex supports the base tracker's `add_mask` interface.

An operator-provisioned inference process must supply the exact local source, checkpoint and tokenizer paths and SHA-256 values, model version, explicit inference permission, and license acceptance. The loader checks paths/hashes and the pinned source before import. There is no automatic checkpoint download or dependency installation by this package. Use OS-level no-egress isolation; offline environment variables alone are not a security boundary.

The source's SAM3.1 loading path tolerates missing/unexpected state keys. Preserve and review load logs and check model coverage before qualification. A successful Python constructor is not proof that the correct tracker weights were loaded. Coverage was checked for the current private SAM3.1 loader, but not for this new prefix loader; qualification does not transfer automatically between them.

For causal evaluation, prepare an explicit chronological **JPEG prefix**, including only frames available by the target cutoff, with image hashes and original-evidence provenance. Native PNG-to-JPEG export is a deliberate derivative step; retain its parent evidence ID, source dimensions, conversion settings and resulting hash. The adapter never silently recodes the retained input. Every frame must share camera/dimensions and have current observation-role provenance. Resolution is bounded.

The experiment:

```text
bounded available prefix -> start_session -> point prompt at first frame
                         -> forward propagation -> publish last frame only
                         -> close_session
```

It rejects future/nonchronological frames, foreign cameras/episodes, hash mismatches, malformed outputs, mask geometry mismatches and duplicate tracker IDs. No tracked objects remains empty. Session/camera-local IDs are returned with the seed and source lineage; they must go through the association layer before becoming persistent entities.

**This is not a live incremental stream service.** A prefix session is reconstructed each call and may be slower than a resident causal tracker. Upstream internals can use all frames in the supplied prefix; only its tail is published, so never reuse retrospective intermediate masks as earlier online evidence. A hard process deadline is still required around GPU loading/inference. API requests and cleanup were tested with mocks, not loaded checkpoints.

Example only after independent provisioning/approval:

```bash
/path/to/isolated/python -m physical_harness.situated.sam_replay \
  --config /path/to/sam-prefix.local.json \
  --prefix /path/to/causal-prefix.json \
  --output /path/to/new-shadow-output \
  --allow-inference --licenses-accepted
```

No such inference was run to create or integrate this bundle. The template selects SAM3.1 but retains explicit local-path/hash placeholders and permission checks. The existing live worker uses lossless native PNG evidence and bounded incremental tracking; this adapter uses fresh JPEG-prefix sessions. Do not mix their latency results or claim that session-local IDs establish persistent identity.

The live frame-index correction passes a propagation bound of 1, clamps the available frame count, and checks that every raw-image read matches the emitted current index. A no-future-read check alone missed the earlier stale-frame bug. Prefix replay instead starts at index 0 with `len(frames)` as its positive bound, including 1 for a single-frame prefix. It publishes only the tail. This is deliberately a different contract, covered by mock regression tests, not a port of the private incremental worker.

## 12. Integration instructions

### Apply software only

Run from the unpacked bundle directory:

```bash
python apply_bundle.py --repo /path/to/physical-agent-harness --check
python apply_bundle.py --repo /path/to/physical-agent-harness --apply
cd /path/to/physical-agent-harness
python -m pytest -q tests/situated
python -m pytest -q
ruff check .
python -m physical_harness.situated demo --output runs/situated-fixture-new
```

The installer only adds listed, hash-checked overlay files and verifies the reused upstream interface blobs. It refuses conflicting destinations, path traversal and symlinks; identical reapplication is permitted. It does not use `git reset`, overwrite local edits, push commits, install models, or start work. A later documentation-only commit can still be compatible; changed pinned code requires an actual integration review, not `--force`.

### Reuse existing authority

The assembly order in a real deployment is:

```python
from physical_harness.situated import (
    CatalogActionHandler, GraphSession, Handler, IdentityLedger,
    enforce_extra_step_checks,
)
from physical_harness.action_compiler.runtime import ActionExecutor

# These are existing, reviewed deployment objects, NOT supplied test fixtures:
# journal, jobs, original_driver, qualified_situated_step_checks,
# selected_graph, registered_handlers, operator_budget, etc.

driver = enforce_extra_step_checks(original_driver, qualified_situated_step_checks)
executor = ActionExecutor(
    driver=driver, jobs=jobs, journal=journal,
    allow_simulated_motion=explicit_existing_motion_approval,
)
identities = IdentityLedger(journal)

# CatalogActionHandler receives resolve_intent and compile_current callbacks.
# The latter returns a current existing Catalog reviewed for this Basis.
# Its execute callback is the SAME executor above, never another nested
# HybridExecutor or a new owner of the same robot resources.
```

`GraphSession` handlers must be registered with matching READ/REASON/MOTION effects and deployment-domain qualification. Connect `quiescent` to the real existing ownership state, `stop` to the actual stop/queue-drain path, and `finish_allowed` to the independent task ledger. There is no library default that invents these qualifications.

**Mandatory for custom inspection/keypose programs:** install reviewers both in whole-program review and in `enforce_extra_step_checks`. The wrapper retains all original `StepReview` requirements and additionally rejects missing/unknown `situated_*` checks on every primitive. Do not accept a custom program using the original step reviewer alone just because its entry check passed.

For each node, construct the current Basis from the already validated sensor path, obtain entity-role bindings from the identity layer, and supply current Facts. The handler resolves a fresh catalog. The graph's historical JSON is not a source of current geometric candidates. Unknown/missing data should take a declared branch rather than force repeated identical model calls.

Provide monitor contexts to the **existing budgeted model transport**. This bundle does not choose an API model, price, endpoint, hosted vendor, or inference queue. Keep its provider reservation/settlement behavior unchanged. Use separate environments and bounded service IPC for model dependencies.

## 13. Updated experiment sequence — two lanes, one motion authority

Merge the software together; qualify the new behaviors separately. Do not restart an active native experiment merely to adopt this code.

### Lane A: no new robot motion

**A0. Integration regression.** Completed in the actual checkout; see [validation](SITUATED_EXECUTION_V2_INTEGRATION.md). Re-run after changes. The synthetic fixture is not a native trial.

**A1. Identity/permanence replay.** Use held-out episode prefixes with a clear identification followed by side views, hand occlusion, reappearance, and similar distractors. Compare independent detection, persistent semantics with the current tracker, and optional SAM prefix tracking. Measure same-instance correctness, ID switches, falsely retained identities, abstentions, label stability and mask/depth support. Score recognition and association separately. A retained correct label attached to the wrong object is a failure. Hand annotations may evaluate a replay but must not leak into causal online decisions.

**A2. Extend the selected SAM3.1 qualification.** Preserve the completed capacity and corrected sparse moving-shadow measurements [S9]. Next test longer streams, the 32-frame worker reset boundary, reacquisition, missing targets, strong view changes, occlusion and similar-object distractors. Multi-object evaluation is still pending. Check raw-image indices, mask alignment and identity separately; retain latency/memory accounting. Qualify the optional prefix loader separately only if needed for replay. Do not repeat model selection or compare JPEG-prefix latency with lossless live tracking as though they were identical workloads.

**A3. Visual-goal/monitor evaluation.** Construct causal command windows using actual timestamps and anchors. Label observable progress, target loss and completion independently; leave unobservable radio power unknown. Compare deterministic checks, a zero-shot local VLM, and the existing expensive verifier under declared budgets. Evaluate false completion, missed completion, abstention and trigger delay at episode/command level. Do not train or import a RoboMME-specific LoRA by default. Goal-reference images must never become success evidence.

**A4. Graph and direct-proposal evaluation.** Use current offline catalogs and allowed capabilities. Compare fixed graphs with model-authored bounded graphs; inspect missing/unknown branches and invalid repairs. Separately ask for anchor-relative keyposes with one permitted reference demonstration if appropriate. Measure semantic correctness, syntax, rejection causes, IK and whole-path feasibility where actual geometry exists. Unknown collision coverage stays unknown; offline feasibility is not executed task success. This uses paid calls only after explicit campaign approval.

### Lane B: preserve and extend the existing native sequence

**B0. Continue existing target acquisition / localization / clearance / stopping qualification.** The new graph and tracker do not relax those prerequisites. Preserve exploratory unknown-clearance diagnostics as a separately labeled lane; no automatic longer travel is authorized here.

**B1. Target-directed short handoff, then equal-total-action A/B.** Keep the same frozen policy and exact recipe; count acquisition, braking and policy exposure. Use balanced repeated conditions and report handoff-state distributions instead of demanding bitwise-identical render resets indefinitely. The previous approach-only pair remains operational evidence, not radio success or a treatment effect.

**B2. Qualified camera-view primitive.** Before active inspection, demonstrate a bounded collision-reviewed base/wrist view change and measured stop with all frames/steps counted. Establish that the new view actually supplies useful evidence. No detector score or stored class label supplies clearance.

**B3. Active identity resolution and arm staging.** Compare passive observation against one qualified information-gathering action. Only after that, qualify arm/torso staging and C-short/A/B/C under the existing policy-handoff envelope. Test identity loss and distractor cases, not just successful frontal views.

**B4. Useful manipulation with the same catalog.** Screen a few visually verifiable tasks and compare qualified parameterized primitives, the frozen policy, and bounded reviewed direct proposals. The fixed controller is the baseline; the graph should not quietly change its low-level recipe while claiming only a planning improvement.

**B5. Sparse executive and memory.** Compare fixed graph -> model-selected graph/repair -> optional fast branch selector, with the same capabilities and observation rules. Measure exceptions and actual task outcomes, not only fewer calls. Add causal memory comparisons only on a genuinely memory-sensitive task with useful motor competence. Identity persistence is a clearly declared state capability, not an undisclosed extra memory condition.

Only after competence is demonstrated should approximate reuse, aggressive frame thinning, async executive overlap or live multi-object multiplexing be promoted. Exact representation-cache savings can be measured earlier without changing action semantics. Action tokenizers/learned hand synergies remain future work, not new dependencies for R1Pro.

## 14. Validation scope and known limitations

See [SITUATED_EXECUTION_V2_INTEGRATION.md](SITUATED_EXECUTION_V2_INTEGRATION.md) for actual-checkout counts and commands. The original bundle author could not retrieve the full checkout and used byte-verified interfaces with test-only namespace shims. Integration now runs against the real repository without those shims, including additional WorldState/EventBus and single-frame-prefix regressions. The archive's original validation report remains historical provenance, not the current validation result.

The synthetic example uses real core orchestration classes with fake geometry and actuation in `fixture` domain. It is not a BEHAVIOR run. Model/SAM loading and results use mocks in tests. No GPUs, real policies, paid APIs, model training, checkpoint downloads or robot/simulator motion were used for integration. The full suite and Ruff results are recorded in the integration report.

Important deployment gaps remain explicit:

- Stable identity depends on a truthful association provider; software proof fields do not solve it.
- Candidate camera/EEF poses are not paths, collision certificates, or useful-view guarantees.
- SAM replay is not persistent online streaming; creating many prefix sessions can be expensive.
- Graph execution is sequential and node repair is limited; no concurrent actuator scheduling or arbitrary code patches.
- Native methods and GPU calls need external hard deadlines. Stop/observe cannot hide uncounted physical steps.
- Current geometry and model proposals can expire during cloud reasoning. No stale-evidence bypass is added.
- Semantic tool correctness and task verification are still empirical, independent evaluations.
- Current default domain is simulator-only; real hardware needs a separate reviewed deployment boundary.

## 15. Source ledger

**Repository facts used:**

[S1] Original bundle's reviewed commit and retained SAM3 result (not latest integration state):
https://github.com/AranKomat/physical-agent-harness/tree/1531ac983ebf142b4aca0b790538fff89330e3ef
https://github.com/AranKomat/physical-agent-harness/blob/1531ac983ebf142b4aca0b790538fff89330e3ef/docs/SAM3_RETAINED_TEST_20260922.md

[S2] Existing compiler and protocol records at that commit:
https://github.com/AranKomat/physical-agent-harness/blob/1531ac983ebf142b4aca0b790538fff89330e3ef/docs/ACTION_COMPILER_V1.md
https://github.com/AranKomat/physical-agent-harness/blob/1531ac983ebf142b4aca0b790538fff89330e3ef/docs/HYBRID_EXPERIMENT_SEQUENCE.md
The user's retained acquisition and target-handoff reports supply the operational findings; they are not independent replications by this implementation.

[S9] Newer integration-checkout SAM3.1 evidence:
[corrected incremental shadow run](SAM31_INCREMENTAL_SHADOW_20260922.md),
[capacity and timing](SAM31_CAPACITY_AND_TIMING_20260922.md), and
[latency path](PERCEPTION_LATENCY_PATH_20260922.md).
The integration preserves these records and the private live worker; no new GPU result is claimed.

**Audited external API basis:**

[S3] SAM README and shared version support:
https://github.com/facebookresearch/sam3/blob/2345a4ad109ac29c569da749c91d84f10dc08c40/README.md

[S4] Predictor request/propagation and prompt differences:
https://github.com/facebookresearch/sam3/blob/2345a4ad109ac29c569da749c91d84f10dc08c40/sam3/model/sam3_base_predictor.py

[S5] Explicit local versioned model builder:
https://github.com/facebookresearch/sam3/blob/2345a4ad109ac29c569da749c91d84f10dc08c40/sam3/model_builder.py

**Conceptual inspiration, not reproduced systems or guarantees:**

[S6] Physical Intelligence pi0.7 steerable/subgoal-conditioned policy:
https://www.pi.website/blog/pi07

[S7] GaP semantic skill-graph representation:
https://graph-robots.github.io/graph-as-policy/

[S8] RoboMME recent-observation / command-start monitoring pattern:
https://github.com/bingaochen/Astra-on-RoboMME/blob/main/examples/champ/input_contract.py

These references do not establish native R1Pro generalization. Implementation decisions, safeguards and proposed experiments in this handoff are this package's design, not claims those papers or systems tested the same configuration.
