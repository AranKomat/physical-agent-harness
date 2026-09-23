# SAM Tracking Through Native Radio Displacement

## Protocol

Phase 2's earlier retained protocol lacked a natural object-movement case (S11).
An older supervised Behavior-Skill rollout contains visible radio contact,
rotation and displacement. This follow-up reuses its legal head-camera pixels;
it does not repeat the policy trial or make new model API calls.

Before inference, freeze trace indices 48 through 96 at stride four: 13 views
from one native chronological segment. These are sparse observations, not
adjacent video frames. Start one SAM 3.1 tracker with image acquisition and text
`radio`, official-file preprocessing, no seed box and no later reset. Retain every
output with no retry or favorable-frame replacement. Only arrived RGB pixels
reach SAM; instructions, task outcomes and evaluator labels are not model inputs.

Source trace SHA-256:
`b606d75c8e95f5ce0b0a40516882b941ba069288b99e93450133a19b0a2fd8a9`.

## Results And Limits

- All 13 steps completed without errors or retries.
- 1,589 loaded learned parameter tensors matched the pinned checkpoint exactly.
- All 13 views have a nonempty mask with local tracker ID 0.
- Visual overlay review shows the mask following the radio from upright onto
  its back and through partial gripper occlusion.
- Some gripper pixels are included in several masks. This is tracking evidence,
  not manipulation-grade boundary accuracy or ground-truth segmentation scoring.
- Initial inference: 495 ms. Warm median: 140 ms on one RTX 4090, excluding model
  loading, simulator capture, downstream depth processing and networking.

This supplies previously missing natural-displacement tracking evidence, not
physical identity qualification. Local ID continuity is not association proof.
Full disappearance/reappearance, similar-object discrimination, crossings,
metric displacement and the complete V3 association chain remain unqualified.
Phase 2 remains partial.

## Retention

Private artifacts: `runs/displacement-sam-20260923-r1/` contains the frozen plan,
runtime hashes, parameter audit, masks and timing. The visual review is
`runs/displacement-sam-analysis-20260923-r1/review.png`. Implementation is in
`scripts/run_displacement_sam.py` and `scripts/analyze_displacement_sam.py`.

Report SHA-256:
`1aa5f876e21eb68ef388b8360ff66eb72d3fb750fa130229f7f918f60275d173`.
Worker-status SHA-256:
`d8e8f9f9aa52e9bbae530a5c0e63ece5f81f57d70854b84556411c19ba5ffd0c`.

No new robot actions or paid calls. The worker ran at low priority on CPU cores
19-22 with thread caps; no instance lifecycle, package or unrelated-process
changes were made. Complete output was copied locally.
