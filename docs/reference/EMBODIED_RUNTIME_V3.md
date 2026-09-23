# Embodied Runtime V3 — implementation and research-agent handoff

**Prepared:** 2026-09-23.
**Repository:** `AranKomat/physical-agent-harness`.
**Reviewed base:** `10778390c24bf34b522ede0ac426a30e3a611913`.
**Bundle:** `physical_agent_harness_embodied_v3_20260923.zip`.
**Delivery:** additive code, tests, configurations and documentation. No existing source file is replaced. Nothing has been pushed to GitHub.

## 1. Read this first

This update implements the post-Situated-V2 design as **Embodied Runtime V3**. Its purpose is to connect the already-built pieces, not start another robot stack.

The final agreed division of responsibility is:

- **GPT is the recurrent embodied executive.** It sees compact current state and selected images, chooses tools/capabilities or a bounded keypose proposal, and participates at meaningful action boundaries. The goal is not to make GPT disappear.
- **GLM is read-only semantic discovery and memory annotation.** One asynchronous call returns attention and memory deltas. It does not choose or execute robot actions, declare a successful task, establish physical identity, or write current metric poses.
- **SAM, depth, tracking, localization and existing geometry/identity checks supply observation support.** They are not replaced by semantic confidence.
- **Classical controllers, guarded primitives, grasp generators and the optional frozen VLA execute below the existing ActionExecutor.** No second actuator owner is introduced.

This bundle contains working software for those boundaries, plus an audited cuRoboV2 planner adapter, a numerical visual-servo helper, a counted trajectory streamer, map tools, and reusable graph macros. **It does not contain a qualified R1Pro collision world, a ready R1Pro cuRobo robot configuration, a new SLAM system, a live force controller, or evidence of task-level improvement.** Those distinctions are part of the implementation, not optional documentation.

Merge the package together. Enable live/model/native paths separately after qualification. Do not restart an active experiment merely to apply it.

## 2. Preserve the current findings

The reviewed head includes the guarded full-description candidate-verification pilot. Preserve its category/color/subtype constraints, negative examples, source evidence, and qualification limits. A plausible red rectangular object is not automatically the requested radio. A remembered label can only attach to new geometry after a real association check.

Prior target-directed handoffs, SAM tests, pose caches, and source-binding audits are useful bounded evidence. They are not permission to loosen motion gates, read simulator object/world poses, add sensors to the challenge, or claim reliable manipulation. A completed graph, an admitted path, or a finite action vector is not radio activation.

This update does not change the matched A/B runners, frozen checkpoint/normalization/noise recipe, existing current-frame tracking corrections, stopping thresholds, native action accounting, existing memory defaults, or paid-call budgets. No model call or training is launched by installing/importing it.

## 3. Architecture

```text
Legal RGB-D/proprioception ─────── existing tracking/geometry/IdentityLedger
          │                                      │
          ▼                                      │
Bounded visual buffer + novelty trigger           │
          │                                      │
          ▼                                      │
One asynchronous guarded GLM call                 │
          ├── attention deltas                    │
          └── historical memory deltas            │
                    │                             │
                    ▼                             ▼
        Selective image-first inventory + compact semantic map
                    │
                    ▼
        Recurrent GPT embodied executive
        current facts + images + small options + optional retrieval
                    │
              select / retrieve / hold
              or separate bounded keypose proposal contract
                    │
        Fresh semantic rebinding when the old catalog has expired
                    │
                    ▼
      EXISTING Action Compiler / ActionExecutor / JobManager
                    │
         classical primitives / planner / optional frozen policy
                    │
         counted fresh feedback → independent verifier and ledger
```

Two output sections in one GLM response are **not parallel token generation**. The same call produces both, but normal structured-output validation waits for the complete response. Concurrency is between the read-only semantic worker and the rest of the runtime. Partial JSON never authorizes an action.

## 4. New code and actual scope

