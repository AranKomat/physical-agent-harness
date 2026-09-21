# Physical Agent Harness — Geometry and Action Compiler V1

## Research-agent handoff

**Prepared:** 2026-09-21. **Reviewed public base:** `ffdd3bb8da9bfffb533cb5b77cd6ea88752c5a14` in `AranKomat/physical-agent-harness`.

**Deliverable:** a unified, additive implementation of the “Minecraftification” interface: legal sensor evidence → object/part geometry → candidate interactions → feasibility-reviewed programs → small action-ID catalog → bounded execution → independent verification. This is not just a GraspGenX wrapper.

**Deployment state:** opt-in software for offline, shadow, and subsequently qualified simulator experiments. It does not make R1Pro motion qualified, enable an ongoing campaign, train a policy, download weights, call GPT, or establish task success. Merge the package in one change; enable native capabilities only when their evidence is established. The whole implementation is present, but a missing real collision/contact/actuation port is not replaced by a fixture.

## 1. Preserve the current experiment and its findings

The current project uses BEHAVIOR/R1Pro, legal RGB/depth/proprioception, one frozen multitask motor where practical, a sparse GPT executive, independent post-action verification, current WorldState and causal multimodal memory. No new training is authorized by this handoff. Benchmark-training overlap is disclosed rather than described as held-out generalization.

The latest public native report is more restrictive than “a wheeled robot can simply navigate.” A small forward pulse passed one ordinary radio-start response diagnostic; reverse tracking and yaw tracking failed, and camera-specific odometry estimates disagreed. The report explicitly says not to claim a qualified A-short/B-short handoff. Those gates remain in force. Infrastructure recovery after an instance restart was not a new motion qualification [S1].

The package does not touch the public matched-radio runner, retained outcomes, campaign ledger, private receipts, policy serving recipes, memory defaults, or native qualification thresholds. Do not restart an active experiment to incorporate it. Do not interpret a successful synthetic fixture, closed transport, or finite 23-D vector as successful manipulation.

## 2. Design decision: hide metric actuation, not uncertainty

The executive should choose **what interaction is useful**, not synthesize meters, Euler angles, forces, joint vectors, or controller code. A proposed object part is still a perception hypothesis. A generated grasp score is not a calibrated probability or a collision certificate.

```text
Existing legal RGB + depth + proprioception
            |
Existing identity/part grounding + calibrated camera geometry
            |
Observed object/part point clouds and surface patches
            |
Candidate generators
  analytic grasp | GraspGenX | contact | explicit pose | policy | inspect
            |
Parameterized program compiler
            |
Robot-specific whole-program feasibility review
            |
Current SceneView + small catalog + current RGB/derived candidate overlay
            |
Existing GPT executive: {catalog_id, action_id}
            |
One-shot resolver + fresh re-review + shared whole-robot lease
            |
Bounded local/native primitive execution
            |
Fresh evidence → existing independent verifier → existing ledger
```

A typical selection is `grasp(object_7, handle_candidate)` expressed as an opaque ID from the current catalog. The underlying candidate owns the TCP pose, approach, opening, source frame, gripper identity, and trajectory requirements. The selection tool accepts **only** `catalog_id` and `action_id`. Extra fields, arbitrary IDs, stale scenes, safety flags, Python, and metric overrides are rejected.

This does not prove that GPT selects the correct object or part. `evaluation.score_selection` explicitly separates valid tool use from correct semantic selection. A schema-valid but wrong grasp is still wrong. Keep current RGB available; do not turn uncertain perception into an apparently authoritative game-state oracle.

## 3. Package contents and actual scope

All implementation lives in the new `physical_harness/action_compiler/` package. Existing source files are not replaced.

