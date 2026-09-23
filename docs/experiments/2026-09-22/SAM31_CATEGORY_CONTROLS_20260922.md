# Fixed-category cross-trace and interruption controls

## Frozen configuration

Prompt `radio`, upstream file preprocessing, existing pinned SAM 3.1 checkpoint,
unchanged confidence thresholds. No color adjective, new GPT call, simulator
motion, or production configuration change. GPU experiments were serialized;
CPU provenance/render checks ran while the second GPU experiment executed.

## Cross-trace result

Replayed all 25 observations of `sam31-live-pose-cache-20260922-r1`, separate from
the five-frame prompt-development trace. Both video-only and image-acquire-then-
video modes first acquired at action 384 and returned masks on all 13 observations
from 384 through 768. No earlier output masks. Image-mode acquisition provides
no measured advantage on this trace. Visual review places masks on the radio.
This remains the same scene and asset, not unseen-task or independent-object
generalization; this trace was previously inspected in other diagnostics.

## Interruption controls

Reused the development trace with two explicitly distinct plans:

- **Forced resets:** preserve chronological pixels; discard tracker state before
  observations 448 and 576. Both reset frames reacquire immediately. The condition
  returns masks on all 12 observations from 416 through 768.
- **Scene switch:** after native observation 480, insert original off-target
  observations 0, 32 and 64, then resume at 512. All three inserted frames return
  empty masks. The mask returns on the first resumed frame, 512, and remains on
  the radio through 768. This is an intentionally reordered stress sequence, not
  physical camera motion, a causal native episode, or natural occlusion evidence.

Tracker IDs are not persistent task entity IDs. Reset generations are recorded;
reused numeric ID 0 across resets does not establish identity continuity.
No hard same-class distractor was present. Neither control qualifies semantic
identity under object substitution or prolonged disappearance.

## Evidence

Private retained runs and full local copies:

- `sam31-category-cross-trace-20260922-r1`: 50 results; source SHA-256
  `2078fdc61b310fc749ba98b464abf24bad1e8aa2ab20cf68ed516c701e2189ae`;
  report SHA-256
  `6a9458aca22ea8a3a9e75d3490f3fe4f16e8db220c24add2880d70d235347692`.
- `sam31-category-stress-20260922-r1`: 53 results; source SHA-256
  `4d2155d4ef71523744a4b74117b57bb59c9e348990160a379054fa1f9f13f8d0`;
  report SHA-256
  `1cedbef1c64083a7d3bfac8fd5b1b1e2a216afd3a2bcf5bfe9c6724010ff6359`.

All 103 outputs pass source image-ID, artifact hash, mask dimensions/dtype/pixel
counts and current-arrival read checks. Synthetic insertion/reset plans are
checked explicitly. Review sheets were inspected for acquisition, reset and
scene-switch conditions. Focused local tests: 25 passed. Changed scripts/tests
pass Ruff after import formatting.

## Next step

Stop expanding prompt tuning on this asset. Keep the fixed category prompt as an
experimental candidate; join replayed masks to same-observation depth and pose
for offline surface analysis. Do not reuse original live availability timestamps
to claim the replay masks were available during the native run. Preserve unknown
identity until separately confirmed, and leave motion gates intact. Hard
distractors and realistic loss/reappearance remain open qualification items.