All new implementation is under `physical_harness/embodied_v3/`.

| Module | Responsibility |
|---|---|
| `contracts.py` | Evidence-bound image references, normalized image regions, dual-clock discovery requests/results, strict semantic value/retention records. |
| `keyframes.py` | Bounded visual buffer; camera/image/track/place novelty triggers; current plus complementary transient-frame selection. |
| `discovery.py` | Strict attention+memory output, existing-model adapter, one asynchronous worker with bounded pending/results, durable reservations, explicit no-call recovery. |
| `inventory.py` | Selective sightings/aggregates, hot/warm/cold views, operator pins, historical place annotations, canonical crops, optional retrieval ranking, guarded entity links. |
| `regions.py` | GLM coarse box → source-preserving crop or source-frame SAM seed; current-mask association checks. |
| `maps.py` | Existing-map projection, cost-aware A*, semantic frontier ranking, persistent exploration visits, room/entity/frontier summary, opaque `MapTool` destinations. |
| `executive.py` | Recurring semantic-boundary scheduling; bounded context assembly; existing GPT transport; strict selection/retrieval/hold; explicit semantic rebinding; existing V2 keypose proposal mode. |
| `capabilities.py` | Immutable qualified graph macros, explicit promotion, current capability/role/precondition admission, six unqualified standard recipes. |
| `planning.py` | Named-joint planner contracts, trajectory validation, audited new cuRoboV2 API adapter and source-checkout verification. |
| `servo.py` | Bounded target-relative SE(3) setpoints; trajectory streaming under existing ownership, fixed-joint hold checks, counted settling and measured endpoint checks. |
| `inspection.py` | Numerical next-best-view proxy scoring using observed point projection, visibility queries, view diversity and travel cost. |
| `monitoring.py` | Existing monitor/advisory results → appropriate executive events, never task truth. |
| `cache.py` | Exact-dependency historical/representation cache over existing Situated cache. No cached actuation authority. |
| `metrics.py` | Explicit input/cache/output/reasoning/image/latency/cost receipts, unknown-value accounting, exact-byte repetition statistics. |
| `sensors.py` | Dormant future sensor descriptors and source-preserving foveated request hooks; extra BEHAVIOR sensor channels rejected. |
| `integration.py` | Main-writer discovery coordinator, current-versus-remembered identity view, optional existing-driver planner routing and added native checks. |
| `demo.py`, `__main__.py`, `__init__.py` | Inert imports and an explicit synthetic end-to-end fixture. |

The existing Situated identity, visual-goal, graph, motion, and monitor implementations remain the source of those contracts. Existing Action Compiler grasp/contact generation, GraspGenX provisioning, receipts, actuator ownership, and neural-control-duty metrics remain intact.

## 5. Apply and test

Unpack the ZIP into a separate directory. Inspect its installer/manifest before applying.

```bash
python apply_bundle.py --repo /path/to/physical-agent-harness --check
python apply_bundle.py --repo /path/to/physical-agent-harness --apply

cd /path/to/physical-agent-harness
python -m pytest -q tests/embodied_v3
python -m pytest -q
ruff check .
python -m physical_harness.reasoning demo --output /tmp/embodied-v3-demo-new
```

The installer compares reused interface Git-blob hashes, checks every payload SHA-256, rejects conflicting destinations and symlink/path escapes, and only adds new files. An identical second application does not replace anything. It rolls back files it created if an in-process write fails. It is not a signed supply-chain attestation or a power-loss-atomic repository update; a crash lock must be inspected rather than blindly removed.

A conventional new-files-only patch is also included. Use the guarded installer in preference to bypassing interface checks. If the research repo has moved forward and a relevant interface changed, re-audit that interface and adapt the integration; do not simply weaken the manifest.

