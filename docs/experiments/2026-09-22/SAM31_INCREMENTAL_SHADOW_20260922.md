# SAM 3.1 Incremental Tracking Qualification

## Frame-Alignment Correction

The initial arrived-frame replay and first moving run below are **not qualified
current-frame tracking results**. Their no-future-pixel check was too weak.
Visual review prompted a source audit: the base propagation loop treats
`max_frame_num_to_track` inclusively, but the multiplex detector computes an
exclusive end. Passing zero made its chunk empty; `end - 1` selected the previous
image while outputs were labeled with the current index. The access journal
confirms previous-image reads followed by current-image cache bookkeeping.

This was our incremental-adapter bug, not evidence that SAM necessarily drifts
this way. Correct source stamps on output files did not prove which image the
backbone actually processed. The historical timings below are retained for
debugging, not evidence of current-frame mask freshness or usable geometry.

The fix passes one while the actual arrived-frame count still clamps propagation
to a single frame. A new guard requires every raw-image read during that step to
use the emitted current frame; learned tracking memory remains permitted. A
regression test rejects the old previous/current read pattern. The strengthened
offline auditor also rejects the first live run, whose original narrow audit
was explicitly invalidated rather than silently overwritten.

## Corrected Replay

`sam31-arrived-fixed-20260922-r1` replays 14 lossless native views from the first
live run, delivering them one at a time. All 28 raw-image accesses select the
current emitted frame, with no future access. Thirteen views (384-768) report the
same radio ID; the partly clipped view at 352 has no detection. Warm median is
167 ms, peak allocated 6,058 MiB. Qualitative overlays show masks on the radio,
including the camera changes where the old adapter put masks on the table/sofa.
This is not a pixel-accuracy score or contact-geometry qualification. Replaying
from 352 rather than episode start also changes tracker history.

## Corrected Moving Run

`sam31-async-shadow-20260922-r2` completed the fresh seed-1 policy-only approach:
768 actions, 25 captures, no drops, no GPT and no classical actions. All 50
journaled raw-image reads used the current emitted frame. The strengthened
audit verified native/published observation equality, RGB/depth source hashes,
timestamps, mask artifacts and conservation of valid masked depth pixels.

| Measure | Warm median | Warm p95 |
| --- | --- | --- |
| SAM tracking | 252 ms | 284 ms |
| Observation ingress to mask/partition ready | 483 ms | 540 ms |
| Queue wait | 6.9 ms | 11.8 ms |
| Evidence read/validation | 44.5 ms | 47.2 ms |

All warm result ages were below 577 ms. Twelve captures (416-768) reported a radio
ID. On these positive captures, median tracking was 266 ms, depth partitioning
7.0 ms, and result age 527 ms. Peak sampled GPU memory was 23,112 MiB, leaving
1,464 MiB; the unchanged abort threshold was 23,552 MiB. All workers exited.
Visual review of the fresh-run overlays shows masks on the radio across the
turn/approach, without the large table/sofa offsets seen in the invalidated run.

This is sparse boundary sampling: median capture gap 7.62 s, maximum 24.74 s,
including simulation/policy work. It is not a continuous video-rate result.
The corrected timing now has verified current raw-image reads, but does not
establish pixel-perfect masks, calibrated identity confidence, contact geometry
or motion safety. Depth partitioning preserves pixels; it does not determine
which surface is the intended object part.

Keep SAM 3.1 local. Do not replace it to compensate for the resolved adapter bug.
Current-frame tracking compute is near the requested budget; the full path is
still above 300 ms. First return to sensor geometry/temporal-quality qualification;
only optimize encoding/decoding and observation cadence further if required by
the control experiment. A second GPU offers memory/isolation headroom, not a
guaranteed per-frame speedup. The bounded adapter still needs longer-stream and
reset/reacquisition qualification before general deployment.

The public acquisition runner now allows an isolated capture observer without
also loading a grounding worker, and exposes explicit lossless PNG compression.
Defaults and classical-motion gates are unchanged. Full public suite: 1,098
passed. Focused public/private observer, queue, launcher and frame-read tests:
57 passed. Ruff passes. Sensor traces and GPU workers remain private; this report
does not redistribute weights or simulator assets.

## Superseded Arrived-Frame Replay

The whole-clip predictor was not simply relabeled as streaming. A guarded private
adapter supplies only already-arrived pixels, advances the actual frame count,
and rejects all unavailable-frame reads. Its fixed metadata capacity is 32;
future frame pixels are absent. Outputs are not revised after emission.

Three failed probes are retained:

- A capacity-sized frame count caused an attempted read of frame 1 when only
  frame 0 existed; the guard stopped it.
- The interactive wrapper assumed propagation had completed and requested an
  uncached output for a new arrival.
- Nested tracker states retained the old frame count and produced no new frame.

The fourth probe uses the base propagation path and updates both frame counts.
It processed 14 original lossless native frames, actions 352 through 768, without
an unavailable read. All 28 journaled image reads had `requested < arrived`.
This is a bounded replay test, not yet a general-purpose streaming service.

