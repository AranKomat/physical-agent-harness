# Physical-agent multimodal memory — implementation handoff v0.7

**Date:** 2026-09-19  
**Reviewed base:** `AranKomat/physical-agent-harness`, commit `6f3216f3e046d356c2801a8aa4211e2e1fecf36d`  
**Deliverable:** additive historical-memory prototype, offline tests, synthetic replay example, research ledger and integration plan.  
**Not a result:** no new BEHAVIOR rollout, model evaluation, GPU inference, paid API call or task-success measurement was performed for this update.

## 1. Read this first: what is changing and what is not

Add a **multimodal episodic-memory sidecar** to the existing physical-agent harness. It records useful past observations as event cards, entity/place views, crops and optional motion references. The executive retrieves selected historical evidence instead of repeatedly receiving the full video history.

Do not restart the harness, replace `WorldState`, or change the motor experiment. The current decisions remain:

- Keep BEHAVIOR as the integration target. General-policy generalization remains deferred.
- The official radio-trained π0.5 checkpoint is an integration fixture, not a general-policy result. No training or adaptation is authorized by this document.
- GPT-6 remains the candidate semantic verifier at sparse boundaries. The cheap-verifier path remains disabled for the initial pilot.
- A cheaper VLM may later narrate memories in a separate background role. Its words are **untrusted historical annotations**, never task-completion judgments.
- Preserve legal-observation boundaries and keep the native evaluator out of all agent, writer and retrieval inputs.
- The website, robot hardware and cloud-serving business are out of scope.

**Primary implementation choice:** add the new package alongside the current code. Begin in shadow/replay mode, where memory is recorded and queried but cannot affect actions or task completion. Only connect it to executive context after evidence and recall checks.

## 2. What the repository already has