| Module | Implemented responsibility |
| --- | --- |
| `types.py`, `serde.py` | Immutable SE(3), evidence/calibration/embodiment basis, gripper profile, proposals, programs, reviews, strict finite JSON. |
| `geometry.py` | Calibrated masked-depth deprojection, optical-Z versus ray-range distinction, partial point clouds, robust-enough planar diagnostics, pose/frame composition. |
| `scene.py` | Stateless current object/part summary and action catalog; no new persistent world model. |
| `proposals.py` | Analytic parallel-jaw grasp hypotheses, planar press, explicit linear pull, navigation/staging/place/retract poses, passive inspection, explicit frozen-policy candidate, diversity and semantic-region filtering. |
| `graspgenx.py` | Lazy, source-pinned adapter to the actual audited upstream GraspGenX API; local asset integrity checks and bounded proposal output. |
| `worker.py`, `worker_client.py` | Supervised local JSON-lines inference process, capped requests/results, correlated IDs, deadlines, no automatic retries. No actuator authority. |
| `primitives.py` | Bounded templates for all nine verbs; intermediate measured grasp/release checks and explicitly supported constraints. |
| `compiler.py` | Feasibility review, blocked/eligible catalog, exact-source resolution, small structured tool schema. |
| `cartesian.py` | Closed-loop bounded SE(3) transit and guarded linear press/pull over real native IK/codec/collision/sensor ports. |
| `runtime.py` | One-shot journaled execution, shared ownership, per-step review, stop/receipt validation, persistent fault handling, no semantic-success promotion. |
| `integration.py` | Existing Snapshot/Action/NativeBindings/SkillReceipt adapters, source-faithful frozen-policy adapter, reset-aware primitive dispatcher. |
| `attention.py` | Semantic-intent queue and event-triggered executive wake decisions; no stale metric-action queue. |
| `metrics.py`, `evaluation.py` | Receipt-derived policy duty and DOF-time metrics, separate auxiliary-model usage, optional measured device-energy integration, semantic tool-choice scoring. |
| `overlays.py`, `fixture.py`, `__main__.py` | Evidence-bound candidate markers and explicit synthetic end-to-end fixture. |

No full-scene meshing, detector, semantic segmentation model, collision engine, R1Pro actuator codec, force sensor, dexterous-hand controller, gait policy, or general hinged-door solver is hidden inside this implementation. Those require their own actual, reviewed adapters. “All at once” means the complete software path, not fabricated native capabilities.

## 4. Sensor and geometry boundary

Start from the **existing validated Hybrid Snapshot**. `basis_from_snapshot` adds explicit execution epoch, robot/calibration fingerprints and evidence handles. Basis equality is strict: episode, source observation, capture time, local-frame epoch, geometry revision, execution epoch and embodiment must match for selection and admission.

Object and part masks must come from permitted RGB-based perception or clearly separated annotation fixtures. Do not feed simulator segmentation, object poses, object meshes, hidden predicates, global robot pose or future observations into the online compiler. A local point cloud computed from allowed depth is different from reading the simulator's full-scene point cloud. Recheck official track rules before a submission [S2].

`deproject_masked_depth` requires calibrated intrinsics, explicit depth scale, a boolean mask aligned to the image, and a declared depth convention (`optical_z` or `ray_range`). It rejects inadequate support rather than fabricating a point. It preserves a bounded sample of visible surface points. A box center or one background depth pixel is not treated as a reliable contact point.

`fit_surface` rejects inadequate/degenerate/nonplanar support and reports a residual. Its normal is oriented using the camera position. It does **not** identify a button, infer a hidden object's shape, prove empty space behind a surface, or measure friction. Semantic grounding and contact feasibility are separate checks.

All poses use named frames and row-major 4×4 transforms in meters. The local map's +Z is not assumed to be up. Grasp lift and placement require an explicitly calibrated up direction and evidence. Preserve the exact camera-to-base/arm transform and epoch; do not equate camera pose with base pose.

## 5. GraspGenX: verified integration, not a gripper-name guess