| Measure | Result |
| --- | --- |
| Warm tracking median | 169.6 ms |
| First cold frame | 592 ms |
| New-track acquisition frame | 233 ms |
| Peak torch allocated / reserved | 6,019.8 / 6,500 MiB |
| Frames with a reported radio ID | Last 8 of 14 |
| First acquisition | Action 544 |

The ID persisted through action 768, but visual inspection showed displaced masks
at actions 640 and 672, including background above the radio. Persistent ID is
not continuous accurate segmentation or qualified geometry. No threshold was
retuned to conceal the missed early views or drift.

The earlier offline 14/14 result used whole-clip input and JPEG-derived pixels;
it is not a valid measurement of this lossless arrived-frame protocol. Both
protocol and encoding differ, so do not attribute all differences to causality.
Private receipts: `sam31-arrived-20260922-r1` through `r4`.

## Live Lossless-Encoding Test

A separate no-motion full-stack run opted into PNG level 1. It retained the
previous three independent text prompts per frame, specifically to isolate the
encoding change from the new tracking adapter. All three paused-world checks
passed; no actions or GPT calls were made. This is not a moving tracking result.

| Measure | Level-1 live result |
| --- | --- |
| Total capture | 178 / 212 / 212 ms |
| Render | 42 / 58 / 59 ms |
| Get observations | 9 / 16 / 16 ms |
| Evidence ingress | 127 / 138 / 138 ms |
| Warm three-prompt SAM worker | 526 / 540 ms |
| Warm observation age at return | 792 / 831 ms |
| Policy inference, actions discarded | 100 / 162 / 167 ms |
| Peak sampled GPU memory | 23,482 MiB |
| Native startup | 197.1 s |

The prior level-6 live capture took 404-448 ms, with warm result age 1.001-1.050 s.
These are separate resets with very small samples, not a statistical speedup
estimate. The lossless pixel equivalence check comes from the separate retained
array encoding test. No 300 ms end-to-end claim follows by adding isolated timing
numbers from different runs.

Only 1,082 MiB remained at the sampled memory peak, 70 MiB above the predeclared
1 GiB reserve. Single-GPU co-residency works for this stationary test but has
little margin. A second GPU can separate simulation from inference; it does not
by itself make one SAM update faster.

Private run: `sam31-fast-evidence-live-20260922-r1`, downloaded and verified by
checksum-rsync. All owned workers exited; the GPU instance was left running.

## Moving Shadow Protocol

Bounded test: the same frozen Behavior-Skill approach, seed 1, at most 768
policy actions and 25 boundary captures. No GPT, classical actions, DINO or SAM 2.
Native capture/stepping stay on their owning thread. PNG level 1 is explicit;
the public default remains level 6.

The native callback publishes an immutable audit record and replaces one pending
slot. It never reads segmentation results. The separate worker takes the newest
available capture, records skips, and resets tracking on a gap rather than
pretending unobserved continuity. Track IDs are namespaced by reset generation.
Input RGB, depth and intrinsics must come from the same validated observation.

Log observation, publication, dequeue, result-ready and archive-completion times;
separate decoding, tracking and depth partition timing. All valid masked depth
pixels must be conserved by partitioning. Partitions do not select a preferred
surface or prove a radio identity. The mask remains shadow-only even if fast.

The existing 23,552 MiB sampled memory cutoff and bounded worker lifetimes remain
active. A capacity abort is a result, not permission to lower the reserve. There
is no new clearance, localization, contact or benchmark-motion authorization.

## Superseded Moving Run Timing

`sam31-async-shadow-20260922-r1` completed 768 policy actions and processed all
25 captures, with zero queue drops and zero GPT/classical actions. The worker
reported no unavailable-pixel reads. All owned processes exited. This is an
operational shadow result, not radio success or continuous high-rate tracking.

| Measure | Warm median | Warm p95 |
| --- | --- | --- |
| SAM tracking | 245 ms | 277 ms |
| Observation age when mask/partition ready | 484 ms | 545 ms |
| Queue wait | 8 ms | 12 ms |
| Evidence read/validation | 45 ms | 46 ms |

The first cold result age was 842 ms. Twelve observations, actions 416-768,
returned a radio ID. For those positive observations, median tracking was 259 ms,
depth partitioning 7.3 ms and result age 530 ms. Empty-mask frames do not count as
successful radio perception. Peak sampled GPU memory was 23,208 MiB; peak torch
allocated/reserved was 6,051/6,502 MiB. Sampling can miss brief memory peaks.

The trial captures at 32-action boundaries. Its median wall-time capture gap was
7.53 s, with a 24.06 s maximum. Those gaps include simulation and policy work;
they are not segmentation latency. The 484 ms figure starts at observation
ingress and ends when derived arrays are ready, excluding subsequent artifact
archiving. It is not a measured 2 Hz or 30 Hz live perception stream.

No model replacement is justified by latency alone here. Tracking is now near
the requested compute budget, while full observation-to-result time remains
above 300 ms. Encoding/decoding and shared-GPU execution still matter. A cloud
endpoint has not been benchmarked and would add transport/queue variability.