Core new modules use standard-library code plus dependencies already used by the repository's dev environment (`numpy`, `Pillow`, `jsonschema`, `networkx` in tests). Tests mock the cuRobo tensor/API boundary and do **not** require Torch or cuRobo. The real planner path requires an independently provisioned compatible GPU environment.

## 6. Integrate semantic discovery

### 6.1 Source references and clocks

Construct `FrameRef` from an existing validated `Basis`, a retained asset ID, content hash, camera, dimensions, and **actual wall availability**. A crop keeps the parent ID and exact normalized ROI. Source bytes must match before model submission.

`sim_time` and monotonic wall time are distinct. Delayed inference uses both: it cannot appear at an earlier executive cutoff merely because the simulator was paused. All wall values in a run must share the same clock origin; remote services must report elapsed durations or use an audited clock mapping. A machine reboot/new run cannot silently reuse old monotonic timestamps as current.

Do not pass outcome-reference or generated images as fresh observations. Existing visual goals remain separately typed. Old canonical imagery is allowed only as explicitly historical context.

### 6.2 Model adapter and one-worker discipline

Reuse the existing guarded model object (`JsonModel` or the approved experimental transport) and its budget journal. Supply an image loader returning **actual `ImageInput` bytes and metadata**, not a filename masquerading as an image.

```python
from physical_harness.perception.discovery import AsyncDiscovery, ExistingModelDiscovery
from physical_harness.reasoning.executive import ExecutiveCadence
from physical_harness.core.coordinator import DiscoveryCoordinator
from physical_harness.world.inventory import SemanticInventory
from physical_harness.perception.keyframes import SemanticKeyframes

# guarded_glm, load_image_input, journal and run_clock come from the existing host.
semantic_adapter = ExistingModelDiscovery(guarded_glm, load_image_input)
worker = AsyncDiscovery(
    journal=journal,
    invoke=semantic_adapter,
    model_name=guarded_glm.name,
    enabled=operator_approved_semantic_inference,
    max_jobs=approved_semantic_job_cap,
    clock=run_clock,
)
inventory = SemanticInventory(journal)
cadence = ExecutiveCadence()
coordinator = DiscoveryCoordinator(
    journal=journal,
    keyframes=SemanticKeyframes(),
    worker=worker,
    inventory=inventory,
    executive_scheduler=cadence,
)
```

`observe(ViewSample, ...)` submits only after novelty. `poll(current=..., now=..., task_revision=...)` runs on the main writer and commits historical results. It does not move the robot or mutate IdentityLedger/metric state.

There is one active call, at most one pending request (newer pending work supersedes older pending work), and bounded completed results. Every admitted request is durably reserved before transport. No failed/ambiguous call is automatically retried. Superseded-before-call requests are still visible in job accounting, but are not fabricated provider usage.

A Python thread cannot forcibly interrupt a hung native/HTTP callback. The existing transport must enforce a hard deadline, normally in a supervised process. `close()` reports failure to stop; it does not pretend a hung thread was killed. Do not spawn replacement workers indefinitely. `recover_completed_results()` can explicitly recover already-journaled results without any provider calls; commit them at their actual recovery/publication time.

### 6.3 Semantic contract

One call returns `updates`, `attention`, and a bounded `scene_summary`. Default caps are four updates and two attention events. It can reference a supplied region or propose a coarse normalized box on a supplied image. It cannot output XYZ, robot actions, arbitrary new inventory IDs, or execution approvals.

The full requested description remains present. Color/subtype/spatial attributes cannot be dropped just to shorten context. Existing full-description qualification stays authoritative.

A `known_id` from GLM remains an association **hypothesis**, not an identity update. `recognized` is the model's semantic interpretation, not an authoritative fact. Apparent disappearance in one view is not evidence of relocation.

The default novelty policy considers new cameras, image-thumbnail changes, camera displacement/rotation, new tracks, important lost tracks, new places, and explicit executive requests. A small minimum interval limits thrashing; it is not a fixed periodic semantic sampler. The buffer can recover some brief views, not guarantee complete event recall. Tune thresholds on held-out traces and log omissions.