The adapter was written against `NVlabs/GraspGenX` commit `b9429097728cb1c430dd78b92edf17ba318aad03`. Its README describes partial-point-cloud grasp generation conditioned on a gripper representation, and a workflow for adding a gripper from URDF/meshes, open/close configurations and swept-volume metadata [S3]. That is not evidence that a named real Galaxea gripper exactly matches the simulated R1Pro gripper.

The local `Gripper` profile pins joint names, actual open/closed positions, bounds, aperture, asset-manifest digest and **T_grasp_tcp**. The adapter converts upstream output using:

```text
T_frame_tcp = T_frame_grasp × T_grasp_tcp
```

The audited upstream sampler already restores translations to the input point-cloud coordinates. Do not add the object centroid again. Do not apply an inverse transform without an explicit frame derivation [S4].

The implemented upstream call is:

```python
GraspGenXSampler.run_inference(
    object_pc_float32, sampler,
    grasp_threshold=-1.0,
    num_grasps=64,
    topk_num_grasps=8,
    min_grasps=1,
    max_tries=1,
    remove_outliers=False,
)
```

This deliberately uses one bounded generation attempt, avoids implicit retry loops, and does not silently fall back between TensorRT/eager paths. Result matrices/scores are shape-checked, finite, bounded, and associated with the exact source basis and gripper. Empty output stays empty. Scores retain their uncalibrated provenance.

### Provisioning and isolation

Upstream import calls dependency setup that can clone assets/checkpoints [S5]. Therefore our package never imports `graspgenx` or Torch merely to expose the compiler. The explicit worker loader verifies paths, clean pinned source, selected checkpoint/config hashes, full selected gripper-file coverage, LFS materialization and the expected gripper fingerprint **before** importing upstream.

Both `GRASPGENX_CHECKPOINT_DIR` and `GRASPGENX_GRIPPER_CFG_DIR` are set to verified existing local directories before import. Use the separate, operator-provisioned inference environment and OS-level no-egress isolation. Environment variables are not a network sandbox; package code and checkpoint loaders remain trusted dependencies. Code, model, data and asset licenses are separate review items.

`configs/action_compiler/graspgenx-worker.template.json` is intentionally incomplete and cannot run unchanged. Fill it from audited local artifacts, not guessed joint values. `checkpoint_root` points at the selected directory containing `gen/` and `dis/`; `gripper_root` is the gripper-descriptions repository; `assets_dir` contains `x_grippers/<name>/`. Manifests are relative to the corresponding root. The manifest hash in the Gripper profile must equal `digest(gripper_manifest)`.

After explicit provisioning, license review and approval, the available worker command is:

```bash
/path/to/inference/python -m physical_harness.action_compiler.worker \
  --config /absolute/path/to/graspgenx-worker.local.json \
  --allow-inference --licenses-accepted
```

Do not run this during a native experiment merely because the package was merged. `GraspWorkerClient` starts only an explicitly supplied command. A timeout or malformed result poisons/reaps that inference channel; it never implies the robot stopped.

GraspGenX is still a learned grasp generator, including a diffusion component in the audited path. Zero VLA-controlled timesteps does not mean zero neural computation, negligible energy, or a tiny network.

## 6. What each compiled interaction does

**Navigate/stage/retract:** use observed, operator-generated target poses, not GPT-generated coordinates. Navigation requires localization, full footprint/payload clearance and qualified base response. Staging uses IK, swept collision and real holds. Existing Hybrid native callbacks may be reused; do not nest resource-owning executors.

**Grasp:** open → pregrasp → contact pose → close → measured-grasp check → short lift. The grasp check occurs before lifting. Aperture and frame conversion use the actual gripper profile. Partial geometry and a high model score do not establish force closure, friction, payload stability or reachability.

**Place:** verify held attachment → approach/support pose → open → measured release → retreat. The support region and payload clearance need independent evidence. A motion receipt does not create an `ON`/`IN` predicate.

