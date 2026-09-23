# Architecture Decisions

Accepted for the experimental harness, 2026-09-23. These are design decisions,
not claims of qualified native performance. Revisit with measured counterevidence.

## ADR-001: Recurrent Embodied Executive

GPT selects and repairs bounded capabilities at semantic boundaries. Eliminating
reasoning entirely was rejected: visual judgment and recovery remain the research
question. Routine controller ticks stay local. Context/cost optimization must not
change this division of responsibility without a measured comparison.

## ADR-002: Discovery Is Read-Only

GLM contributes semantic hypotheses, attention and historical annotations, never
actions or task truth. A cheaper tactical-controller substitution was rejected
because naming an object does not establish identity, geometry or safe control.
Current status: promising inventory candidate; new delta/live contract unqualified.

## ADR-003: Labels Are Not Identity

WorldState beliefs, physical association and discovery sightings are distinct
views. One permissive object record was rejected because it could make historical
labels appear current. IdentityLedger bindings remain evidence-bound; two objects
with the same category do not become the same entity.

## ADR-004: Metric Geometry Comes From Sensors

VLM boxes propose regions; measured depth and legally estimated camera pose supply
metric geometry. Converting textual confidence or guessed XYZ into motion targets
was rejected. No automatic repair of ambiguous coordinate conventions is allowed.

## ADR-005: Frozen VLA Is An Optional Specialist

One existing executor owns classical primitives, planner/servo paths or a frozen
policy backend. Mandatory end-to-end VLA control and task-specific success
assumptions were rejected. Compatible checkpoints remain experimental until
bounded native evidence supports the intended task distribution.

## ADR-006: Simulation Qualifies, It Does Not Define Runtime Truth

Simulator fixtures are useful for integration and failure injection, not a
requirement for every decision or a source of privileged task state. Automatic
digital-twin planning was rejected as an unqualified dependency. Native ports
still need separate calibration, codecs, collision and stopping checks.

## ADR-007: Maps Are Incremental Evidence Views

Topology and local occupancy come from online observations. Compact map summaries
and frontier tools project existing data rather than own competing SLAM state.
Pre-mapping and obligatory persistent dense reconstruction were rejected. Geometry
retrieval can be on demand, with unknown space preserved as unknown.

## ADR-008: Responsibility-Based Code, Preserved Research Records

Seven runtime domains replace milestone namespaces. Internal call sites migrate
together; no indefinite alias layer is retained. Dated reports and exact receipts
remain reproducible evidence, but do not look like active deployment configs.
Changes to recorded data, native qualification, or paid budgets are outside a
consolidation release. See [migration scope](../architecture/consolidation.md).