### 6.4 Coarse box to tracking

`BoxSeed.sam_prompt()` converts normalized xyxy into the SAM API's normalized xywh. **The seed must address the original source frame in the same camera/session.** Never paste a four-second-old box onto a new image. Replay a causally available source prefix or use a qualified current re-grounding path.

`crop_source()` stores an actual PNG through the existing asset writer and retains its parent. A crop is evidence for future reinterpretation; it is not a new independent observation.

`require_current_tracking()` only validates lineage and an external association result. It returns no pose/identity/motion authority. Promote a sighting to an existing entity only through `SemanticInventory.link_entity()` plus a qualified sighting-to-current-instance association and the existing IdentityLedger binding.

## 7. Selective image-first inventory

The inventory is a semantic retrieval/attention projection over the **existing Journal**, not a replacement WorldState. It contains:

- transient views handled by the short buffer;
- historical sightings or aggregates, optionally linked to a qualified entity;
- hot/warm/cold derived views, with bounded capacities;
- original image/box metadata and a few complementary canonical views;
- current-task/future/landmark/novelty/uncertainty value hints;
- an optional historical place annotation.

The rank is an explicit heuristic, not a calibrated probability or universal utility function. Current-goal relevance is discounted after the goal changes. Safety/held/user-requested pins are runtime/operator decisions; a model cannot invent them. If mandatory pins exceed capacity, fail rather than silently evict them.

Demotion removes items from prompt/tracking priority without deleting the underlying journal/evidence. The archive itself is bounded and requires explicit run rotation/storage management when full. This is not unlimited retention. No retention decision may prune obstacle sensing, emergency monitoring, or the raw safety path.

Canonical selection uses source content, quality and diversity of **measured viewing directions** in named frames. It does not guess an object's front/back. All submitted candidates remain in historical records even if only some are selected for hot context. `add_views()` requires a separate association check for each added view.

Retrieval uses structured place/cutoff filters and lexical matching. Optional externally computed embedding scores can rank authorized candidates; no CLIP/SigLIP model is loaded. Embedding output is neither identity nor geometry. Exact-byte caching is not cross-frame visual-feature reuse.

## 8. GPT stays in the embodied loop

`ExecutiveCadence` wakes for primitive completion, meaningful discovery, target loss/reacquisition, new candidates, verification, unexpected change, graph judgment and explicit requests. It ignores routine progress ticks and coalesces pending events. The local controller/safety path never waits for GPT.

`build_context()` requires the goal/subtask, held objects, hard constraints, unresolved failures, robot state, current compiled facts, current eligible options and current imagery. Relevant historical crops, map summaries, world deltas and prior attempts are optional additions. It only trims items explicitly marked optional and reports omissions. If critical context cannot fit, it fails instead of hiding it.

Defaults are limits, not a demonstrated optimum: 20,000 metadata bytes, four images, four million image pixels, and an optional model-specific token count capped at 8,192. No `characters/4` estimate is used as an image-aware token counter. The existing provider still owns exact model-specific token/spend accounting.

`ExecutiveSession.decide()` reuses the guarded transport, yielding only a offered-option selection, a retrieval query, or hold. Retrieval is fulfilled by the host's existing image/history tools; it is not an arbitrary file/URL reader. A retrieved crop remains historical in the next packet.

`propose_keyposes()` is an alternative single-call output contract at a boundary where novel bounded movement is the actual question. It reuses **Situated V2's** `PoseAnchor`, `MotionLimits`, schema, and `motion_program`, with no prerequisite GLM action selection. It returns a **source-bound proposal**; it does not execute or refresh it. Contact, force, or arbitrary joint control is not opened up. An expired keypose proposal must be regenerated/re-grounded through an independently qualified path, not retimestamped.

### The essential slow-reply fix