**Press:** precontact → bounded low-speed line into the observed surface → release check → retract. The numerical Cartesian executor has a per-tick contact-corridor monitor and full swept checking. It is not force/impedance control and assumes no unapproved force channel. A correctly traversed distance does not prove electrical radio activation.

**Pull:** grasp an observed handle, establish attachment, then a short stroke along an independently established **prismatic** axis. Do not use it for a hinged door, threaded cap or unknown articulation without a different qualified primitive.

**Inspect:** passive current sensing only, zero motor steps. A moving scan requires a separately qualified motion action. A no-op capture is not automatically informative.

**Frozen policy:** one explicit candidate carrying the exact policy identity/recipe, not an automatic fallback when geometry fails. The original full action interface is preserved. The reset-aware dispatcher marks classical interventions; first entry, intervention or changed instruction drains stale queue/history/in-flight inference, while unchanged uninterrupted policy calls preserve their published temporal recipe. A reset must never reset simulator state.

Constraint names currently understood by the compiler are `keep_upright`, `avoid_rim`, `use_left_arm`, `use_right_arm`, and `no_base_motion`. They produce mandatory native review checks, repeated per step. Unsupported or contradictory constraints are rejected. Merely accepting the text is not implementing its physical enforcement; absent reviewers leave the candidate blocked.

## 7. Execution, clocks and research integrity

A generated proposal is not executable authority. `ReviewEngine` requires actual native reviewers for sensor lineage, robot model, codec, stopping, geometry, joint limits, IK, contact/attachment and applicable semantic constraints. Missing or unknown checks remain blocked. Every review is bound to the exact program, source basis and domain. Copying all-true fixture reviewers into `behavior_sim` is forbidden.

`ActionExecutor` re-observes and re-reviews before execution, then acquires the shared **whole-robot** JobManager lease and reserves the attempt in the existing Journal before any motion callback. Each primitive receives fresh per-step review, bounded deadlines/step budgets, and explicit stop/receipt checks. All braking/settling ticks are counted in the receipt. `stop` and `observe` cannot secretly advance simulation time.

One-shot selections persist in the existing journal. Repeating the same selected action is refused; repeated same-intent attempts have an explicit configurable cap. A failed primitive does not run the next primitive or switch to VLA. A lost/ambiguous receipt triggers stopping and a latched fault. Unknown stop retains resource ownership; reconstructing the Python object does not erase unresolved journal history. Qualification/evidence callbacks remain trusted native code, not security or physical-safety proofs.

**Paused simulator and GPT latency:** default freshness/catalog windows are short engineering bounds, not a qualified scheduling policy. An 8–20 s model call can outlive them. This implementation deliberately does not restamp old evidence, relabel a new capture as an old one, or bypass freshness. Use the repo's separate paused-world recapture qualification path before live GPT dispatch, or demonstrate that the configured timing contract is met. A strict rejection is preferable to silently acting on old metric candidates.

The intent queue stores **semantic goals**, not previous-scene coordinates. After a verified boundary, rebuild the next catalog from current sensors. A unique eligible candidate for the already-approved intent can proceed without another GPT call; ambiguity or failure wakes the executive. Only the existing independent semantic verifier/ledger should invoke queue advancement. Failed model outputs and candidate descriptions are not verification authority.

## 8. Integrating with the existing harness

Use one actuator-owning executor. `ActionExecutor` reuses the original `JobManager` and `Journal`; it is not a second persistent state/memory service. Reuse original non-owning native callbacks below it, and keep existing HarnessRuntime → verifier → ledger above it.

Recommended assembly boundaries:

