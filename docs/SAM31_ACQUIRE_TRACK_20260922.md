# Acquire once, then track: retained diagnostic

## Result

On the previously missed live-fusion trace, image-mode candidate acquisition
followed by ordinary video tracking acquired the radio at action 416 and retained
ID 0 through all 12 observations from 416 to 768. A matched video-only baseline
acquired at 672 and returned four positive observations. Manual inspection of
all 25 overlays places the positive candidate masks on the radio; it does not
establish exact boundary accuracy or autonomous semantic identity verification.

Both conditions use the same pinned checkpoint, `a radio` prompt, exact upstream
file preprocessing, native RGB frames and video settings. The earlier legacy
preprocessing run acquired at 704; do not compare that number as if preprocessing
were held fixed. Within the original 384-512 comparison window, the new condition
has four positive boundaries out of five, versus zero for matched video-only.

## Causal procedure

Before acquisition, try each arriving observation with a fresh state and upstream
image-only admission. The first nonempty result starts tracking; the script does
not select frame 416 in advance or inspect later frames to choose it. Subsequent
steps explicitly restore video-mode admission. All acquisition results remain
unconfirmed candidates, with no motion authority or ledger success claims.

The diagnostic is an explicit opt-in on the private adapter. The production
worker, default preprocessing and video thresholds remain unchanged. No simulator
actions or paid GPT calls were made. It is not a deployed perception fix.

## Verification

- Source receipt SHA-256:
  `4d2155d4ef71523744a4b74117b57bb59c9e348990160a379054fa1f9f13f8d0`.
- Result receipt SHA-256:
  `4e201a7a3907debba13077cb34856f3422e356590fca5a9c68559f39baba24fa`.
- All 50 frame results match source image IDs and artifact hashes. Every logged
  raw-image read is the currently arrived frame, never a future frame.
- Mask dtype, dimensions, IDs and pixel counts verified independently from NPZs.
- Focused local tests: 22 passed. Touched Python files pass Ruff.
- Local full backup: `sam31-acquire-track-20260922-r1`, with `audit.json`, both
  25-frame review sheets, report and all 50 output NPZs.
- Retained warm post-416 step median: approximately 164 ms for acquisition-then-
  tracking and 140 ms for video-only. Includes artifact compression/write time;
  excludes simulator capture, contention and end-to-end live latency.

## Next gates

This answers whether lower-confidence initial acquisition can be retained by the
existing tracker. It does not qualify persistent identity under distractors,
disappearance, camera resets or full occlusion. Next run candidate loss and
reacquisition controls and require same-frame semantic confirmation before
binding a candidate to the task entity. Then replay surface fusion with the
new candidate masks before paying for another native rollout. Do not count
candidate geometry as confirmed target geometry.
