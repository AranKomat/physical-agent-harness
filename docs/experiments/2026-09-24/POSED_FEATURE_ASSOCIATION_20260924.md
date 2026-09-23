# Posed Feature Association Evidence

## Fixed Experiment

Combine reciprocal SIFT correspondences with measured depth and existing legal
camera poses for the five retained radio views 384, 416, 448, 480, 512. No new
alignment is fitted. Parameters are 2,000 full-image features, reciprocal 0.75
ratio matches, and a two-pixel mask erosion. Depth is sampled at matched pixel
locations and deprojected into each recorded camera pose's local-map frame.
Two non-wrapping destination-mask translations (+/-180 pixels) are wrong-region
controls, not genuine similar-object distractors.

Source: `sam31-live-pose-cache-20260922-r1`. Native receipt SHA-256:
`2078fdc61b310fc749ba98b464abf24bad1e8aa2ab20cf68ed516c701e2189ae`.
This is the same source as the prior retained surface-consistency analysis,
not the later live fusion run which had empty target masks in this window.

## Results

| Pair | Unique pixel pairs | Median disagreement | p95 disagreement |
| --- | ---: | ---: | ---: |
| 384 -> 416 | 5 | 9.38 mm | 18.20 mm |
| 416 -> 448 | 6 | 6.76 mm | 36.56 mm |
| 448 -> 480 | 7 | 4.12 mm | 12.68 mm |
| 480 -> 512 | 7 | 6.86 mm | 14.13 mm |

All eight translated-region controls have zero matches. These are internal
correspondence residuals, not absolute accuracy or an uncertainty calibration.
The maximum individual residual is 45.70 mm. No residual threshold was fitted
to grant identity; all outputs retain `identity_qualified=false`.

## Corrections And Limitations

The initial attempt selected the later live-fusion source and correctly failed
on empty masks. No masks were borrowed between episodes. The documented earlier
source was then selected and its native receipt hash verified. The first
successful result (`posed-feature-association-20260924-r2`) counted multiple
SIFT orientations at the same pixels separately. The corrected r3 permits each
source/destination pixel location only once, removing 0, 1, 1 and 2 duplicates.
Both successful outputs remain local; the failed source selection is recorded
here and in the tool history, not represented as a completed run receipt.

The final result is `runs/posed-feature-association-20260924-r3/receipt.json`.
Same-frame mask/pose lineage is checked through the existing consumer. Full
mask erosion is not robot-pixel exclusion, and pose estimation and SIFT use
correlated RGB-D evidence. No genuine same-category alternatives, loss/reentry,
or changed-object matching is tested. Nearest-depth sampling is not a subpixel
depth uncertainty model. This does not qualify Phase 2 association or geometry.

Decision: appearance-plus-depth provides measurable support beyond tracker IDs,
but this small sequence cannot calibrate a general association producer. Do not
repeat it to increase passing counts or promote its residuals to a confidence
threshold. Genuine distractor/ambiguity evidence and independent uncertainty
assessment are still needed. No robot actions, new model inference or paid calls
occurred. The script passes Ruff; no public runtime code was changed.
