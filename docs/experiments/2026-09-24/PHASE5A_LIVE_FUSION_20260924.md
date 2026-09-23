# Phase 5A Live Positive Fusion

## Result

Run `live-fusion-dense768-20260924-r5` completed the bounded simulator-only
shadow protocol with the pinned Behavior-Skill policy and corrected extended
fusion validator.

- Policy actions: 768
- GPT calls: 0
- Dense RGB-D captures: 84 (`384..768`, stride 4, excluding action boundaries)
- Fresh pose rows: 97
- Expected fusion boundaries: 13 (`384, 416, ..., 768`)
- Bound fusion rows: 13/13
- Fresh fusion rows: 13/13
- Target-bearing fusion rows: 13/13
- Motion authority: false throughout

The retained SAM results acquired a tracker candidate at sequences 704, 736,
and 768. RGB, depth, pose, mask artifact, and source-lineage checks passed for
all fused rows. The retained GPU artifact is
`runs/live-fusion-dense768-20260924-r5/posthoc-validation.json`.

## Scope

This qualifies positive, fresh, causally aligned sensor-fusion evidence in the
declared shadow window. It does **not** qualify metric localization accuracy,
identity, collision-free clearance, base transit, arm staging, contact, or task
success. No fused result was exposed as motion authority.

The first r5 owner receipt was marked failed because the remote orchestrator
still required exactly five fusion rows. That validator was stale relative to
the declared 768 window; the corrected validator was applied after the run and
passed against the unchanged retained artifacts. No simulator rerun was used
to overwrite that bookkeeping failure.

## Decision

Phase 5A's bounded positive-fusion gate is passed. Stop repeating the dense
fusion diagnostic. The next phase-level experiment is a small, independently
verified execution/endpoint test under the existing strict clearance and stop
gates. A negative result there must remain a motion-qualification result, not be
reinterpreted as a failure of the fusion lineage demonstrated here.
