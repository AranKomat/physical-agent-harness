# Memory research ledger — v0.7

Access date: 2026-09-19. This is a targeted architecture/code review, not a reproduction of any paper's experiments. “Recommended” below is our integration judgment, not a measured performance ranking. No external framework, VLM, robot model, or simulator was run in this review. Sources are primary author papers, repositories, and project pages.

## Reviewed application base

**Physical Agent Harness**, commit `6f3216f3e046d356c2801a8aa4211e2e1fecf36d`.

- Repository: https://github.com/AranKomat/physical-agent-harness/tree/6f3216f3e046d356c2801a8aa4211e2e1fecf36d
- Current README: https://github.com/AranKomat/physical-agent-harness/blob/6f3216f3e046d356c2801a8aa4211e2e1fecf36d/README.md
- Evidence: https://github.com/AranKomat/physical-agent-harness/blob/6f3216f3e046d356c2801a8aa4211e2e1fecf36d/physical_harness/evidence.py
- Context: https://github.com/AranKomat/physical-agent-harness/blob/6f3216f3e046d356c2801a8aa4211e2e1fecf36d/physical_harness/context.py
- Spatial wrapper: https://github.com/AranKomat/physical-agent-harness/blob/6f3216f3e046d356c2801a8aa4211e2e1fecf36d/physical_harness/adapters/rtsm.py

**Source-derived:** The base has content-addressed artifacts, bounded context, task/world-state separation, local RGB-D odometry code and retained relation beliefs. It explicitly does not claim a qualified training-free general BEHAVIOR/R1Pro policy. The reviewed `ContextProjector` selects caller-supplied entities/images, not automatically retrieved episodic memories.

**Decision:** Add historical memory beside those interfaces; do not replace their state or verification semantics. Keep current generalization deferral and official radio integration fixture unchanged.

## S1. ReflectWorld / ReflectWorld-MM — strongest new functional-overlap candidate

- Paper: https://arxiv.org/abs/2607.09759 (v2, July 2026).
- Repo: https://github.com/addxai/ReflectWorld
- Inspected revision: `d2d395426600067cae1c8de0a2d3e86e3a65ae51`.
- Architecture: https://github.com/addxai/ReflectWorld/blob/d2d395426600067cae1c8de0a2d3e86e3a65ae51/docs/architecture/overview.md
- Service schemas: https://github.com/addxai/ReflectWorld/blob/d2d395426600067cae1c8de0a2d3e86e3a65ae51/services/mem/src/models.py
- Relevant packages: `packages/cam`, `packages/percept`, `packages/mem`, `services/mem`.

**Source-derived:** Camera/video capture becomes segments, entity observations and persistent memory. The architecture separates a largely TypeScript runtime from a Python memory service and Qdrant. The request schema exposes entity/run/camera filters and `semantic_mode="inline"|"background"`; **inline is the default**. The paper evaluates long-video/lifelong-memory question answering, not robot task completion.

**Decision:** First external backend to compare in a separate replay sidecar. Its broad memory product is more relevant to this idea than adding another VLA. Do not import the dashboard, face/voice recognition or broad assistant integration into the minimal harness. Disable unnecessary personal-identity features. Enforce our episode, capture-time, knowledge-watermark and evidence boundaries around every write/read.

**Limits:** Read architecture and request schemas, not a full security or end-to-end concurrency audit. A search filter called `run_id` does not prove causal-prefix isolation. A “background” option does not prove bounded queue behavior under robot load. No claim that it is faster/better on BEHAVIOR.

**License:** Repository declares Apache-2.0; its third-party notices and individual models/assets require separate review. No source copied into our overlay.

## S2. WorldMM — best multimodal retrieval representation donor

- Paper: https://arxiv.org/abs/2512.02425 (revised March 2026; CVPR 2026).
- Repo: https://github.com/wgcyeo/WorldMM
- Inspected file: https://github.com/wgcyeo/WorldMM/blob/main/src/worldmm/memory/visual/memory.py
- Inspected visual-memory Git blob: `95c88f278ae722feb28565a9a7cd2cc8c9461c61`.
- Other useful interfaces: `src/worldmm/memory/memory.py`, `src/worldmm/memory/utils.py`.

**Source-derived:** Episodic, semantic and visual memories are separately retrievable. Visual memory stores clip metadata and uses precomputed embeddings; it can retrieve original frames by time or matching clips by text. This preserves evidence that text summaries discard.

**Decision:** Borrow the separation between historical descriptions, structured facts and original visual evidence. Use text to find the correct evidence, not as a substitute for all evidence. Start with entity/place/time filters and lexical ranking; benchmark a visual embedding reranker only after measuring misses.

**Limits:** The inspected visual code is organized around prepared files/embeddings, including an internal pickle loader. That is not our live sensor API or an acceptable untrusted input format. Future-prefix leakage must be audited in all upstream caption/semantic preprocessing, not just the final clip filter. No WorldMM runtime integrated here.

**License:** Not fully audited in this pass. Do not copy source or redistribute models until checked.

## S3. ReMEmbR — direct robot diary precedent, but inspect rather than blindly copy