The inspected base already contains `EvidenceStore`, `WorldState`, `TaskLedger`, bounded context, chunked skills, event handling and recovery contracts. Since the earlier review, it also contains an Open3D RGB-D odometry path, retained relation memory and semantic-boundary observer/verifier hooks. These are implementation interfaces, not yet blanket physical-competence claims. See the pinned [README](https://github.com/AranKomat/physical-agent-harness/blob/6f3216f3e046d356c2801a8aa4211e2e1fecf36d/README.md).

The new gap is narrower than “build memory”:

| Already present | New component needed |
|---|---|
| Immutable source artifacts | Automatically choose and index useful past evidence |
| Current and remembered object relations | Chronological event history linked to those entities |
| Task progress and dependencies | Searchable explanations of attempted actions and observed outcomes |
| Current images selected by the caller | Crop galleries, landmark views and retrieved historical images |
| Recent runtime events | Human-readable historical cards and optional narration |
| Byte-bounded context | Retrieval whose entire text-and-image contribution stays bounded |

The existing `EvidenceStore` remains the blob store. The new database is **not** the world-state database. Sharing a database by accident is rejected when known world-state tables are found.

## 3. Architecture to implement

```text
                              legal sensor stream
                        RGB / depth / proprioception
                                       |
                    +------------------+------------------+
                    |                                     |
             existing perception                  source recording
          localization / RTSM / etc.               EvidenceStore
                    |                                     |
             current WorldState             bounded recent frame refs
                    |                                     |
                    |                  runtime events / sightings / places
                    |                                     |
                    |                              EventRecorder
                    |                               /          \
                    |                   deterministic card      optional queue
                    |                           |                    |
                    |                    episodic.sqlite       cheap VLM writer
                    |                           ^                    |
                    |                           +--- untrusted narration
                    |                           |
                    |                     historical Retriever
                    |                           |
          TaskLedger + ContextProjector + selected cards/images
                                       |
                              executive decision
                                       |
                          existing skill/navigation loop
```

The semantic verifier remains outside the memory writer. It can inspect original evidence retrieved through the normal bounded interface, but a writer caption does not become verifier evidence merely because it is stored.

### Three separate meanings of “memory”

**Current belief:** “The candle is believed to be in the cabinet now.” This belongs to `WorldState` and has uncertainty, timestamps and supporting observations.

**Historical event:** “At time 80, the controller attempted to place the candle; the runtime later reported a supported postcondition.” This belongs to episodic memory. It remains a historical report even if the candle moves again.

**Learned behavior:** A reusable motor skill in a policy or controller. This update does not train or alter it.

A text diary is a search index over experience, not a second authoritative copy of the world.

## 4. Research conclusions and reuse choices

The [research ledger](MEMORY_RESEARCH_LEDGER.md) contains source URLs, inspected code paths, review depth and limitations. The following are our integration judgments, not measured winners.

**ReflectWorld is the most interesting new external candidate.** Its architecture already combines stream segmentation, entity-resolved observations, event/semantic memory and agent recall. Its Python service schemas include run/entity/camera filtering and inline/background semantic updates. Keep it as a separately launched comparison backend, not a compulsory dependency or a replacement for calibrated robot state. Its published evaluation concerns long-video memory/QA, not physical manipulation. Disable irrelevant identity/face/voice features and audit causal retrieval. Sources: [architecture](https://github.com/addxai/ReflectWorld/blob/d2d395426600067cae1c8de0a2d3e86e3a65ae51/docs/architecture/overview.md), [service schema](https://github.com/addxai/ReflectWorld/blob/d2d395426600067cae1c8de0a2d3e86e3a65ae51/services/mem/src/models.py), [paper](https://arxiv.org/abs/2607.09759).

**WorldMM is a useful representation/retrieval donor.** Preserve episodic descriptions and original visual memories separately, with time-based access to frames/clips. Its inspected implementation uses prepared metadata and embeddings; it is not a ready-made streaming robotics adapter. Do not import its whole preprocessing pipeline or assume a query-time filter fixes summaries generated with future video. Sources: [paper](https://arxiv.org/abs/2512.02425), [visual memory](https://github.com/wgcyeo/WorldMM/blob/main/src/worldmm/memory/visual/memory.py).

**ReMEmbR supplies a direct robot-diary precedent:** caption, time, pose, query. However, the inspected example calls a function before submitting to its executor, so it does not implement the intended asynchronous offload at that line. This corrects our earlier overstatement. Borrow the pattern, not the callback implementation. Source: [db_processor.py](https://github.com/NVIDIA-AI-IOT/remembr/blob/main/examples/chat_demo/db_processor.py).

**EventMemAgent and KEMO support event-based retention, with different integration costs.** EventMemAgent includes a bounded online builder and trained tool-using agent; its visual-change mechanism should not be assumed to identify meaningful robot events. KEMO's author page describes kinematic/visual event selection, learned VLA fusion, and code still “coming soon.” Use skill outcomes, target loss, room/door transitions and perception changes first. Do not add model training. Sources: [EventMemAgent builder](https://github.com/lingcco/EventMemAgent/blob/main/eventmemagent/memory/builder.py), [KEMO](https://hatty-z.github.io/KEMO/).

**M3-Agent and MEM are useful supporting references.** M3-Agent separates memorization and reasoning; MEM studies short visual and long textual memory inside a policy. Neither is evidence that our external diary improves BEHAVIOR before we test it. Sources: [M3 project](https://m3-agent.github.io/), [MEM paper](https://arxiv.org/abs/2603.03596).

No external implementation has been vendored. This keeps the overlay small, avoids incompatible runtimes and leaves the researcher free to substitute a backend after actual replay measurements.

## 5. Delivered files and actual capabilities

```text
physical_harness/memory/
    schemas.py       immutable source/card/cutoff/writer contracts
    store.py         append-only episode-local SQLite records
    selection.py     bounded recent references and event recording
    media.py         source-preserving crops and storyboard handles
    writer.py        optional bounded asynchronous narration worker
    retrieval.py     entity/place/time filters, lexical ranking, bounded packets
    __init__.py      public imports

prompts/memory_captioner_v07.txt
examples/memory_replay.py
tests/memory/...
docs/MULTIMODAL_MEMORY_V07.md
docs/MEMORY_RESEARCH_LEDGER.md
```

The core uses the Python standard library. Pillow is needed for crop creation and the synthetic image tests/demo. No model SDK, embedding model, detector, video decoder or GPU runtime is imported by the memory package.

### Implemented versus deferred

| Capability | Status |
|---|---|
| Source-backed historical cards and episode isolation | Implemented |
| Exact entity/place/time filtering and lexical ranking | Implemented; not learned semantic retrieval |
| Original image references and pixel crops with lineage | Implemented |
| Multiple temporal images / storyboard and existing clip handles | Implemented as references; no video cutting service |
| Bounded event-triggered recent-frame selection | Implemented from supplied events, not a learned event detector |
| Optional nonblocking caption-worker submission | Implemented/tested; no actual model transport bundled |
| No-current-state-write rule | Enforced by package dependency/API design; not a security sandbox |
| Two-axis causal cutoff | Implemented |
| Whole-context size/image checks | Implemented; provider token/tile accounting still required |
| Automatic object masks, identity association, place recognition | Existing perception/adapters must provide them |
| Live BEHAVIOR capture bridge, paid Qwen/GPT writer | Not wired/run here |
| ReflectWorld or WorldMM backend adapter | Comparison design only |
| Consolidation, forgetting, semantic vector search | Deferred pending evidence of need |

## 6. Storage model: evidence first, narration second

### Asset

An `Asset` identifies a hash-named artifact with an episode, observation ID, capture interval and camera. Images have dimensions; crops additionally have the parent image and pixel box. Clips have source intervals. No arbitrary URL, executable path or pickle deserialization is accepted.

Register the artifact after the existing sensor path captures it. Hash checking establishes byte integrity, **not** the truth of a caption or the provenance of a malicious upstream sensor plugin. The adapter remains responsible for admitting only legal sensor data and honest capture times.

### Card

A `Card` records one of `event`, `entity_view`, `place_view`, `motion`, or `coverage_gap`.

It carries stable entity/place bindings, source event ID, capture interval and asset IDs. A sighting of an existing object does not create a new identity just because its label changed. New identity decisions remain in the tracker. Store ambiguous IDs/hypotheses upstream rather than letting the captioner decide identity from similar appearance.

The field `reported_outcome` deliberately says **reported**. `verifier_reported_supported` means the runtime emitted that event historically; it does not certify that the predicate is true now. No field is called “ground truth.”

### Annotation

A writer returns only `Draft(text, cited_asset_ids, optional token counts)`. Provider-output parsing accepts exactly the text and citation fields. Reject additional `verified`, `action`, `task_status`, or world-state payloads. An annotation remains `untrusted_narration`, even when GPT rather than Qwen wrote it.

Use stable model and prompt identifiers. A conflicting rewrite under the same ID fails instead of silently rewriting history. For a corrected narration, use a new prompt/model revision and retain the old record. General retraction/curation UI is not implemented yet.

### Entity and place cards are views, not giant profiles

The first implementation stores sightings linked to IDs and retrieves a bounded history. It does not rewrite an ever-growing biography after each frame. A compact profile can later be a materialized query over immutable sightings. That avoids duplicate storage and recursive summary drift.

## 7. The important causal rule: use two cutoffs

A single timestamp is insufficient when model work runs asynchronously.

Example: a frame is captured at simulation time 100. The simulator pauses while a caption job runs. At the first executive decision, the caption is not ready; at a later wall-clock moment it is ready, still with simulation time 100. An offline replay that filters only `capture_time <= 100` would incorrectly expose the later caption to the earlier decision.

The implementation records:

```python
Cutoff(
    episode_id="episode-17",
    observed_through=100.0,
    knowledge_seq=recorded_commit_watermark,
)
```

Every executive decision saves its cutoff. A returned card, asset or annotation must both belong to the episode and have been available by that watermark; its source observations must not exceed the capture cutoff.

`knowledge_seq` is a local durable append order, not a synchronized wall clock. Multiple writers use the same memory store serialization point. Capture time still comes from the simulator/sensor path. If another service uses its own clock, the integration must map it explicitly rather than guessing.

When replaying recorded material, stream only the prefix that was available. Do not build summaries using an entire future episode and then give them an earlier timestamp. The contracts reduce accidental leakage; they cannot detect a dishonest caption-service implementation that secretly read future files.

## 8. Event selection and asynchronous construction

### First version

Register recent legal image references in `RecentBuffer`. On a normalized runtime event, persist a deterministic source-backed card through `EventRecorder`. This operation never calls a model or moves the robot.

Use real boundaries: skill returned, target lost, contradiction, arrived, door blocked, new place, object sighting or a coarse heartbeat. Unknown event types must be normalized explicitly. Do not attach full arbitrary event payloads to the writer; bind only stable IDs and evidence.

The default recent reference buffer holds at most 64 frames and twenty seconds. A boundary selects at most four representative images from the preceding eight seconds, prioritizing current camera views and early views. These are engineering defaults, not established optimal settings. Critical before/after frames may need explicit pinning by the adapter. Empty evidence creates a `coverage_gap`, not an invented diary.

### Worker behavior

`AsyncAnnotator.submit()` queues an ID/cutoff and returns without performing inference. The deterministic card already exists. The worker invokes the injected callback separately, validates its result and appends the annotation. Current defaults are one worker, queue capacity eight and at most thirty reserved caption jobs per episode.

Reservations are persistent and conservatively counted. A queue-full job is recorded, its card survives, and there is no hidden retry. Duplicate requests or restarts cannot silently repeat an expensive job with the same identity. Interrupted reservations remain unresolved; explicit reconciliation is a later operational task.

The worker is a daemon thread suitable for replay and controlled pilots. A Python thread **cannot forcibly stop** a stuck model/RPC callback. The callback must have its own hard timeout; `close(timeout)` reports whether it stopped. Close/join the writer before closing its store. For production use a separately supervised process, bounded IPC and GPU scheduling. None of those production guarantees is claimed by this prototype.

Run event ingestion on a sidecar/drain, not a hard-real-time controller callback. Persisting hashes and SQLite records has nonzero cost even without inference. If a shared GPU is used, motor deadlines take priority; low-priority narration should skip rather than delay control. Resource prioritization is an integration requirement, not implemented here.

### Model choice

Start with no narrator or a deterministic template writer on replay. Add a cheap VLM after the transport and budget are explicitly approved. The six-scene Qwen verifier diagnostic does not qualify it as a narrator; it merely shows why narration must stay advisory. Assess false event descriptions before exposing them to the executive.

The caption callback receives source handles, not automatically encoded images. Its adapter must resolve each handle through `store.read_asset(asset_id, cutoff)`, decode within image limits, and submit the actual ordered pixels to the chosen VLM. Captioning metadata alone is not a visual test.

A paid writer must wrap the callback in the existing authorization/reservation ledger, with an output cap and no automatic tier upgrade or retries. This package's call cap is not a dollar budget. GPT remains the verifier candidate; this update does not change that selection.

## 9. Crops, places and motion

**Crops:** `make_crop` creates actual PNG pixels, validates dimensions, and retains the original image, box, camera, observation ID and capture time. Making a crop tomorrow does not make yesterday's scene current. A crop is useful for appearance, marks or instance comparison. It may remove the receptacle, floor or nearby objects needed for spatial reasoning. Store/retrieve its parent for containment, reachability and clearance judgments.

**Place views:** Use a wide frame tied to a navigation/SLAM place ID and optional upstream geometry. A caption such as “corridor with blue sofa” is a search handle, not a coordinate frame or localization measurement. Do not replace map matching with text identity.

**Motion:** Use an existing recorded clip interval or several temporally ordered images. `storyboard` returns handles and times; it does not generate intermediate motion or encode a video. A single still image cannot establish how an action unfolded. Automatic clip cutting/codec tooling remains a separate optional media job. Preserve actual ordering, timestamps and original media.

Do not apply ordinary appearance deduplication to motion trajectories blindly: identical-looking endpoint frames can represent different times and a meaningful pause. The packet builder deduplicates identical image bytes for context economy, but preserves event records. Use the explicit storyboard path when temporal sequence matters.

## 10. Retrieval and context behavior

`Retriever.search` first filters by episode/cutoff and optional entity/place/time/type. It then uses deterministic lexical ranking. `history` returns a limited chronological slice. No claim is made that this is semantic vector retrieval; a missed synonym is an expected limitation to measure.

`Retriever.packet` bounds cards, images, pixels and JSON bytes. It rereads authoritative stored IDs instead of accepting a caller-forged `Hit` summary. Historical images and narration are clearly labeled. It returns clip handles rather than automatically inserting whole clips into the prompt.

`attach_memory` takes an already-built current context and adds `episodic_memory`. It does not discard live images, task constraints or pending failures to make the diary fit. An over-budget context fails visibly so the caller can retrieve fewer old cards. In ordinary use the caller should retry locally with a smaller memory budget, not retry a paid model request.

Initial engineering defaults:

| Bound | Value | Meaning |
|---|---:|---|
| Memory cards | 5 | Maximum historical entries per packet |
| Memory images | 3 | Separate from required current views |
| Memory pixels | 1,500,000 | Geometry bound, not token price |
| Memory JSON | 7,000 bytes | Text/metadata only |
| Entire context JSON | 12,000 bytes | Current context plus memory |
| Entire image count | 6 | Current and retrieved combined |

These limits are deliberately separate. Byte count is not token count; pixel count is not the provider's tile accounting. An actual model runner must enforce its own text/vision tokenizer, model limits, cost reservation and transport limits with `provider_check` or equivalent.

The present executive tool allowlist has no free-form `memory.*` surface. The least disruptive first integration retrieves memory automatically when building context. Later expose bounded historical queries through the existing `inspect` handler, or explicitly revise its tool schema. Do not silently introduce arbitrary tool names that the executive rejects.

## 11. Installation and first offline check

The distributed update contains `overlay/`, a manifest, an additive installer and a patch. It does not include your existing repository source or any robot data.

From the extracted update package:

```bash
# Default is dry-run; use a clean checkout at the reviewed commit.
python apply_memory_update.py /path/to/physical-agent-harness

# Review the paths, then explicitly apply. No commit/push occurs.
python apply_memory_update.py /path/to/physical-agent-harness --apply
```

A newer descendant can be used with `--allow-descendant` after reviewing intervening changes. The installer still refuses file collisions and dirty tracked files. It never overwrites different existing files. Reapplying identical added files is idempotent. A clean worktree is preferable when your researcher is modifying the main checkout concurrently.

Inside the target checkout:

```bash
python -m pip install -e '.[dev]'
# Add optional image tooling in the research environment, not the core runtime.
python -m pip install Pillow
python -m pytest tests/memory -q
python -m pytest -q
python -m physical_harness doctor
python examples/memory_replay.py --output /tmp/memory-v07-demo-new
```

The last command uses synthetic drawn shapes and a deterministic caption callback. It should show zero robot actions, zero model calls, zero paid API calls, and correct old/new knowledge-cutoff behavior. It is a contract demonstration, not a benchmark or VLM result.

## 12. Exact native integration recipe

The code below is integration pseudocode around the delivered APIs; the private radio runner and its source adapters are not supplied by this package.

```python
from physical_harness.evidence import EvidenceStore
from physical_harness.memory import (
    Asset, MemoryStore, RecentBuffer, EventRecorder, Retriever,
    PacketBudget, boundary_from_runtime, attach_memory,
)

# Use the existing sensor artifacts directory, but a SEPARATE database.
blobs = EvidenceStore(episode_directory / "evidence")
memory = MemoryStore(episode_directory / "episodic.sqlite", episode_id, blobs.read)
recent = RecentBuffer(episode_id)
recorder = EventRecorder(memory, recent)
retriever = Retriever(memory)

# SENSOR DRAIN, not motor callback:
# 1. Resolve each legal source artifact through the existing evidence path.
# 2. Register Asset with true episode/capture/camera/dimensions and SHA256.
# 3. memory.add_asset(asset); recent.add(asset)

# SEMANTIC EVENT DRAIN:
boundary = boundary_from_runtime(
    runtime_event,
    entity_ids=tracker_entity_ids,
    place_ids=navigation_place_ids,
)
card = recorder.record(boundary)

# DECISION TIME:
cutoff = memory.cutoff(current_sim_time)
# Persist this cutoff in the decision log BEFORE asynchronous jobs can finish.
base = existing_context_projector.build(...)  # unchanged current context path
hits = retriever.search(cutoff, entity_id=current_target_id, limit=5)
packet = retriever.packet(hits, cutoff, PacketBudget())
context = attach_memory(base, packet, provider_check=approved_budget_preflight)
# Use the existing executive transport and log the exact delivered context.
```

For a first live hook, use the semantic-boundary evidence that the runtime now captures after actions. Register before/after frames using their original observation timestamps. `MemoryStore` reads existing hash-named files; do not pass arbitrary paths or private database handles into caption prompts.

The sidecar can store object/place bindings without estimating new 3D geometry. That makes crop/event/time recall testable before full mobile navigation is qualified. Metric place coordinates, if used, must still come from the legal localization path.

The callback that maps a **qualified verifier result** into `WorldState` remains separate. A memory card may describe that result but must never call the same completion hook. The writer package intentionally has no `WorldState`, `TaskLedger` or controller imports.

## 13. Replay evaluation: find what works without another motor search

Do not decide from paper leaderboards. Run memory comparisons on the **same frozen observation prefixes**, with human/evaluator labels held outside the system.

### First dataset

Use the existing radio capture only for integration and observability checks. It is insufficient to establish multi-object memory. Collect or reuse legal recordings showing repeated objects, occlusion, relocation, return to a place, an unsuccessful attempted manipulation and at least one motion whose endpoints alone are ambiguous. Native robot control need not be autonomous to test historical recall; label the trace source honestly.

Separate development traces from evaluation traces by episode/scene. Do not use every prefix of a single video as independent evidence of broad generalization. Keep capture clocks, action receipts and knowledge availability logs. All retrospective labels are evaluation-only.

### Questions that expose the difference

Ask where an object was **last observed**, which cabinet had been inspected, what changed after an attempt, which of two appearances matched a prior object, whether an outcome is actually visible, and what evidence supports the answer. Include unknown/unobservable questions. Asking only “what is in the current image?” will not test episodic memory.

### Controlled conditions

| Condition | Executive input | Purpose |
|---|---|---|
| M0 | Current state + bounded recent frames | Existing baseline |
| M1 | M0 + text event cards | Does historical indexing help? |
| M2 | M1 + retrieved source images/crops | Does visual evidence recover lost detail? |
| M3 | M2 + selected ordered storyboard/clip access | Does temporal evidence help motion questions? |
| Optional external | ReflectWorld-normalized memories under same bounds | Is a larger existing backend worth integrating? |

Use the same event construction, narrator outputs and cutoffs for M1 versus M2; only visual access should change. Disable `get_image`/clip tools in a true text-only condition, not merely inline thumbnails. Keep the same total context budget, not a larger allowance for the new system. Record all extra writer/retriever/answer-model costs.

For raw-video baselines, restrict frames to the same observed prefix and information allowance. A full-video offline QA result is not comparable to online robot memory. For asynchronous comparisons, distinguish “instant offline availability” from actual measured online writer completion; never claim they are equivalent.

### Metrics

Measure source-event and source-image recall at a fixed retrieval budget; answer correctness with cited support; false memories; identity confusion; unknown-case abstention; stale-current-state claims; bytes/images/pixels delivered; writer calls and queue drops; writer latency and lag; retrieval latency; and total API/compute cost.

Agreement with GPT is **not ground truth**. Use independent human labels or permitted out-of-band state to score, never to author the memory input. Report numerators and denominators rather than a single percentage from a tiny probe. A paired improvement on several memories is exploratory; expand episodes before claiming general benefits.

Only after this passes should the memory influence live choices. Compare downstream omitted/repeated subgoals, recovery decisions, task success and cost using the same motor/executive configuration. No memory QA gain proves motor competence.

## 14. Recommended work packages and stop conditions

**A — Merge and validate.** Apply only new files, run new and full tests in your real checkout, inspect state/provenance boundaries, then commit locally. Stop on a schema mismatch rather than adjusting native action codes.

**B — Shadow capture.** Attach legal images and normalized events from the existing pilot to the sidecar. Keep memory out of executive context. Confirm episode/time/hash lineage and no additional paid calls. Any missing media becomes a coverage gap, never a guessed observation.

**C — Entity/place/media path.** Bind tracker/navigation IDs, generate source-linked crops on selected sightings, add wide landmark views and ordered failure snippets. Stop if identical-object identity is unsupported; preserve ambiguity rather than force a match.

**D — Optional narrator.** Add one timeout-bounded approved VLM callback; start with a low per-episode job budget. Evaluate captions on replay. If captions fabricate outcomes, keep templates and sources, revise writer prompts only on development traces, or drop narration entirely.

**E — Bounded recall.** Run M0/M1/M2 first. Add M3 only for questions that need temporal evidence. If no gain at equal budgets, do not add a vector DB or another model by default; inspect whether retrieval, evidence coverage or the actual task requires history.

**F — External backend audition.** Only if needed, launch ReflectWorld on the same prefixes with optional inference/features disabled by default. Normalize its outputs into our historical-card interface. Check IDs, source references, write latency, future leakage and cost before expanding. Discontinue if integration cost exceeds useful recall improvement.

These can proceed while the general motor problem remains deferred. Do not turn memory work into another policy qualification campaign.

## 15. Acceptance gates and limitations

Before exposing memory to actions, require:

1. No cross-episode, future-frame or late-annotation leakage at saved decision cutoffs.
2. Crops preserve source time/geometry/parent and remain distinguishable from current views.
3. A command or writer sentence never creates a verified belief or finishes a task.
4. Queue saturation and narrator failure preserve original evidence and do not block motion.
5. All extra text/images fit the complete context budget, with actual provider accounting.
6. Memory can answer at least the intended historical questions using genuine recorded traces; unobservable outcomes remain uncertain.

The prototype has no learned semantics, automatic segmentation, identity resolution, object detector, streaming video encoder, external backend transport, distributed-store recovery or production security isolation. Its trace scan is intentionally bounded for short episodes, with a visible error beyond the reference limit rather than silently losing recall. Callback plugins remain trusted code; advisory labels are not a sandbox against a malicious plugin or prompt injection. The executive must treat all remembered text, including text visible in scenes, as data.

For ten-minute experiments retain the raw evidence and all cards on disk. Evict only working-buffer references and prompt content. Add retention/deletion only for real storage/privacy requirements, not because a transformer context is small. Later consolidation must remain source-linked, preserve contradictions and avoid repeatedly summarizing summaries.

## 16. Validation performed for this delivery

The new memory suite passed **65 tests** in the local environment. This includes one compatibility test against a byte-identical copy of the inspected upstream `EvidenceStore`; its Git blob SHA was checked as `8725ef829657b81a93f3d3358784629345970588`. A standalone overlay without that existing module skips that one test; the other 64 remain runnable.

The additive installer passed **11 tests** against temporary synthetic git repositories. A synthetic image/event/crop/narrator replay completed with no model calls or robot actions.

The full current application suite was **not** rerun here because the complete checkout was unavailable in the execution environment. No Ruff pass, external-framework reproduction, native sensor/perception validation or robot outcome is claimed. Run the full suite in your checkout before merging. See the delivered validation report for commands and environment.

## 17. Researcher handoff instruction

> Keep the current BEHAVIOR pilot, verifier choice and motor-generalization deferral unchanged. Merge the additive `physical_harness/memory` prototype in a review branch and run all tests. First wire legal saved/live observations and semantic-boundary events into a separate episodic store in shadow mode. Do not enable narration or paid calls automatically. Preserve capture times and record a knowledge watermark for every decision. Add object crops and place views using existing IDs, then compare recent-only, text-memory and text-plus-source-image recall on held-out recorded episodes under identical budgets. A memory caption must never update current beliefs or certify completion. Treat ReflectWorld as an optional replay backend to assess, not a replacement for the harness. Report evidence coverage, retrieval quality, wrong-memory rates and total cost before connecting the memories to live decisions.
