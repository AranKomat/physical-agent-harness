# Physical-agent experiment runner — v0.10

**Self-contained researcher handoff.** Target: `AranKomat/physical-agent-harness`, reviewed at `72fbfd15b5fe547e8f447884236ac5edfb27ee96` (2026-09-19).

## 1. What this update is—and is not

This update adds an executable integration layer around the existing v0.9 harness. It is not another replacement framework. It uses the real `WorldState`, `TaskLedger`, `RichContextBuilder`, `ExecutiveLoop`, `HarnessRuntime`, `VerificationRouter`, `EvidenceVisualVerifier`, and episodic-memory classes.

The first goal is one bounded **simulator** experiment with real image-bearing model requests and an existing, reviewed native motor fixture. The model executive, semantic verifier, evidence import, historical memory, cost journal, and replay export are now connected in code.

It does **not** supply a new motor policy, establish a training-free BEHAVIOR/R1Pro pairing, implement robotics SLAM or object re-identification, train models, or establish benchmark improvement. Those cannot be inferred from interfaces or synthetic tests. The official radio-task-trained policy remains an integration fixture, not generalization evidence. No new training is authorized by this package.

The public repository and its license are unchanged until you apply the overlay. Do not publish private image traces, credentials, or billing ledgers with the source code.

## 2. What is implemented

| Area | New working code |
|---|---|
| Executive model | Responses or qualified Chat-compatible JSON adapter, actual image bytes, independent contexts, locally validated decisions |
| Verifier | Fresh before/after images per call; source/hash/time checking; explicit goal criteria and qualification; unknown/unobservable outcomes cannot complete tasks |
| Native execution | Typed callbacks plus a real bounded POSIX JSON-lines subprocess bridge for a separate simulator Python environment |
| Experiment loop | Observation → rich context → model decision → reviewed semantic action → fresh observation → semantic verification → ledger/event → next decision |
| Crops and places | Automatic parent-linked crops from supplied tracker boxes; representative wide views associated with supplied place IDs |
| Coverage | Scoped, source-backed coverage notes; no inferred destination from a missing detection |
| Memory | Source observations, semantic events, cards, optional asynchronous narration, and bounded retrieval in shadow mode |
| Context | Per-field freshness and unresolved conflicts, in addition to existing broad context |
| Cost | Explicit rate cards, provider input counting, durable reservations, usage reconciliation, role-specific reports |
| Replay | Frozen M0 decision snapshots plus causal M1/M2 exports; optional image-bearing memory QA |

"Implemented" means executable code and the stated tests, not real-world qualification.

## 3. Install and run the no-cost checks

Use a clean branch/worktree at the reviewed revision. From the extracted package:

```bash
python apply_experiment_v010.py /path/to/physical-agent-harness
python apply_experiment_v010.py /path/to/physical-agent-harness --apply

cd /path/to/physical-agent-harness
python -m pip install -e '.[dev,experiment]'
python -m pytest tests/experiment tests/memory -q
python -m pytest -q
ruff check .

python -m physical_harness.experiment demo --output /tmp/physical-demo-new
python -m physical_harness.experiment doctor \
  --config configs/experiment_v010/doctor.fixture.json
python -m physical_harness.experiment export-replay \
  --run /tmp/physical-demo-new --output /tmp/physical-replay-new
```

The demo generates simple PNG images and passes them through the actual new model-request and runner paths with a deterministic fake provider. It calls no external model or simulator. The loopback HTTP and subprocess tests test real local transport mechanics, not robotics ability. `doctor.fixture.json` validates configuration only; it is not a functional inference endpoint.

The installer is dry-run by default, checks the upstream commit and dependency file hashes, rejects unexpected files, and does not commit/push. `--allow-descendant` permits a reviewed descendant only if the checked dependency files still match. Do not override a mismatch blindly.

## 4. Configure real models without guessing their names or prices

Copy `configs/experiment_v010/pilot.template.json` to a private run configuration. It intentionally fails validation until placeholders are replaced.

Set the exact model IDs actually available to your account. Configure GPT for the executive and semantic verifier according to your experimental decision; no particular model name or availability is assumed by the code. Both roles may use the same underlying model, but have distinct instructions, contexts, and accounting.

Fill each model's rate cards with current **USD per million input, cached-input, and output tokens**, including source and date. Values are decimal strings. Include the actual service tiers that may be returned. A paid Responses result without a recognized actual tier leaves spend unresolved rather than pretending it was served at the requested discounted rate. The code never silently changes Flex to standard or retries a failed request.

Set `OPENAI_API_KEY` in the process environment, not in JSON. The default HTTP transport uses HTTPS, rejects redirects, disables inherited proxy routing, and runs each request in a separate process with a local wall deadline. Explicit loopback HTTP is supported for local model servers. A local timeout does not cancel remote generation or guarantee that it will not be billed.