- Paper: https://arxiv.org/abs/2409.13682
- Repo: https://github.com/NVIDIA-AI-IOT/remembr
- Memory schema: `remembr/memory/memory.py`.
- Inspected example: https://github.com/NVIDIA-AI-IOT/remembr/blob/main/examples/chat_demo/db_processor.py
- Inspected example blob: `cccc7db53f49bb2bf35c3c9dcb223ade560f3076`.

**Source-derived:** Captions are associated with timestamps and robot position/orientation; the API searches by text, time and location.

**Code-level correction:** The inspected callback uses:

```python
self.vila_executor.submit(self.process_into_db(self.image_buffer, pose_dict))
```

Python evaluates `process_into_db(...)` before calling `submit`. That line does not offload captioning as intended; a correct callable submission would pass the function and arguments separately. Our earlier blanket description that this example already provides a working asynchronous caption path was too strong. This observation is about that example/revision, not a judgment that every ReMEmbR integration is broken.

**Decision:** Reuse the caption/time/place idea; implement and test our own bounded writer lifecycle. Model inference must never run inside the control/event callback.

**License:** Repository has a license notice; no code reused here, so no dependency assumed without a separate audit.

## S4. EventMemAgent — useful online-memory design, not a required new agent

- Paper: https://arxiv.org/abs/2602.15329
- Repo: https://github.com/lingcco/EventMemAgent
- Inspected builder: https://github.com/lingcco/EventMemAgent/blob/main/eventmemagent/memory/builder.py
- Inspected builder blob: `6093a0fa40edaf86445b6de3a00fa7b7984bf86a`.

**Source-derived:** A bounded short-term frame buffer feeds event memory and retrieval. The released builder exposes sampling/frame/change settings, Qwen-VL captioning options, HTTP/shared-runtime paths and histogram-based change logic. The complete method also trains an adaptive tool-using agent.

**Decision:** Prefer event boundaries to dense captions, but use our known skill/door/room/target events first. A moving camera can change the histogram without an important physical event, or miss a subtle grasp transition. Keep a low-rate heartbeat and optional visual novelty as supplementary triggers.

**Limits:** We did not reproduce its published video benchmarks. We do not need GRPO, its OCR/detection service bundle or its checkpoint for the first memory slice. Its default retries/frame budgets are not adopted as our paid-inference policy.

**License:** README declares Apache-2.0; separate model/tool dependencies still need review.

## S5. M3-Agent — useful parallel perception/control reference

- Paper: https://arxiv.org/abs/2508.09736
- Author project: https://m3-agent.github.io/
- Repo: https://github.com/ByteDance-Seed/m3-agent

**Source-derived:** The author project describes separate memorization and control activities with entity-oriented episodic/semantic memory. Robot-perspective questions are part of its evaluation.

**Decision:** Strong conceptual support for a parallel memory process. Avoid confusing robot-view video question answering with closed-loop manipulation success. No M3 source-level transplant or model run in this update.

## S6. KEMO — event selection evidence, not available drop-in code

- Author page: https://hatty-z.github.io/KEMO/

**Source-derived:** Kinematics plus visual filtering select transition keyframes; learned fusion inserts those memories into a VLA. The page reports 28–95-second real manipulation tasks and currently labels code “coming soon.”

**Decision:** Useful event-selection idea. Not a released plug-in we can claim to have integrated, and not evidence for ten-minute BEHAVIOR performance. Keep policy weights unchanged in this workstream.

## S7. MEM — short visual / long textual memory inside a policy

- Paper: https://arxiv.org/abs/2603.03596

**Source-derived:** Multi-scale embodied memory combines short-horizon visual memory and longer-horizon language memory; reported tasks can last approximately fifteen minutes.

**Decision:** Supports the representation tradeoff. This is model-level work, not a training-free library that can simply be installed around any executor. External memory remains the right initial experiment for our swappable stack.

## Existing spatial stack: RTSM, RoboStream, DynaMem, DREAM

- RTSM: https://github.com/calabi-inc/rtsm
- RoboStream: https://github.com/yu2hi13/RoboStream
- DynaMem: https://dynamem.github.io/ and https://github.com/hello-robot/stretch_ai
- DREAM: https://github.com/BJHYZJ/DREAM

These were discussed/reviewed earlier; this pass does not repeat an exhaustive source audit. Keep their roles distinct. Spatial association, dynamic map maintenance and localization are not the same as autobiographical event retrieval. RTSM remains the existing source of object IDs/geometry. No new SLAM or hardware dependency is added to ship the diary prototype.

## Excluded or unverified claims

The earlier conversation mentioned HyMeS and HALO. This pass did not independently establish a suitable, released, source-audited integration for them. They are **not dependencies or evidence for the delivered implementation**. No previous headline score is carried into our acceptance criteria.

## Overall decision

Build a small, source-preserving episodic sidecar first. Compare ReflectWorld as an optional external backend using the same recorded prefixes and memory contracts. Borrow WorldMM's multimodal separation and ReMEmbR's spatio-temporal indexing. Use harness events rather than a new learned event detector initially. Do not retrain a VLA, change the motor plan, or expand to a full surveillance/assistant platform.

The unresolved empirical question is **which memory construction/retrieval design improves our decisions under a fixed information, latency and cost budget**. None of these sources by itself answers that for our robot. The replay protocol in `MULTIMODAL_MEMORY_V07.md` is designed to answer it without waiting for a general motor-policy winner.
