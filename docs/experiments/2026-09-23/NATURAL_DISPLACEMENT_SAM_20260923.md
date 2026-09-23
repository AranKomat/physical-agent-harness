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

## Intermediate-Observation Optical Flow

A paired Lucas-Kanade follow-up used all retained observations 48-96, comparing
direct propagation across each original four-observation gap with propagation
through its three intermediate observations. Source corners are seeded only
from the starting SAM mask; destination masks score results and never steer
propagation. Parameters were fixed: up to 100 corners, quality 0.01, spacing
3 pixels, 21-pixel windows, pyramid level 3, forward/backward error at most
1 pixel and forward photometric error at most 20. Both conditions start with
identical points. No replenishment occurs inside a pair.

| Pair | Direct points in target | Via intermediate observations |
| --- | ---: | ---: |
| 48 to 52 | 65 | 61 |
| 52 to 56 | 3 | 3 |
| 56 to 60 | 4 | 6 |
| 60 to 64 | 18 | 19 |
| 64 to 68 | 0 | 9 |
| 68 to 72 | 13 | 17 |
| 72 to 76 | 17 | 17 |
| 76 to 80 | 14 | 15 |
| 80 to 84 | 16 | 15 |
| 84 to 88 | 19 | 14 |
| 88 to 92 | 19 | 14 |
| 92 to 96 | 12 | 16 |

All translated-mask controls still receive zero points. Intermediate sampling
helps some pairs but does not repair the main rotation: surviving tracks fall
from 64 to 7 between observations 53 and 54, and only 3 reach the ending mask.
These retained observations are approximately 32 control actions apart, not
full-rate video. Thus this does not establish that high-rate optical flow would
fail, nor that surviving points necessarily belong to the object rather than
the gripper. The correspondence calculation took 145 ms locally, excluding
source decoding and hash checks. No association or motion authority was granted.

Private receipt: `runs/displacement-flow-20260923-r1/receipt.json`.
Script SHA-256:
`80b37ca80296590e6072c640decdfe44bf22d81cc3c6670a2543b2c8af28d31f`.
Do not tune thresholds on these same views to manufacture a positive result;
the remaining transition needs denser visual evidence or fresh discrimination.

## Full-Rate Video Follow-Up

The retained native video contains 3,224 frames at 30 fps. The inspected recorder
composes the head-camera image into columns 224-671, resized to 448x448. A fixed
interval, video frames 1663-1791, corresponds to source observations 52 and 56.
Its two endpoint mean absolute grayscale differences against resized retained
RGB captures are 2.042 and 2.028 on a 0-255 scale, within the predeclared limit 8.
No offset search was performed. This is compressed/resized pixel evidence, not
native full-resolution RGB-D or newly qualified timing/metric calibration.

The same 53 initial corners and unchanged LK checks were used for four temporal
sampling conditions. Destination masks were used only for evaluation.

| Video stride | Frames used | Surviving points | In ending radio mask |
| --- | ---: | ---: | ---: |
| 128 | 2 | 1 | 1 |
| 32 | 5 | 2 | 2 |
| 8 | 17 | 0 | 0 |
| 1 | 129 | 17 | 14 |

All off-target translated-mask controls received zero points. The full-rate
condition took 121 ms for the entire 128-interval propagation, excluding video
decoding, hashes and feature seeding. This is offline local CPU timing, not an
end-to-end native latency claim. Visual review finds surviving points on the
radio body/handle but also on the gripper; endpoint mask inclusion is not ground
truth identity. The stride-8 failure is retained, not discarded.

This changes the next implementation direction: test a cheap full-rate visual
continuity signal between slower SAM/discovery updates. Do not conclude from the
sparse failures that temporal association is impossible. Robot-pixel exclusion,
uniqueness, loss/reset behavior and independent metric support are still required
before this signal can establish physical identity or authorize manipulation.

Private artifacts: `runs/contact-video-flow-20260923-r1/receipt.json` and
`review.png`; script `scripts/replay_contact_video_flow.py`.
Video SHA-256:
`38a2f21ce2213d19617d8233a1a8f620815548ce0ea543d212235b92db10c52e`.

## Streaming Shadow Integration

A private `ContinuityShadow` now carries candidate feature points across ordered
frames. It requires a typed camera/session/observation identity, consecutive
sequence numbers and a bounded capture-time gap. Camera/session changes, gaps
or resolution changes discard the old points. Repeated/regressed frames and
historical mask seeds are rejected. New masks can seed only their named current
observation; reseeding starts a new tracker generation.

It reports point count and a diagnostic reacquisition request below four points.
That threshold is not a physical-association or geometry-confidence threshold.
Every output explicitly withholds association, current geometry and motion
authority. It is not connected to the native actuator or frozen-policy inputs.

On all 129 video frames in order, the streaming adapter matches the prior batch
result: 17 final surviving points, 14 inside the ending mask. This replay uses
video presentation time, explicitly not qualified native sensor capture time.
Private receipt: `runs/contact-video-streaming-20260923-r1/receipt.json`.
Six additional unit tests cover continuity, camera/session/gap resets and stale
seeds. Live sensor publication, robot-pixel exclusion, independent association
and natural loss/reacquisition still need qualification.

## Longer Continuity And Refresh Comparison

The adapter was then run over all 1,537 video frames from 1535 through 3071,
comparing a single initial seed against refreshes at all 13 existing SAM source
frames. All 13 video/capture mappings satisfy the same predeclared pixel-error
limit; observed mean absolute differences range from 1.992 to 2.050/255.
Destination-mask membership is evaluated before each refresh, not immediately
after reseeding. Both conditions share every video frame and fixed parameters.

Neither condition falls below four surviving points. However, at the final
anchor the single-seed condition has 15 survivors with only 9 inside the SAM
mask; periodic refresh has 17 survivors with 16 inside. After the major rotation,
the corresponding counts are 12/16 versus 14/17. All translated-mask controls
remain zero. These mask-relative measurements are not ground-truth identity or
accuracy, particularly because some SAM masks include the gripper.

This identifies a monitoring limitation: surviving point count alone does not
detect candidate drift/contamination. The adapter's low-count reacquisition
request cannot be interpreted as comprehensive tracking health. Periodic
current-source mask consistency and robot-pixel exclusion remain necessary;
no identity or motion authority is added.

Tracking time totals 1.316 seconds for single-seed and 1.285 seconds for refresh,
excluding video decoding, integrity checks and actual SAM inference. Refreshes
are idealized at their exact source frame, not measured asynchronous arrivals.
This is not a live two-rate pipeline latency or Phase 3 pass.

Private result: `runs/contact-continuity-long-20260923-r1/receipt.json`.
No new GPU work, model calls or robot actions were performed.

## Consistency Monitor Correction

The shadow adapter now propagates its previous points into the current image
before every mask refresh and records the inside/outside counts, fraction and
pre-refresh low-support status. Reseeding cannot hide disagreement. No comparison
is made across camera/session/gap resets, and stale mask sources remain rejected.
The values are descriptive, not a newly fitted identity-confidence threshold.

A regression replay of the same 1,537 frames matches the independently computed
counts at all 12 refresh boundaries. The lowest consistency is 14/27 (51.85%),
which the point-count-only monitor would miss. Final consistency is 16/17.
This is implementation verification on existing evidence, not a new independent
performance trial. Full private suite with isolated OpenCV: 1,085 passed and one
existing skip. Receipt: `runs/contact-continuity-monitor-20260923-r1/receipt.json`.

The next meaningful integration must handle actual asynchronous mask arrival;
the idealized source-aligned replay does not qualify that behavior. No further
identical offline repetitions are indicated.
