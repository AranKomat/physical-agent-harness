# World State And Memory

There is one authority for each question, not a single object record with every
kind of evidence treated as equally current:

- `world.state.WorldState`: episode-scoped current beliefs and predicate history.
- `perception.identity.IdentityLedger`: track-to-entity association, conflicts,
  remembered semantics, and current evidence-bound geometry bindings.
- `world.inventory.SemanticInventory`: historical sightings, semantic hypotheses,
  aggregates and retrieval hints. A known-ID suggestion is not an identity proof.
- `world.memory.MemoryStore`: evidence-backed episodic cards and image references
  under a causal cutoff, with posed views available as an optional index.

These are different projections of source evidence. The discovery coordinator
must not write current metric state or identity merely because GLM names an
object. `perception.identity.focus_identity_view` exposes this distinction explicitly.

`core.evidence.EvidenceStore` and the existing memory media path own artifact
bytes. Inventory crops retain parent asset/hash/ROI rather than inventing a second
sensor source. Coverage is negative observational evidence, not a guessed move.
Do not wire a second coverage system simply because another record type exists.

Representation caches in `world.representation_cache` and `world.semantic_cache`
share the existing dependency checks: the latter is a restricted semantic view,
not a second actuation cache. Cached history never refreshes a current pose,
collision review, identity proof or success result.

Native memory stays in its explicitly configured mode. A package reorganization
does not turn shadow retrieval into executive input or authorize future evidence.