The Responses path uses `/responses/input_tokens` before generation. If an endpoint/model does not support this path, do not disable accounting and continue with paid calls: supply a tested image-aware counter programmatically or qualify another endpoint. The Chat-compatible path needs an injected counter for paid use. A self-hosted zero-API-price local narrator may run without a token estimator, but that does not make GPU time free.

The first implementation supports a conventional input/cached-input/output tariff. It does not implement arbitrary provider fees, separately billed cache writes, context-threshold pricing, or GPU rentals. If the chosen model's tariff has those terms, qualify/extend the accountant before relying on its dollar bound. Provider bills remain the ultimate accounting reference.

Before real execution:

```bash
python -m physical_harness.experiment doctor --config /private/pilot.json
```

This performs no network call and starts no simulator. It does not prove endpoint access, affordability, model quality, or sensor correctness.

## 5. Connect the existing BEHAVIOR driver—do not reimplement the simulator

The native process can use a different Python environment from the harness process. Install this package's `experiment` extra in the native environment as well, alongside its existing simulator dependencies.

Set:

```bash
export PHYSICAL_DRIVER_FACTORY='your_private_package.driver:create_driver'
```

`create_driver(episode)` returns your existing driver object with:

```python
name: str
simulated: bool = True
qualification_id: str

capture_legal() -> LegalObservation | dict
read_rgb(native_reference: str) -> bytes
run_skill(request: SkillRequest) -> SkillReceipt
stop() -> bool
```

The shipped `physical_harness.experiment.existing_bridge:driver_factory` adapts that object into `NativeBindings`; no edit to the experiment package is needed. Alternatively, your factory may return `NativeBindings` directly and be named in the native command.

The required work is **wiring these four real methods**, not copying another ZIP or inventing stubs that claim success.

### `capture_legal`

Return the existing approved observation envelope: episode, observation ID, simulation time, RGB/depth references, proprioception, camera intrinsics/frames, and optional observation-derived pose. The adapter passes image bytes—not file names—to the model path and checks their dimensions against calibration.

Simulation is paused during executive/verifier inference in this version. Re-reading an unchanged paused scene should return the same observation ID and bytes. A new observation ID must advance simulation time. Reusing an ID with changed pixels is rejected. Before any native action is dispatched, the runner reobserves; a changed scene invalidates the decision rather than executing a stale plan.

The metadata-only bridge cannot prove that your private driver did not use simulator ground truth. Keep the existing legal-observation boundary and audit it. Do not pass simulator object coordinates, segmentation IDs, task success, or reward through estimates, descriptions, or model context.

### `run_skill`

Use the policy's **verified** observation/action codec, normalization, controller mapping, and checkpoint. No slicing, scaling, or robot-tag guess is provided here.

Execute at most the frozen action/step/time bounds. Return a `SkillReceipt` whose `skill_id`, start/end simulation times, action count, and metadata match the request. Required metadata:

```json
{"episode_id":"actual-episode","execution_epoch":0,"stop_acknowledged":true}
```

`completed` means the bounded controller job returned—not that the semantic task succeeded. The runner validates the receipt before any verification/completion callback. On partial execution or unknown stop state, return/raise conservatively; the run stops without an automatic retry.

The first model interface selects predeclared **semantic action IDs**. It does not synthesize arbitrary torques, Python, or unreviewed coordinates. Register navigation or IK-backed skills only after their native executors are qualified. The existing navigation/L3 contracts are not magically made native by this update.

### `stop`

Return `True` only after the relevant simulator/controller execution is stopped. Process death, discarding an action response, or a timeout is not a stop acknowledgement. The subprocess client marks a timed-out channel unresolved and refuses further commands.

This runner is scoped to simulation. It is not a physical safety controller, deployment certification, or a substitute for independent local watchdogs/interlocks.

## 6. Optional perception outputs and automatic visual memory

Your driver can also expose these callbacks, each accepting only the legal envelope:

```python
estimates(envelope) -> iterable[BeliefEstimate]
boxes(envelope) -> iterable[ObjectBox]
place(envelope) -> (place_id | None, description | None)
coverage(envelope) -> iterable[CoverageScan]
```

These are the point to reuse the existing RTSM/perception adapter and legal localization, not to launch another unreviewed framework.

`ObjectBox` binds an actual integer-pixel box to a camera and observation. It includes the track ID, label, and `identity_candidates`. The runner calls the existing `make_crop`, saves the cropped pixels, retains the wide parent and original capture time, and writes an entity-view card. Ambiguous candidates remain retrieval aliases; they are not resolved by matching text labels. Goal verification checks target identity and rejects unresolved candidates.

