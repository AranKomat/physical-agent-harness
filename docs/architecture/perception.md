# Perception And Identity

The intended two-rate pipeline is occasional semantic discovery and frequent
source-bound tracking/geometry, not a VLM call on every frame.

1. Legal RGB-D/proprioception enter through sensor adapters.
2. `perception.keyframes` selects bounded, available observations for discovery.
3. `perception.discovery` runs the strict, read-only semantic contract.
4. `perception.regions` preserves source boxes/crops for SAM seeding.
5. Tracking, depth, localization and `perception.identity` establish current
   support; labels alone cannot establish persistent physical identity.

GLM is the current candidate for occasional inventory. Its bounded delta prompt
is a different, not-yet-qualified task. VLX has promising target grounding but
known semantic confusions. LocateAnything is a description-grounding candidate,
not a category-inventory substitute. SAM remains refinement/tracking, not the
authority for which physical instance fulfills the complete task description.

The corrected private streaming SAM 3.1 worker is distinct from the public
`integrations.sam` offline prefix adapter. Do not replace the live worker with
that replay implementation. Camera/session/local track IDs must survive handoff;
old boxes may only seed their original images before causal propagation.

Normalized, pixel, and metric coordinates are separate contracts. Convert boxes
only using declared source dimensions. Derive XYZ from measured depth and legal
camera calibration/pose, never from VLM prose. Occlusion and ambiguous reacquisition
remain unknown until association evidence resolves them.

See [current experiments](../experiments/queue.md) and
[integration status](../integration/README.md); no model-ranking generalization
follows from the small retained radio trace.