A four-second GPT response often outlives a two-second metric catalog. V3 does **not** stretch the old catalog TTL. Before executing a selected option, `execute_selection()` requires:

1. a freshly observed `Basis` and a new current catalog;
2. an unchanged task revision and compatible robot/localization/execution frame;
3. exactly one current candidate with the same semantic intent;
4. an external `RebindReview` establishing the same goal, physical instance, affordance and constraints, permitted geometric change, and no relevant contradiction;
5. the normal existing ActionExecutor's full and per-step review.

No unique match means no action. There is no closest-pose substitution, matching by label alone, or automatic fallback to the VLA. The decision is reserved in the journal before execution and cannot be used twice. This is a semantic re-grounding boundary, **not a stale-state bypass**.

The host implements real association/rebinding checks. All-true test checks are forbidden in native use. If equivalent re-grounding cannot be established, ask for a fresh decision or observation. This conservative outcome is preferable to making an old coordinate look fresh.

## 9. Compact semantic maps and navigation tools

V3 projects existing occupancy/topology/identity/coverage stores rather than installing new SLAM.

`NavigationGrid` is an immutable snapshot of known cells and already-footprint-inflated free cells, resolution, frame, source basis and optional map bounds. `shortest_path()` implements deterministic four-neighbor cost-aware A*. Unknown cells are never a shortcut. Frontier reachability is computed in one breadth-first expansion, not a separate search for every cell.

`rank_frontiers()` combines an externally supplied semantic relevance hint with observed unknown-boundary count and path cost. This is a transparent heuristic, **not an implementation or reproduction of VLFM**. Exploration visits persist across calls but do not cross a localization-origin change.

`semantic_map_view()` supplies rooms, current place, gateway states, coverage, known inventory and a small frontier list. An explored fraction is only reported when the region denominator is known. No invented “87% explored.” Door usability requires both an observed-open state and a separate freshness check; it is still not collision permission.

`entity_destination()` resolves a reachable approach region rather than the occupied object center. A last-known object location is only a **search-region hint** and requires reacquisition. `place_destination()` accepts a measured local place-entry anchor from the existing resolver. `MapTool.select()` accepts an offered destination ID and returns a current path proposal for the existing navigator.

This does not repair the older `OccupancyMap`'s restricted camera convention, certify all height layers, supply floor support, handle arbitrary roll/pitch, or prove full-body/payload clearance. The live map producer must satisfy its geometry contract. A local observed map suffices as a representation; no complete environment simulator or pre-map is required. Current execution domains remain fixture and BEHAVIOR simulation, not certified real deployment.

## 10. Classical planner and servo integrations

### 10.1 Audited cuRoboV2 API

The implemented adapter is **not** the old `MotionGen` API renamed. It follows the inspected `NVlabs/curobo` revision `78fd485fa82d9b9a063fb4985e371814587e666a`:

```python
from curobo.motion_planner import MotionPlanner, MotionPlannerCfg
from curobo.types import GoalToolPose, JointState

# Planner construction and scene/robot provisioning are operator-owned.
# V3 adapter uses:
result = planner.plan_pose(goal_tool_pose, start_joint_state)
trajectory = result.get_interpolated_plan()
```

It uses the inspected goal tensor layout and **wxyz quaternions**, requires one explicitly configured tool frame, exact named-joint order, exact interpolation/control dt, and a current scene-install receipt. The provisioned source checkout and loaded module location are checked. Deploy trusted code read-only; runtime integrity checks do not defend against arbitrary concurrent code modification.

`PlanRequest` includes current joints, fixed joints, actual joint/velocity/acceleration limits, target TCP, scene evidence/digest, robot-configuration digest, sample budget and control dt. `JointTrajectory.validate()` checks initial position, limits, sampled velocity/acceleration and rest boundaries. It does not prove swept collision, friction, tracking stability or task success.