1. Current legal capture → existing Snapshot → `basis_from_snapshot`.
2. Existing perception/grounding → entity and part masks → `ObjectCloud`.
3. Candidate generators → `compile_catalog` using actual native reviewers.
4. `SceneView(...).view()` and optional candidate overlay accompany current RGB; `Catalog.tool_schema()` exposes eligible ID choices.
5. `CatalogMotor.publish(catalog)` offers eligible actions under the existing action interface. Its `run_skill` returns the original strict three-field metadata receipt; observed goal predicates remain empty.
6. `PrimitiveDispatcher` sends classical steps to reviewed native handlers and policy steps to `FrozenPolicyPort`. Provide all primitive handlers named in the compiled programs or leave those programs unavailable.
7. Use existing verifier/ledger events for semantic completion, task progression and `IntentQueue.advance`.

`CatalogMotor.wrap_native` preserves the original observer and replaces only the opted-in motor/stop callables. It does not modify the matched-radio runner automatically. A dynamic catalog requires the operator integration to publish current `available_actions` before each executive decision and retain the same catalog until resolution. Do not leave both the original motor and the new dispatcher writable from unrelated tools.

`FrozenPolicyPort` preserves the full interface, identity and recipe, but the actual serving process must report the loaded identity and implement reset/drain acknowledgements. It wraps the original native callback, not another whole-robot resource-owning hybrid instance.

## 9. Metrics: make the simplification measurable

The Journal-based summary separates:

- validated native steps, classical steps and policy-controlled steps;
- policy-controlled simulated seconds and their fraction of recorded action time;
- policy DOF-seconds divided by total controllable DOF-seconds;
- motor policy calls, known/unknown policy-inference time, execution wall time;
- separately recorded grasp-generation, perception, executive and verifier calls;
- unclosed attempts, missing receipts, unresolved stops and faulted accounting.

Current policy use still owns the full normal 23-D interface; this package reduces *when* policy runs, not its internal action dimensionality. Missing data does not become zero cost. `energy_joules` remains unknown unless a real measurement is supplied. The optional power integrator computes whole-device energy for measured windows; it does not attribute shared-device energy to a model or infer savings from duty cycle. Report masks/point-cloud/model-generation work as well as VLA work.

The intent queue and event-attention controller reduce unnecessary executive calls; they do not turn safety monitoring off. The lowest competent qualified executor is useful, but the goal is task success and predictable control—not forcing neural duty to zero at any cost.

## 10. Experiment sequence and explicit stop conditions

Implementation is unified; qualification remains separable so failures have an identifiable cause. Use existing budget approvals. The following sample counts are proposed test sizes, not authorization to rent GPUs, call models or start motion.

**E0 — Software and merge.** Run package tests, the synthetic fixture, full repo tests and Ruff. Do not relaunch existing native trials. Treat failed guards or mismatched source hashes as a merge/audit task.

**E1 — Sensor/semantic candidate replay, no motion.** Use retained legal RGB-D snapshots from radio plus a visible rigid grasp task. Check camera/depth conventions, gripper frames, target/part localization, point-cloud coverage, grasp/contact candidates and feasibility rejections. Ground truth may be used only in a separate evaluator report. Start with a small frozen set, for example 10–20 observations. Retain empty/blocked cases in the denominator. Stop on wrong frame/scale/calibration rather than tuning a model around it.

**E2 — GPT tool-choice replay.** Supply the same current RGB/derived overlays/catalogs under a fixed prompt and model route. Prelabel acceptable semantic choices separately from model input. Test ambiguous parts, unsupported constraints, stale IDs, blocked actions, and missing evidence. Measure schema validity and correct choices separately. This is not executed grasp success and does not require GPT training. Do not pool development Codex calls with the performance API condition.

**E3 — Proposal backend comparison.** On the same frozen legal point clouds and actual gripper configuration compare analytic proposals with source-pinned GraspGenX. Measure proposal time, empty output, part-support, IK/swept-path rejection, diversity and memory use. No model inference was performed for this bundle. Do not credit a model score as simulated grasp success.

**E4 — Native local primitive qualification.** Resolve the current base-response/localization discrepancies before long navigation. Separately qualify small arm transit, actual gripper closure, measured grasp/release, and guarded contact monitoring. Unknown clearance, frame disagreement, wrong holds, failed stop or unexpected contact stops the trial. No automatic “try the policy instead.”

