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

## Evidence and Boundaries

- Native receipt SHA-256:
  `b398e1ae27dc2f69985bcd829d11ffc2ad8c7964f3af0b2935d9f40eaa7fa965`.
- Pose receipt SHA-256:
  `c26834b67cb786d5dfb17b5fc4e9e0a2fa46d419ed1880d7703343c4514d2ac1`.
- Full completed run copied locally; checksum rsync found no differences in
  remote source files. Local pose and SAM lineage audits passed.
- Public suite: 1,234 tests passed. Private pose queue/audit tests: 13 passed.
- Cached live rerun must establish result age before promoting this optimization.
- No independent drift truth or qualified base transform follows from depth-fit
  success. Outputs still have no clearance or motion authority.
