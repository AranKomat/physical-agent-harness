# V3 coverage of the 50-item post-Situated-V2 backlog

This table uses the numbered backlog in the implementation request. **New** means executable software in this overlay; **reused** means an existing implementation is deliberately retained; **port-gated** means the code boundary exists but the actual robot/model integration remains unqualified. No row is a claim of native task success.

| # | Requested item | Delivery |
|---|---|---|
| 1 | Far-range semantic discovery | **New:** strict `DiscoveryRequest/Result`, coarse sightings; no manipulation-grade geometry assumed. |
| 2 | Asynchronous GLM worker | **New:** one in-flight/one coalesced pending job, bounded results, durable records; guarded transport must enforce hard timeout. |
| 3 | Attention and memory in one call | **New:** two typed response sections with output caps; not partial-token actuation or parallel decoding. |
| 4 | Event-driven semantic keyframes | **New:** view/pose/track/place novelty and explicit refresh; no fixed periodic requirement. |
| 5 | Short frame buffer | **New:** bounded current/complementary-frame selection and omission reporting. |
| 6 | GLM box to SAM track | **New + reused tracker:** source-frame seed/xywh conversion, crop hashing and current-mask association check; live corrected SAM stays unchanged. |
| 7 | Sighting versus entity | **New + reused IdentityLedger:** sightings and guarded links, no geometric/identity promotion by GLM. |
| 8 | State maturity | **New/reused:** transient buffers → historical sightings → established current entity links → existing action-specific eligible catalogs. Readiness is not a permanent global boolean. |
| 9 | Relevance-based memory admission | **New:** ordinal semantic hints plus declared heuristic ranking; no calibrated probability claim. |
| 10 | Hot/warm/cold hierarchy | **New:** derived bounded tiers and protected runtime pins; archive capacity is explicit. |
| 11 | Crowded-scene aggregates | **New:** ignore/aggregate/sighting/retain/focus; aggregate wording never establishes individual IDs. |
| 12 | Image-first semantic memory | **New:** actual frame/crop references and parent lineage; descriptions remain interpretations. |
| 13 | Canonical complementary views | **New:** source/hash/association-checked multi-view selection and retained candidate history. |
| 14 | Optional embedding index | **Optional interface:** externally computed scores rank authorized historical candidates; no embedding model installed. |
| 15 | Room diary/deltas | **New:** room-initial versus delta request mode, known summary and dual-clock change retrieval. |
| 16 | Compact semantic map | **New projection:** occupancy, rooms/gateways, inventory, frontiers and coverage in one bounded view. |
| 17 | Entity/place/frontier navigation | **New proposals + existing navigator:** current approach/search-region destinations and opaque MapTool IDs; native admission still required. |
| 18 | Semantic frontier scoring | **New heuristic:** semantic hint + unknown-boundary count − path cost; not a learned VLFM reproduction. |
| 19 | Online map rather than digital twin | **Reused/new projection:** works from a bounded observed map; does not implement new SLAM or repair old camera assumptions. |
| 20 | Map as GPT tool | **New:** offered destination IDs, compact summary and current path proposals; no GPT-authored wheel commands. |
| 21 | Next-best-view scoring | **New:** numerical observed-point projection/diversity/visibility/travel proxies; missing geometry remains unknown. |
| 22 | Distinct visual memory/outcome/information goals | **Reused Situated V2:** separate types remain; no duplicate visual-goal hierarchy. |
| 23 | Discovery versus manipulation perception | **New boundary:** sightings don't need masks/XYZ; native manipulation still requires current reviewed geometry. |
| 24 | Near-range SAM/depth path | **Reused:** corrected existing live tracker and Action Compiler deprojection, not replaced by a new image service. |
| 25 | Current versus remembered semantics | **Reused + projection:** `focus_identity_view` uses actual current binding or explicitly historical semantics/conflicts. |
| 26 | cuRoboV2/cuMotion arm backend | **New/port-gated:** actual audited cuRoboV2 `plan_pose` adapter, scene receipt, joint/timebase checks and existing Driver wrapper. cuMotion is an alternative interface target, not separately implemented. |
| 27 | High-rate visual servo | **New numerical helper/port-gated:** bounded target-relative setpoints; high-rate performance and native actuation not established. |
| 28 | Force/tactile interface | **Dormant:** descriptors only; no invented force sensor or contact-controller implementation. |
| 29 | Foveated high-resolution hook | **New/dormant:** source-preserving crop and qualified closer-view request; no new BEHAVIOR camera or artificial-resolution claim. |
| 30 | LiDAR interface | **Dormant:** descriptor for future hardware; extra BEHAVIOR channels rejected. |
| 31 | Compiled capabilities/macros | **New:** six unqualified parameterized semantic graph templates with pre/postconditions and explicit review. |
| 32 | Graph-fragment compilation | **New:** freeze existing bounded graph as unqualified artifact; no automatic promotion from success count. |
| 33 | Capability registry | **New + existing capabilities:** exact graph/deployment promotion plus current facts/bindings/capabilities admission. |
| 34 | Learned action tokenization | **Deferred by request:** no tokenizer, latent-action study, training or new hand controller. |
| 35 | Recurrent GPT embodied executive | **New integration:** meaningful physical decisions remain with GPT; GLM stays read-only. |
| 36 | Semantic-boundary scheduling | **New:** completion/discovery/identity/candidate/verifier/graph events, coalesced and budgeted. |
| 37 | Executive Attention Budget V2 | **New:** mandatory-state preservation, explicit optional pruning, bounded current/history imagery and optional real tokenizer count. |
| 38 | WorldState as RAM/on-demand retrieval | **Reused + new:** current facts/catalog/identity views plus bounded inventory queries; host fulfills existing evidence/history tools. |
| 39 | Semantic delta log | **New:** dual-clock historical changes and current-task attention, no full-video replay default. |
| 40 | GLM not action-side | **Enforced:** no action fields or actuator callback in semantic request/result/coordinator. |
| 41 | No Jev dependency | **Deferred by request:** existing generic branch interfaces untouched; no new model/service. |
| 42 | GPT direct keypose path | **Reused/promoted:** alternative single-call `propose_keyposes` reuses bounded V2 anchors/program compiler; remains proposal-only pending fresh review. |
| 43 | Frozen VLA optional specialist | **Reused:** explicit mode/candidate only, no automatic failed-planner fallback or changed policy recipe. |
| 44 | Explicit control mode | **New:** typed options validate mode/intent compatibility; native constraints remain separate. |
| 45 | Desired image subgoal | **Reused V2:** separate real/reference/hypothetical visual roles; no new learned world model. |
| 46 | Monitor fabric | **Reused + routing:** deterministic and existing advisory learned monitors feed appropriate semantic events. No new monitor training. |
| 47 | Monitor-result routing | **New:** progress versus completion candidate/failure/loss/uncertainty; no automatic task-truth mutation. |
| 48 | Compute accounting | **New + reused:** provider usage, exact image repetition, cached tokens, reasoning conventions, cost unknowns; retain existing duty/energy counters. |
| 49 | Representation cache discipline | **New wrapper over existing cache:** exact dependencies only; no poses/commands/collision approvals/task truth cached as authority. |
| 50 | Runtime framing | **New docs:** information-efficient recurrent embodied reasoning plus classical execution, not a promised drop-in universal policy speedup. |

## Additional integration corrections found while implementing

**Slow executive reply versus short catalog TTL:** explicit semantic rebinding to a fresh candidate is required; stale metric catalogs are never retimestamped. When there is no unique, qualified current equivalent, the system requests fresh judgment rather than substituting a nearby pose.

**Journal semantics:** code uses the actual repository `Journal.records()` format and does not put an `id` field at the top level of a record body (the journal supplies that identifier). Inventory batches and execution selections are immutable and persisted before use.

**Planner holds and accounting:** trajectory streaming checks fixed as well as controlled joints; all confirmed braking/settling ticks are counted. A successful planner return alone is not measured endpoint success.

**Compute claims:** two output sections do not mean simultaneous token decoding; exact-byte novelty is not semantic information; zero VLA steps is not zero neural compute; no speedup or current model price is assumed.