The operator-supplied scene callback must really update the collision environment, full robot and payload, fixed joints and tool/base transforms. A receipt is only useful if that implementation is qualified. No R1Pro robot configuration or ESDF is synthesized from a string. The upstream grasp example disables finger collisions; **this adapter intentionally does not call `plan_grasp()`** or disable fingers to obtain a passing plan.

`attach_free_space_planner()` routes only `STAGE`/`RETRACT` `MOVE_EEF` through this planner. Grasp/contact/policy steps retain their existing path. Apply `with_planner_requirements()` to programs before creating their reviews/catalogs and `enforce_embodied_checks()` to the driver; all four added planner/scene/hold/timebase checks are mandatory, including per-step enforcement.

cuMotion is an alternative future provider of the same `PlanRequest`/`JointTrajectory` boundary, **not a second implemented adapter in this bundle**. No automatic legacy/V2/cuMotion fallback is installed.

### 10.2 Native counted trajectory streaming

`TrajectoryStreamer` runs under the **existing** Driver/ActionExecutor owner. Its port must provide:

| Port call | Required semantics |
|---|---|
| `observe(deadline)` | Current `JointSample`; does not advance physics. |
| `check_segment(request, from_q, to_q, sample, deadline)` | Actual current swept-collision/kinematic check; unknown rejects. |
| `command(request, q, sample, deadline)` | Exactly one counted native control tick; return fresh measured joints and fixed-joint holds. |
| `settle(request, sample, remaining, deadline)` | Bounded counted braking/settling samples. No hidden ticks. |
| `stopped(sample)` | Independent measured stopping. |
| `endpoint_reached(request, sample, deadline)` | Measured FK/TCP confirmation of the requested endpoint. |

The streamer validates controlled/fixed joint order, hold drift, tracking, source continuity, deadlines, cancellation, and counted final observations. Uncertain command completion raises to the outer fault-latching executor. A timeout cannot release ownership or silently switch controllers. Callbacks require their own hard deadlines.

### 10.3 Visual servo

`VisualServo` is a numerical bounded SE(3) setpoint generator, not a new neural policy. It consumes fresh current target-relative geometry and measured TCP pose, preserves instance association, limits each translation/rotation step, bounds total correction path and target jumps, requires repeated convergence, and stops on target loss.

Its speed is configured; **no achieved high-rate robotics performance is claimed**. The native adapter must solve IK, review the swept setpoint, execute and measure it. There is no force/impedance controller or pressure/contact inference hidden here. Use existing contact primitives for actual interaction.

## 11. Inspection, macros and monitoring

### Inspection

`assess_views()` adds concrete numerical scoring to existing Situated `InspectionCandidate`s. It projects observed cloud points into candidate cameras and reports field-of-view coverage, supported versus unknown visibility, projected area, measured-view novelty and travel cost. Missing visibility/feasibility providers produce diagnostic-only candidates, not eligible hints. The score is an information-gain **proxy**, not a learned estimate or proof that a new view will identify the object. It does not reconstruct unseen shape or infer semantic “front.”

The existing inspection execution still requires calibrated camera-to-body kinematics and native motion qualification. Reaching a viewpoint is not satisfying the information goal.

### Reusable graph macros

Six versioned recipes are provided: `go_to`, `inspect`, `pick`, `place`, `press`, and `pull_prismatic`. They are semantic graphs over registered handlers, not saved joint trajectories. Coordinates and entity instances are late-bound to current observations. The registry stores explicit operator promotion against exact graph/deployment fingerprints, then requires current capabilities, facts and unambiguous role bindings before returning a graph.

Promotion metadata is not current availability. Templates have **no promotion by default**. Recorded software/replay tests cannot authorize native motion. The independent ledger passed to GraphSession must be scoped to the macro's declared postconditions; a global unrelated task-complete flag is not enough. Existing GraphSession budgets, failure behavior and no-code-generation rules remain in force.

