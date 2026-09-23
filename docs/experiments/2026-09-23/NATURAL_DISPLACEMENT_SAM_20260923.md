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

## Identity-Ledger Integration Follow-Up

The 13 actual mask artifacts were subsequently replayed through `Tracklet`,
`IdentityLedger`, `AssociationProof` and `focus_identity_view`, backed by a real
SQLite journal. Every input mask hash, source-image hash, index and mask summary
was checked. Because this RGB-only plan does not attest native simulation times
or metric calibration, the replay explicitly uses fixture-order clocks and no
metric centers; it is not presented as a live native association test.

All 13 masks remained candidates without canonical labels or action bindings.
Later local-ID continuity, supplied with unknown independent association support,
did not replace the first track's historical geometry. Reloading the journal
produced identical identity state. Private result:
`runs/displacement-identity-20260923-r1/receipt.json`.

The unresolved positive requirement is an independent association producer, not
more tracker-ID persistence. It needs evidence for uniqueness, temporal support
and geometric support before transferring a remembered semantic label to current
geometry. SAM continuity and visual overlay review alone do not supply that proof.
Further repeats of this negative contract test are not the next experiment.

## Independent Feature-Correspondence Diagnostic

An offline SIFT test then measured appearance support on the same frozen 13
images, independent of SAM's numeric IDs. OpenCV 4.10.0.84 was installed in an
isolated local dependency directory, not the shared GPU host or existing runtime.
Parameters were fixed before running: 2,000 image features, reciprocal nearest
neighbors with a 0.75 ratio test, and a 3-pixel RANSAC homography threshold.
Features are extracted on whole images; source-mask membership and destination
candidate membership are checked after matching. Two translated destination
masks, left/right by 180 pixels, are artificial wrong-region controls.

| Pair | Matches into radio candidate | Homography inliers |
| --- | ---: | ---: |
| 48 to 52 | 21 | 13 |
| 52 to 56 | 1 | 0 |
| 56 to 60 | 6 | 6 |
| 60 to 64 | 4 | 4 |
| 64 to 68 | 2 | 0 |
| 68 to 72 | 3 | 0 |
| 72 to 76 | 7 | 7 |
| 76 to 80 | 3 | 0 |
| 80 to 84 | 9 | 9 |
| 84 to 88 | 6 | 6 |
| 88 to 92 | 5 | 5 |
| 92 to 96 | 3 | 0 |

All 24 wrong-region controls had zero destination matches. However, five actual
pairs had fewer than four matches, including the large rotation at 52 to 56.
The full local analysis took 1.12 seconds excluding imports. This is evidence
against promoting sparse SIFT matching alone into the missing association
producer. Matches can also come from included gripper pixels, and a fitted
homography is neither rigid 3D identity nor uniqueness among similar objects.
No thresholds were relaxed and no positive association was written.

Private result: `runs/displacement-features-20260923-r1/receipt.json`.
Script SHA-256:
`0d0efd524018fc6b983f2e16b7bc800194c336eddfcb179b91a302eee7e9c990`.
Next useful association test requires denser temporal evidence and robot-pixel
exclusion or independent reobservation, not another identical sparse replay.