The curator saves a wide view for a supplied place ID and a later revisit, with a simple cooldown. It does not infer a floor plan, recognize a room reliably from prose, generate novel views, or solve SLAM. A metric map remains the navigation system's responsibility. For the first stationary/bounded radio test, a known episode-local place label is adequate **if disclosed as fixture metadata**, not claimed as learned localization.

`CoverageScan` requires explicit targets, cameras, a measured coverage fraction, and a declared method. Only depth visibility, calibrated sweep, or human annotation are accepted. The corresponding note points to same-episode, same-time camera evidence. These checks validate provenance, not the accuracy of the supplied coverage measurement. A Qwen caption saying "I do not see the ball" is not a high-coverage scan. Never convert a non-detection into a guessed new object location.

The runner receives observation batches at semantic boundaries. Dense policy control and any high-frequency tracking during a long skill remain inside the native driver. This update does **not** claim to implement continuous multi-camera tracking or early interruption from a streaming perception server. Keep the initial skill duration short enough for the qualified native controller; add streaming only when an experiment exposes that need.

## 7. Verification and the radio observability trap

The verifier is a fresh call, not the planner reviewing its own conversational history. It gets a frozen postcondition, explicit visible criteria, before/after image metadata, and actual pixels. It must return one schema-validated verdict and cite supplied after-image IDs.

Important distinctions:

- Image provenance is not proof that a model's interpretation is correct.
- `qualified=False` remains diagnostic; a confident answer cannot complete a goal.
- `verifier_qualification` is an operator attestation referring to your qualification record, not a magic certificate generated by the code.
- Goal bindings are fixed before the run. The model cannot invent a new easier predicate and mark the original task complete.
- An unobservable goal returns `uncertain` without repeated futile model calls.

**Seeing a radio does not establish that it is powered on.** The template keeps power-on explicitly unobservable from RGB and separately labels visibility as an integration diagnostic. It cannot report the BEHAVIOR task as successful. Use an actual permitted visual indicator or another allowed sensor before changing that observability setting. A diagnostic subgoal is never a substitute for the benchmark goal.

The default verifier uses at most three views per before/after side. With more cameras, configure each goal's `verifier_cameras` explicitly; the executive can still receive the broader image set. There is no silent camera truncation.

For conjunctions, split the task into explicit goals. An individual `Goal` has one current-belief binding. General programmatic goal generation/dependencies are not supplied by this pilot.

## 8. Execute the first real model/native pilot

After configuration, native-driver wiring, independent visual-verifier qualification, and an approved budget:

```bash
python -m physical_harness.experiment run \
  --config /private/pilot.json \
  --output /private/runs/radio-pilot-001 \
  --allow-network --allow-paid --allow-motion
```

All three opt-ins are separate. Omit motion to test observation/model decisions without executing a native command. The starter configuration bounds the run to four executive decisions, one policy prefix, and a small declared dollar ceiling. Tighten or deliberately change those limits based on the native fixture—not on an untested performance assumption.

A useful first outcome may be:

```text
fresh pixels reached executive
one permitted semantic action dispatched
fresh after-images reached independent verifier
verdict stayed uncertain where state was unobservable
ledger did not invent success
historical cards and exact decision cutoffs were recorded
all processes stopped with explicit status
```

That is a successful integration test even if the benchmark task is not solved.

## 9. What gets recorded

A run contains:

```text
journal.sqlite             immutable requests, decisions, receipts, events, accounting
world.sqlite               current beliefs and task ledger
memory-decisions.sqlite    decision-time historical cutoffs
episodic.sqlite            event/entity/place cards and optional annotations
spatial-memory.json        shadow-only posed RGB-D keyframes and coverage records
evidence/                  content-addressed original images and crops
report.json                result and per-role accounting
```

The journal records the exact instructions, context, schema, image descriptors, parameters, and request hash. The pixels live once in the evidence store; repeated base64 bodies and credentials are not dumped into logs. To reproduce a request, resolve its descriptors against the content-addressed artifacts. Retain the run configuration privately.

The compact roster now includes per-field evidence timestamps and ages. A fresh `visibility` update cannot make a five-minute-old `location` look fresh. Unresolved same-time belief conflicts are included so the executive can see both possibilities.

The existing broad context policy remains generous. The runner does not aggressively hide surrounding objects or substitute a cheaper relevance model. Byte/pixel ceilings are distinct from token accounting. Oversized requests stop visibly; they are not silently shortened by the provider.

## 10. Memory is shadow-only in live runs

Legal frames and semantic events feed the memory sidecar. Crops and place cards are produced from real supplied bindings. Retrieval is computed and logged at each executive turn but is **not** inserted into the live executive context.

A historical-memory failure is recorded and disables the shadow path; it does not issue an action or certify success. Essential observation validation failures do stop the run. The synchronous source-storage/curation path has real overhead; measure it before using high-rate streams.