No generic hinged-door, elevator, cloth-folding, hand-synergy or dexterous-hand capability is invented. Those mechanisms need actual qualified implementations. A graph fragment can be frozen as an unqualified artifact; success counts do not auto-promote it.

### Monitors

Existing deterministic and learned monitor results map to semantic executive events. Routine progress may continue silently; arrival/primitive completion, failure/loss and verifier uncertainty can wake GPT. Learned completion remains advisory. This package neither retrains a monitor nor changes the independent task ledger.

## 12. Compute and future sensors

`ComputeLedger` records actual or explicitly unknown usage: input/cache/output/reasoning tokens, image IDs/content hashes/pixels, model role, latency breakdown and cost. Reasoning is not added to output again when it is already included. Concurrent wall-time sums are not episode latency. Newly seen image bytes are not a measurement of novel semantic information.

Use existing policy duty-cycle/DOF-time and measured energy integration alongside these records. Zero VLA steps is not zero neural compute. GraspGenX, perception, GLM and GPT may still be expensive. No model prices or vendor speedups are hardcoded.

`SemanticRepresentationCache` only reuses exact dependencies for image/embedding metadata, historical annotations and map summaries. It is **not neural feature-cache surgery across similar frames**. Cached annotations retain their original source; repeated reuse is not independent evidence. It does not cache current poses, trajectories, collision approvals or task completion.

Foveation and force/tactile/LiDAR descriptors are future interface boundaries only. Current foveation means a source-preserving crop or a separately qualified closer view, not invented optical resolution. Extra sensor inputs remain rejected in BEHAVIOR. Existing RGB-D-derived geometry remains the legal source; verify the actual challenge track rules before a submission.

## 13. Experiment sequence after integration

Do not treat this handoff as permission for new spend, native motion, downloads, or relaxed gates. Freeze the experiment version/configuration first.

### Lane A — no-motion integration and retained-data work

1. Run the targeted suite, the full actual repository suite, Ruff, and the synthetic CLI. Preserve the original experiment outcomes and sources.
2. Replay retained discovery packets through the strict contract and inventory. Test prompt/output-cap violations, duplicate/late/out-of-order responses, old-task attention, source crops, and loss of identity. Verify no writes to current geometry or actuation records.
3. With an explicitly approved GLM budget, compare bounded delta output against existing room inventory calls on held-out views. Measure important-object recall, attribute preservation, uncertainty, packet validity, provider latency/usage and omitted transient views. Keep identity/localization evaluation separate from semantic naming.
4. Test coarse-box → original-frame SAM seed → current-mask association using the **existing corrected tracker**. Preserve reset/camera/session IDs. An old box on a new frame is an invalid test, not a tracker failure.
5. Test hot/warm/cold retention and image-first retrieval on changing goals. Include duplicate-looking objects, clutter aggregates and held/active-object pins. Replaying all prefixes of one trace is not many independent trials.
6. Build compact map views from retained legal geometry. Check map frame/epoch, occupancy assumptions, unknown cells, gateway age and coverage denominators. Test semantic frontier ranking without moving.
7. Compare GPT decisions using the same current images with compact versus existing context; measure valid selections and independent semantic/physical appropriateness. Do not score schema validity as task success. Test slow-reply semantic rebinding on changed/ambiguous targets.
8. Provision cuRoboV2 only with separate authorization. Test actual R1Pro robot/tool/fixed-joint configuration and legal collision scene offline. Compare returned trajectories against independent FK/swept checks. Do not replace failures with an empty collision world.

### Lane B — existing native qualification, unchanged authority

