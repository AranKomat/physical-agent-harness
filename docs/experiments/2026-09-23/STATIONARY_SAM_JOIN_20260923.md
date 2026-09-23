# Stationary Native SAM Join

Scope: one fresh native head RGB-D capture, SAM 3.1 acquisition with the frozen
`fireplace` prompt, depth-surface partitioning and causal publication checks.
No policy actions or paid API calls. Simulator initialization/reset settling
is separate from commanded motion. This is not Phase 5A qualification, even
if the single-frame smoke passes: moving localization, multi-view fusion,
physical identity, clearance and stopping remain unqualified.

## First Attempt

Private artifact directory: `runs/stationary-sam-join-20260923-r1`.
SAM loaded successfully; all 1,589 learned parameters matched the pinned
checkpoint. Native initialization and fresh capture completed. Before inference,
the test adapter passed NumPy calibration scalars into the public `Intrinsics`
contract, which intentionally accepts Python numbers. It raised
`ValueError: Invalid number`. No segmentation or freshness result was obtained.

The owner recorded failure, forced cleanup and reaped its workers. An independent
GPU process query found no compute workers. The whole small run was copied locally
and the checksum rsync comparison was empty. Consumed source/checkpoint hashes
were unchanged. The failure receipt remains intact.

## Correction

The private adapter now converts numeric calibration scalars to Python floats
at the boundary, rejecting malformed, nonnumeric and nonfinite matrices and
preserving public focal-length/principal-point checks. Ten regression cases
cover NumPy numeric types and invalid inputs. The stationary/preparation test
selection passes 49 tests; changed private files pass Ruff.

A separately named `stationary-sam-join-20260923-r2` attempt uses this correction
without changing the prompt, masks, freshness threshold or motion gates.
The first attempt is not a model failure.

## Corrected Attempt Result

The second attempt passed the declared single-frame component check:

- One candidate mask, with 29,710 valid depth samples across 16 retained patches.
- SAM acquisition: 0.8785 seconds; capture-to-join publication: 1.3032 seconds,
  including artifact writes, below the frozen 2-second bound.
- Sim time remained 0.3416666845; proprioception remained unchanged.
- All 1,589 learned parameters matched; consumed source/checkpoint hashes stayed
  unchanged. Only frame 0 was accessed, after that frame had arrived.
- Peak sampled aggregate GPU memory: 16,516 MiB, below 23,552 MiB.
- Zero commanded actions, zero paid calls; workers reaped without forced cleanup.
  Independent GPU query found no remaining compute processes.
- Whole run copied locally; checksum rsync comparison empty.

The fresh RGB visibly contains the fireplace, but the mask is a candidate,
not independently qualified physical identity or a collision surface. Reported
patch coordinates use an initialized camera-local origin, not measured global
robot pose. No positive multi-view or motion claim follows from this result.
Phase 5A remains incomplete.

Full private suite after the correction: **867 passed, one existing skip** with
`PYTHONPATH=scripts:src:../../physical_agent_harness_scaffold`. An initial bare
pytest invocation failed collection because the scripts directory was absent
from its import path; the configured suite passed. Public production code was
not changed by this correction.

## Subsequent Environment Incident

An automatic Ubuntu update was later found to have overlapped this test.
The SAM log places acquisition at 06:41:11 UTC; dpkg records NVIDIA library
replacement at 06:42:19 UTC. The successful result is retained, but its timing
may include background package-update contention and is not a clean isolated
latency benchmark. Source/checkpoint hashes did not cover OS package state.
Future stationary runs now check package-manager activity, GPU driver agreement,
boot identity and CUDA/NVML library hashes before/after execution. This change
does not retroactively qualify the earlier environment or authorize a repeat.
