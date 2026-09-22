# Situated Tracking Reset Diagnostic

Date: 2026-09-22. Retained-image GPU diagnostic, not live identity, motion,
task-success, or full Situated V2 integration qualification.

## Protocol

Replayed the 25 lossless head-camera observations from corrected trace
`sam31-async-shadow-20260922-r2` chronologically, one arrival at a time. Used
the existing pinned SAM 3.1 weights, corrected raw-image-index guard and unchanged
`a radio` prompt. No simulator, policy or GPT was loaded.

Two conditions ran sequentially on the idle RTX 4090:

- Uninterrupted: existing 32-frame-capacity tracker, all 25 arrivals.
- Reset diagnostic: capacity 8, fresh state before indices 8, 16 and 24
  (source action sequences 256, 512 and 768). IDs are namespaced by condition
  and reset generation, never treated as persistent entity IDs.

The shorter capacity exercises resets within available data; it does not test
a stream longer than 32 frames or install automatic resets in the live worker.
Conditions shared predictor weights but used independent tracking state. Order
was not balanced. A 300-second external timeout bounded the completed run.

## Results

| Measure | Uninterrupted | Reset every 8 |
| --- | --- | --- |
| Frames processed | 25 | 25 |
| Positive radio-mask frames | 12 | 11 |
| First detection, source action | 416 | 416 |
| Missing after initial detection | None | 768 |
| Current-frame raw-image reads | 50/50 | 50/50 |
| Tracking median excluding first frame | 160 ms | 166 ms |

Reset frames took 200, 214 and 200 ms. At sequence 512, the fresh tracker
immediately reacquired the radio. At 768, it returned no object while uninterrupted
tracking retained a visibly aligned mask. No later frame exists, so recovery
delay is unknown. Resetting while the radio was absent at 256 did not invent
a detection. This is one paired diagnostic, not a reset-failure rate estimate.

Where both conditions produced masks, same-image mask IoU was 0.955-1.000:
agreement, not pixel accuracy. Visual review of five paired full-frame/crop
panels supports alignment; no pixel ground truth was supplied. Peak torch
allocated/reserved memory was 6,051/6,502 MiB without simulator or policy.
These timings do not replace the live co-residency measurements of 252 ms
median tracking and 483 ms median ingress-to-result latency.

## Identity and Geometry Limits

The trace has no post-acquisition natural disappearance, similar-object crossing,
or independent identity labels. All 25 head-camera calibrations lack camera-to-map
extrinsics. Therefore metric cross-view association is not established; no
all-true proof was supplied to Situated V2 simply because SAM kept local ID 0.

All positive-mask pixels had valid depth in the accepted 0-10 m range, which
does not prove correct surface membership. The first mask touches the image
edge. Early positive frames have zero unwarped overlap with the preceding
detection as the camera turns. Simple screen-space overlap would therefore
reject apparent continuity even in this easy trace. Calibrated geometry and
ambiguity handling remain necessary. Recorded optical-axis depth quantiles
are not interpreted as distance to the robot.

## Decision and Next Gate

Keep SAM 3.1 and its validated history; do not reset periodically merely to
simplify bookkeeping. Never equate a reset's new local ID with the old entity
without association evidence. If reacquisition fails, retain remembered semantics
but mark current geometry unavailable; do not copy an old mask into a new view.

Next collect post-recognition loss/reappearance with legally estimated camera
poses and explicit confidence/epochs. Keep policy and motion gates unchanged.
Occlusion/distractor testing, longer-stream qualification and the native Situated
association bridge remain incomplete. Localization, clearance and stopping
still precede strict hybrid motion comparisons.

## Receipts

- Private run: `situated-reset-replay-20260922-r1`. All 50 mask artifacts and
  the report are backed up locally; source/mask hashes and lineage audit pass.
- Source receipt SHA-256:
  `3a7a76acc7c47e9e835c66b38564c65e315caa4c41cca7d81ca9ccc3e972874a`.
- Replay report SHA-256:
  `3863ca74d0bbf127a1ae52ad7d4b9370434da0c060aeb414881c075c2bf4adad`.
- Focused private replay/streaming/queue tests: 14 passed; Ruff passes.
- Zero new robot actions or paid GPT calls. The GPU worker exited; subsequent
  inspection reported 0 MiB in use. Instance remains running as requested.
- Licensed observations and private worker code are not published here.