9. Continue the existing target-acquisition/transit/localization/clearance/stopping gates. V3's map or semantic memory does not complete them.
10. After those gates, compare the existing frozen-policy handoff conditions using the predeclared balanced/repeated design and actual handoff-state distributions. Do not demand pixel-identical natural rollouts indefinitely or cherry-pick starts.
11. Qualify short collision-reviewed free-space arm trajectories and fixed-joint holds, including cancellation/unknown stop. Then qualify target-relative servo separately. Report setup, simulation and wall-clock latency separately.
12. Compare existing staging versus the new planner behind the **same** action interface, budgets and independent verifier. Only then compare recurrent GPT + compact context against existing executive routing.
13. Promote one macro after genuine repeated native evidence and explicit review; test reuse in a changed layout with late-bound geometry. Adding a graph entry does not establish generalization.
14. Evaluate memory on a genuinely memory-sensitive task only after useful motor competence. Measure successful-task cost/time/quality, not token savings on failed tasks alone.

The smallest useful next result is a current, evidence-bound GPT selection from a compact context, followed by an independently admitted native action—not another broad architecture expansion.

## 14. Validation and what was not run

See `VALIDATION_REPORT.md` in the bundle for the final counts and exact scope. The author ran new targeted tests, installer tests, a synthetic end-to-end example using the real Journal/JobManager/ActionExecutor interfaces, and package application checks. Network/DNS restrictions prevented a complete repository checkout and installing Ruff. The local test workspace used uploaded earlier overlays plus byte-verified current reused modules, with implicit namespace-package roots for missing upstream packages.

**The full current repository suite and Ruff were not run by the bundle author.** They must run in the research agent's actual checkout. No native BEHAVIOR episode, live GLM/GPT call, real SAM/GraspGenX/cuRobo inference, training, hardware action, or GitHub write was performed. Mock tensor/API tests check the inspected cuRobo contract, not the real CUDA library or robot.

## 15. Sources and provenance

The code extends the user's existing architecture and requested backlog. It does not claim to reproduce external papers' success rates. Source references below support interface/design provenance, not performance of this implementation.

- **S1 — reviewed project baseline and latest candidate-description work:** `https://github.com/AranKomat/physical-agent-harness/tree/10778390c24bf34b522ede0ac426a30e3a611913`.
- **S2 — existing action catalog, guarded executor and ownership:** `physical_harness/action_compiler/{types,compiler,runtime,primitives}.py` and `physical_harness/core/jobs.py` at S1.
- **S3 — existing Situated identity/graphs/visual goals/keyposes/monitor/cache:** `physical_harness/situated/` at S1. Do not replace the corrected private live SAM worker with the earlier offline prefix adapter.
- **S4 — existing provider accounting and actual image boundary:** `physical_harness/experiment/{models,journal,media,validation}.py` at S1.
- **S5 — exact inspected cuRoboV2 API:** `https://github.com/NVlabs/curobo/blob/78fd485fa82d9b9a063fb4985e371814587e666a/curobo/examples/getting_started/motion_planning.py`; inspected file blob `7d8821391c61ae9185ebc4a922607f817ed8956c`.
- **S6 — official challenge boundary to recheck before submission:** `https://behavior.stanford.edu/challenge/evaluation.html`.

Code licenses, model weights, robot assets and datasets have separate terms. This bundle includes only new authored overlay files and its documentation/tests. It does not redistribute the copied upstream source used in the author's partial test workspace, model weights, private observations, credentials, or licensed robot assets.

## 16. Explicit non-goals

No GLM tactical controller. No Jev dependency. No CLIP/SigLIP semantic prescreener. No new GaP runtime. No new VLA/tokenizer training. No generated-world-model visual-goal service. No generic real-robot deployment. No mandatory dense map or complete simulator. No privileged benchmark state. No automatic macro self-modification. No collision/identity/success inferred from model confidence. No claimed 2–5× speedup before measurement.

The complete numbered-backlog mapping is in `docs/EMBODIED_RUNTIME_V3_COVERAGE.md`: each of the 50 requested entries is marked **new software**, **existing feature reused**, **qualified-port integration**, or **explicitly deferred**. This prevents brainstormed future sensors/controllers from being mistaken for deployed capabilities.
