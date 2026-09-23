# SAM Scripted Loss And Similar-Object Diagnostic

## Protocol

One fresh seven-frame SAM 3.1 run on retained scripted sensor images, with no
robot actions or paid calls. This addresses an unexecuted scripted diagnostic
from Phase 2, not natural occlusion, crossing, continuous displacement,
calibrated geometry or physical association qualification.

Predeclared inputs: fixture indices 0, 2, 3, 4, 5, 6, 7 from the frozen r2
association protocol. The fixed prompt is `pumpkin`; one initialization, no
prompt sweep, reset, retry or outcome-dependent frame selection. The existing
bounded worker enforces deadlines and arrived-frame-only raw reads. The frozen
plan fixes seven steps. Script phase times are not labeled native sim time.

Only exact RGB files enter inference. Scripted entity/place/event labels,
expected outcomes, prior masks and unpaired depth are excluded. Official-file
preprocessing and initial image acquisition precede propagation. Every output
identity remains unknown; no association proof or motion authority is granted.

Checkpoint SHA-256:
`0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`.
SAM source: `2345a4ad109ac29c569da749c91d84f10dc08c40`.
All 1,589 learned tensors match the checkpoint after loading.

## Results

| Fixture | Local IDs | Mask pixels | Step latency |
| --- | --- | --- | ---: |
| 0: initial room | 0, 1 | 235, 104 | 775 ms |
| 2: changed view | 0, 1 | 269, 106 | 181 ms |
| 3: scripted displacement | 0, 1 | 274, 112 | 135 ms |
| 4: outdoor/off-target | none | none | 134 ms |
| 5: near wall | none | none | 134 ms |
| 6: hallway | 0 | 1,026 | 135 ms |
| 7: room revisit | 0 | 371 | 134 ms |

Seven steps completed without worker error, timeout or retry. Warm median is
**134.23 ms**, including GPU synchronization but excluding model startup,
capture, geometry and publication. The otherwise idle host has one RTX 4090.
This is not end-to-end pipeline latency.

Visual review of source images with mask-derived boxes supports alignment with
visible pumpkins. This is not pixel ground truth, instance recall, contact-boundary
accuracy or correct reidentification. The distant masks are particularly small.

## Interpretation

SAM retains two candidate regions, emits empty results on these off-target views,
and emits a candidate again after the discontinuity. Local ID 0 reappearing in
another view does not prove it is the same physical object. This reinforces the
need for independent association after loss; it proves neither an identity
switch nor correct continuity. No canonical identities were assigned.

Without paired calibration/depth and continuous natural motion, this run cannot
close the remaining native Phase 2 gates. Invalidation of previously valid
geometry remains a separate integration qualification. Do not repeat this
scripted sequence as a substitute for collecting the missing natural evidence.

## Verification And Artifacts

Private run: `runs/scripted-sam-loss-20260923-r1`.
Review/analysis: `runs/scripted-sam-loss-analysis-20260923-r1`.
Local preflights r1/r2 are retained; r2 adds a transfer list before inference.
Remote preflight passes. Source/runtime hashes remain unchanged. The roughly
220 KB run is copied locally with an empty checksum-rsync comparison. The worker
exited and no GPU compute process remained afterward.

Private suite: **968 passed, one existing skip**. The 27 focused tests cover
the existing worker plus fixed-plan preparation and overwrite refusal, not
visual accuracy. Focused Ruff passes. No motion gate or call ceiling changed.

| Artifact | SHA-256 |
| --- | --- |
| Run report | `1aa5f876e21eb68ef388b8360ff66eb72d3fb750fa130229f7f918f60275d173` |
| Worker status | `6c8aed97e06b24d89ebe30305e0559feb96f95bf0b8fe9e96f26bde571f651be` |
| Inference plan | `4f5773c1be5107e652597de739a36ee046ba31f60c7ee858037a3f87fa69db45` |