Narration is absent by default. To enable it later, insert the model object from `narrator.template.json` under `models.narrator`, replace its exact local model ID, and qualify the server's structured-output support. It uses the existing bounded asynchronous worker and the same durable cost journal. It receives only historical evidence and cannot modify WorldState or the task ledger.

If a cheap narrator invents details, its words can still bias retrieval. "Advisory" is not "harmless." Measure false memories and keep the original images. Do not add narration simply because a worker exists.

## 11. Replay without future leakage

Export:

```bash
python -m physical_harness.experiment export-replay \
  --run /private/runs/radio-pilot-001 \
  --output /private/replay/radio-001
```

M0 is the exact JSON saved **before the corresponding model call**. Never rebuild it from the final WorldState database: that would leak later object moves and task completion.

For each decision the export contains:

- **M0:** the already-stateful rich context, including short entity histories;
- **M1:** that same M0 plus causal historical cards/text;
- **M2:** M1 plus selected original historical images/crops.

Thus this tests the incremental value of episodic retrieval, **not memory versus no memory**. M1/M2 use the same cards and the same recorded observation-time/knowledge watermark. An annotation that finished later while simulation time was paused remains unavailable to an earlier decision. The variants share declared maximum budgets; do not pad fake tokens to pretend actual usage is equal. Report the actual cost/latency of each.

Optional `evaluate_qa` in `experiment/replay.py` sends these actual pixels to a configured `JsonModel`. Its separate labels file has:

```json
[{
  "question_id":"q01",
  "decision_file":"decision-0000.json",
  "question":"Where was this object last observed?",
  "expected_evidence_ids":["actual-source-id"],
  "must_abstain":false
}]
```

For the optional image-bearing QA run, extract a single role's `settings`, `transport`, and `rates` object into a private model configuration, then run:

```bash
python -m physical_harness.experiment evaluate-replay \
  --export /private/replay/radio-001 --labels /private/qa-labels.json \
  --model-config /private/qa-model.json --output /private/qa-results-new \
  --max-api-microusd 5000000 --max-calls 30 --allow-network --allow-paid
```

The numeric ceiling here is an example user budget, not a predicted task cost. For a self-hosted zero-API-price model, omit `--allow-paid` and configure `paid:false` and zero tariff explicitly.

Labels never enter the model prompt. Automatic metrics are citation recall, unsupported citation IDs, and abstention agreement. Semantic answer correctness still needs independent review; agreement with GPT is not ground truth. Use trusted local replay exports rather than arbitrary third-party manifests.

The radio trace validates wiring only. For memory utility, collect actual multi-object/multi-place traces with relocation, occlusion, similar objects, failures and revisits. They may be teleoperated or scripted, but the agent input must still come from legal sensors. Do not wait for a general motor-policy winner to record such data.

## 12. Source/runtime compatibility and remaining work

The overlay adds files under `physical_harness/experiment`, tests, configs, and docs. It only patches `pyproject.toml` to add `jsonschema` and the experiment extra. It does not replace the existing runtime/state/memory implementations.

Still required on your side:

1. Fill actual accessible model IDs, endpoint capabilities and current rates.
2. Wire the real native driver's four methods and its existing safe action codec.
3. Supply real perception boxes/IDs/place estimates for automatic visual memory; do not use synthetic fixtures as measured perception.
4. Independently qualify the visible predicates you permit to update the ledger.
5. Run your complete upstream CI and a bounded native pilot; publish evidence, not interface counts.

Do not begin a training project or promise Halloween generalization because this runner exists. General R1Pro motor qualification, native navigation/IK and accurate object tracking are still separate capability questions. This update reduces the **glue-code** gap; it does not resolve those empirical gaps.

## 13. Implementation sources and scope of evidence

Source-level compatibility was checked against the pinned repository's files, including:

- https://github.com/AranKomat/physical-agent-harness/blob/72fbfd15b5fe547e8f447884236ac5edfb27ee96/physical_harness/runtime.py
- https://github.com/AranKomat/physical-agent-harness/blob/72fbfd15b5fe547e8f447884236ac5edfb27ee96/physical_harness/verification.py
- https://github.com/AranKomat/physical-agent-harness/blob/72fbfd15b5fe547e8f447884236ac5edfb27ee96/physical_harness/visual_verifier.py
- https://github.com/AranKomat/physical-agent-harness/blob/72fbfd15b5fe547e8f447884236ac5edfb27ee96/physical_harness/memory/integration.py

Provider implementation references, checked 2026-09-19:

- https://developers.openai.com/api/reference/resources/responses/subresources/input_tokens/methods/count
- https://developers.openai.com/api/docs/guides/images-vision
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/docs/guides/flex-processing

These sources support interfaces and request conventions, not model availability, prices, robotics performance, or correctness on your task. The tests and sample reports describe synthetic/transport checks only. See the package `VALIDATION.md` for exact test scope and unexecuted checks.