**E5 — Tiny ordinary-start grasp or contact episode.** Keep one rigid target and one frozen policy, no historical memory initially. Compare (a) frozen policy, (b) classical transit plus policy, and (c) candidate-conditioned parameterized primitive where qualified. Keep equal total native action ceilings for end-to-end comparisons. Equal-policy-exposure handoff diagnostics are separate and explicitly have unequal total horizons. Radio pressing may remain visually unverifiable; also choose a task with legal visible progress.

**E6 — Executive and sparsity.** Compare a fixed qualified executor/intent sequence with the same executor plus current-context GPT. Then compare per-boundary calls with the event/intent queue, retaining emergency/progress monitoring and identical allowed tools. Run a few ordinary starts after plumbing passes; one success is exploratory.

**E7 — Memory and longer tasks.** Only when execution is controllable, enable the already implemented causal memory on a genuinely memory-sensitive task. Reuse M0/M1/M2 rules. Do not add a new map or claim that radio-contact performance measures memory.

Record native scorer/Q out of band, program/part/pose lineage, handoff rejections, actual policy exposure, contact failures, wall-time censoring, and all qualified/unqualified port versions. No dataset or policy training is part of this plan.

## 11. Installation and validation

The bundle is additive. Its installer checks payload SHA-256 values and exact upstream interface Git blob hashes, preflights conflicts, refuses symlink/path escapes, never overwrites existing files, and accepts identical reapplication. Use an idle checkout/worktree; it is not a multi-process repository lock.

```bash
python apply_bundle.py --repo /path/to/physical-agent-harness --check
python apply_bundle.py --repo /path/to/physical-agent-harness --apply

cd /path/to/physical-agent-harness
# Existing project dev/behavior environments already declare NumPy/Pillow/test dependencies.
python -m pytest -q tests/action_compiler
python -m physical_harness.action_compiler demo --output runs/compiler-fixture-new
python -m pytest -q
ruff check .
```

Optional consolidated offline validator:

```bash
python tools/validate_action_compiler.py \
  --output runs/compiler-validation-new --full-suite --lint
```

The fixture uses synthetic depth/masks and a fake actuator/geometry reviewer confined to `fixture`. It generates catalog, scene, schema, selection, receipts and accounting artifacts. It is not a robotics benchmark or evidence that GraspGenX is installed. See the bundle’s `VALIDATION_REPORT.md` (also installed as `docs/ACTION_COMPILER_V1_VALIDATION.md`) for exactly what was and was not tested locally.

## 12. Sources and terminology

[S1] Current project report, pinned: https://github.com/AranKomat/physical-agent-harness/blob/ffdd3bb8da9bfffb533cb5b77cd6ea88752c5a14/docs/HYBRID_NATIVE_EXPLORATION_20260921.md

[S2] Official BEHAVIOR evaluation rules, retrieved during this implementation: https://behavior.stanford.edu/challenge/evaluation.html . Track requirements may change; this package is not a submission-compliance certificate.

[S3] GraspGenX repository README at reviewed revision: https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/README.md

[S4] Actual sampler API and coordinate restoration: https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/graspgenx/grasp_server.py

[S5] Import setup and asset behavior: https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/graspgenx/__init__.py and https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/graspgenx/_setup_dependencies.py

[S6] GraspGenX research paper: https://arxiv.org/abs/2606.00998 . This bundle is an API integration and original harness implementation, not a reproduction of the paper's evaluation or an import of its end-to-end physics demonstrations.

“Minecraftification,” “geometry/action compiler,” and “neural control duty cycle” here describe this project's design and measurements. They are not claims that uncertain robot sensing is equivalent to Minecraft's authoritative game state, that GPT never chooses incorrectly, or that more articulated robots need no whole-body/contact control.
