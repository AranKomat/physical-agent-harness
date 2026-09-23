# Natural Similar-Chair Candidates

## Protocol

Retained Corvid trash rollout:
`shortlist-corvid-extended-20260921-r1/picking_up_trash/trial-0/rollout.mp4`.
After visual screening and before inference, freeze frames 0-360 at stride 30
(13 one-second samples). Crop the onboard head panel, resize 448 to 720 square
with bilinear interpolation, and acquire once with prompt `chair`. No explicit
later reset, prompt variation, candidate selection or retry. All candidates and
empty outputs are retained. The worker uses only arrived RGB images.

Pre-inference review marks frames 0-180 chair-present, including a clipped chair
portion at 180, and frames 210-360 absent. Frames 0/30/60 contain multiple visible
chairs. These are qualitative visibility labels, not exhaustive instance counts
or pixel annotations. Labels are evaluation-only, not model inputs.

## Results

| Frame | Local candidate IDs |
| --- | --- |
| 0 | 0, 1, 2 |
| 30 | 0, 1, 2 |
| 60 | 1, 2 |
| 90 | 1, 2 |
| 120 | 2 |
| 150 | 2 |
| 180 | 2 |
| 210, 240, 270, 300, 330, 360 | Empty |

All 13 steps completed without retry or deadline. All seven chair-present
frames have candidates; all six absent frames have empty output. Visual overlay
review shows separated chair regions initially and a surviving clipped chair
mask as the view pans away. This is not a measured instance recall or ID-switch
score: physical identities and precise visibility counts were not annotated.
Colors in the review represent array order, not persistent identity.

First step: 488 ms. Warm median: 145 ms, excluding load, transfer and preparation.
The worker's checkpoint audit and current-frame read checks pass. GPU allocation
returns to zero. No robot actions or paid calls; no changes to the user's other
workload, system packages or instance lifecycle.

## Phase Decision

This adds a natural simultaneous similar-object candidate example to Phase 2,
complementing the natural sofa loss/return test. It does not qualify association,
identical-object crossings, reidentification, current metric geometry, or safe
manipulation. SAM local IDs are still scoped candidate identifiers. No object is
selected for an action and no `AssociationProof` is granted.

Do not rerun the sequence simply to accumulate detections. The missing boundary
is independent association under ambiguity, not the ability to emit multiple
masks. Native crossing/reentry and uncertainty qualification remain open.

## Retention

Prepared images and all raw mask outputs are local at
`runs/natural-chair-candidates-20260924-r1`. Hash-checked analysis and overlays:
`runs/natural-chair-analysis-20260924-r1`. The analysis checks every image/mask
hash, output shape, ID list and pixel-count summary. Preparation and analysis
scripts pass Ruff; no public runtime code changed.

| Artifact | SHA-256 |
| --- | --- |
| Frozen plan | `be9fbb9503efd3d3d973b57bc6c2fe837cf9bf12cc385fc6a3764c693f7acf06` |
| Pre-inference visibility review | `eb8c2c9a73b120fb0354f4a55d4c6753b8a0cc452791f47bc308900e439a4c8d` |
| Worker status | `fa9c96d7336b81274b602bbb1bb34b4fb025dd81a9216adbcb4b2e2cce0936f1` |
