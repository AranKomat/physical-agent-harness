# Live Pose Shadow Timing

Date: 2026-09-22. This tests pose delivery timing, not localization accuracy,
task success, clearance, or motion authority.

## Baseline

Private run `sam31-live-pose-20260922-r1` ran the frozen Behavior-Skill policy
for 768 actions, with zero classical actions and zero GPT calls. SAM received
the usual 25 boundary observations. An independent CPU FIFO received all 33
dense observations at actions 384-512, every four actions. No dropped frames,
automatic pose resets, or changes to the existing registration gates.

All 33 pose estimates passed existing fit/step checks, and all evidence-lineage
checks passed. **Only 14/33 results arrived within the two-second age bound.**
The owner receipt's `passed` means the bounded run completed, not that freshness
or a benchmark task passed.

| Live measure | Median | p95 | Maximum |
| --- | --- | --- | --- |
| Pose update processing | 1.224 s | 1.346 s | 1.373 s |
| Publication-to-dequeue wait | 0.707 s | 1.089 s | 1.122 s |
| Observation-to-pose-ready age | 2.074 s | 2.582 s | 2.638 s |

SAM processed 25/25 boundary captures with 50/50 current-frame raw reads.
Warm tracking median was 244 ms; ingress-to-mask/depth age median/p95 was
502/556 ms. Peak sampled GPU use was 23,132 MiB, below the unchanged 23,552 MiB
cutoff. All owned processes were reaped and GPU use returned to zero.

## Measured CPU Bottleneck

Offline profiling on the same remote CPU and the saved 32 depth pairs found:

| Component | Median per pair |
| --- | --- |
| Cloud creation and voxel downsampling | 120 ms |
| Normal estimation for both clouds | 604 ms |
| ICP | 405 ms |
| Information matrix | 94 ms |
| Entire estimator | 1,196 ms |

These are per-component medians, not additive percentile guarantees. This
profile runs without concurrent simulation and is not a live latency result.

Added opt-in `CachedPointToPlane`: retain exactly one prepared depth cloud and
reuse it only when the next previous-depth array's content, dtype and relevant
intrinsics match. Copy the depth cache key so caller mutation cannot change it.
Recompute ICP, the information matrix and acceptance on every pair. The default
estimator remains uncached. No geometry resolution, iteration cap, fit threshold,
step threshold, information threshold, or freshness threshold was relaxed.

On all 32 saved pairs, local cached replay matched original accumulated transforms
within absolute tolerance 1e-8. Local median update time was 933 ms uncached and
690 ms cached. This is an offline Mac comparison, not proof of live speedup.

## Cached Live Follow-Up

`sam31-live-pose-cache-20260922-r1` completed the same declared protocol with
opt-in cached preparation. All 33 estimates passed existing checks and all
33 were available within two seconds. Pose and SAM lineage audits passed.

| Live measure | Median | p95 | Maximum |
| --- | --- | --- | --- |
| Pose update processing | 0.826 s | 1.039 s | 1.226 s |
| Publication-to-dequeue wait | 0.006 s | 0.011 s | 0.155 s |
| Observation-to-pose-ready age | 1.044 s | 1.265 s | 1.428 s |

SAM again processed 25/25 boundary captures with 50/50 current-frame reads.
Warm tracking median was 247 ms; mask/depth result age median/p95 was 481/558 ms.
Peak sampled GPU use was 23,148 MiB. Policy runtime was 217.36 s for 768 actions.
Workers were reaped and GPU use returned to zero; the instance remains running.

These are two separate trajectories with one run per configuration, not a
statistically replicated benchmark. Exact-input offline equivalence supports
the cache semantics; the live follow-up establishes timing only for its bounded
window. The 33 correlated observations are not 33 independent experiments.

Cached native receipt SHA-256:
`2078fdc61b310fc749ba98b464abf24bad1e8aa2ab20cf68ed516c701e2189ae`.
Cached pose receipt SHA-256:
`862a35e8612046ac9354e9f2559dd960180abd9e4989ec9efcafbdf048584cc8`.

## Same-Frame Metric Binding

A subsequent offline audit joined SAM masks at actions 384, 416, 448, 480 and
512 to the exact RGB/depth IDs, episode stamps, and live camera-pose estimates.
Availability is the later of pose readiness and mask archive completion; it is
not backdated to observation time. All five joined artifacts were available
within 1.21 s of observation. Six join tests cover matching, cross-frame rejection,
and stale-pose rejection.

Deprojecting the selected valid depth pixels into the estimated local frame gives
visible-surface medians within roughly 1 cm across those views. This is internal
consistency only: they are not object centers, independent pose-error measurements,
or proof of identity. Surface spans remain broad (about 0.37-0.43 m, 0.20-0.21 m,
and 0.48-0.50 m along the three local axes); no contact geometry is certified.
The join is offline, not yet a live fused-result consumer. No control input changed.

## Evidence and Boundaries

- Native receipt SHA-256:
  `b398e1ae27dc2f69985bcd829d11ffc2ad8c7964f3af0b2935d9f40eaa7fa965`.
- Pose receipt SHA-256:
  `c26834b67cb786d5dfb17b5fc4e9e0a2fa46d419ed1880d7703343c4514d2ac1`.
- Full completed run copied locally; checksum rsync found no differences in
  remote source files. Local pose and SAM lineage audits passed.
- Public suite: 1,234 tests passed. Private pose queue/audit tests: 13 passed.
- Cached live freshness passes this bounded test; next bind same-frame masks,
  depth and pose for metric multi-view analysis, still without motion authority.
- No independent drift truth or qualified base transform follows from depth-fit
  success. Outputs still have no clearance or motion authority.
