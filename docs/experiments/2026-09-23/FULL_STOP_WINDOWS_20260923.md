# Combined Stop-Window Replay

## Scope

Offline Phase 5 diagnostic on the completed paired-render short pulse. No native
actions, model calls, runtime gate changes or evaluator-pose inputs to the window
calculation. This is not stop or navigation qualification.

Inputs are the legal refreshed RGB-D/FK relative-base estimates at 30 Hz and all
22 named joint positions sampled at 120 Hz. Each ready window contains five
consecutive control intervals and twenty joint-position differences. No padding,
endpoint cancellation, timestamp shifting or future-window samples are used.

Limits match the pulse diagnostic: base planar 0.002 m/s, yaw 0.005 rad/s,
left wrist joint 7 at 0.006 rad/s, other arm/torso joints at 0.03 rad/s and fingers
at 0.005 m/s. Rates are interval averages, not bounds on instantaneous velocity.

## Results

- 25 action-ending rows; first four are not ready, leaving 21 full windows.
- Windows ending at actions 15-25 are stop candidates: 11 total.
- All windows containing the five commanded motion intervals are rejected.
- The initial five-hold window is also rejected: maximum joint-limit fraction
  is 1.032829, despite the recorded endpoint preflight passing. This argues for
  full-window measurement, not loosening thresholds.
- Final window: maximum planar rate 0.000024163 m/s, yaw rate 0.000014572 rad/s,
  maximum joint-limit fraction 0.034074.

The final base window has only 32.93 micrometres of allowable per-endpoint planar
position error under a worst-case two-endpoint error model. This is a tolerance,
not a calibrated measurement bound. Earlier observed 16.8 micrometre pose error
on this same trace is not independent qualification. Correlated errors and
within-interval motion remain unresolved. Raw runtime stop still fails, and no
replacement authority is enabled.

## Integrity And Verification

The analysis checks source completion, estimator/source hashes, paired-capture
lineage, exact sample counts, timestamps, rigid transforms, the complete named
joint set and contiguous callback/action indices. Its input estimator artifact
also contains retrospective truth, but only legal estimated transforms are used
by the window calculation. Regression tests cover missing/invalid samples,
out-and-back cancellation, substep joint motion and prefix causality.

Private artifacts:

- `runs/full-stop-windows-20260923-r1/receipt.json`
- `scripts/replay_full_stop_windows.py`
- `tests/test_full_stop_windows.py`

Input SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Native receipt | `925ba36ac0b82dc2ec9b34bb9f3e2cc966d973937bd41d06782079068a4a746f` |
| Joint substeps | `9048bc8fd3c4ad518d6a85aa2817f861fce8b73ae12c4c1e08ab5f4fcb428c72` |
| Refreshed estimate replay | `335826dd00fac513a0aa82b76258e0f13c6847d8ff416c2a78b4ff480ff2e6d4` |

Next: qualify uncertainty and observation timing before considering a live shadow
stop monitor. External clearance remains a separate unsolved gate. Do not repeat
the same pulse solely to reproduce these results.
