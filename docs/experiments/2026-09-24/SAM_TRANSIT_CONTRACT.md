# SAM Transit Contract

CPU-only retained replay, 2026-09-24. No new native actions or paid calls.

The exploratory executor now accepts an explicit `SAMTransitTarget` consumer
instead of requiring legacy segmented Grounding-DINO output. The default legacy
path remains unchanged; the old private owner's unsupported transit flags remain
blocked before launch. This is not yet a working live owner.

The consumer checks exact episode/frame/RGB/depth/time binding, tracker generation
and ID, causal publication clocks, two-second age, archive hash and path, mask and
partition alignment, valid measured depth, robot-relative FK transform and the
existing near-hand/base rejection. Accepted proposals are journaled in executor
samples. Existing action, abort, braking and continuity limits are unchanged.
An accepted proposal carries no identity, clearance or motion certification.
The live owner must still verify the model/source pins and task-to-track selection.

## Retained Evidence

Source: `live-fusion-dense768-20260924-r5`, 25 retained captures.
Private receipts: `sam-transit-contract-20260924-r1` and `r2`.

The first implementation required exactly one connected depth patch, rejecting
all target-bearing frames. That was unnecessarily restrictive for fragmented
depth. A separately recorded revision requires one patch containing at least
80% of valid masked depth; it never averages disconnected patches. This is an
exploratory heuristic, not a calibrated identity or collision guarantee, and
its same-trace adjustment is not held-out validation.

The revised replay accepts 13/25 frames. Eleven lack a unique candidate; frame
416 is rejected for an ambiguous split surface. Frame 704 yields 2,925 points
in patch 17, 82.00% of valid support. Its median in the measured robot-base frame
is approximately `[1.14071, -0.31776, 0.55685]` metres. This is a visible surface,
not an object center or a target that may be reused in a fresh episode.

Replay consumption uses the historical archive-availability time, explicitly
not present wall time. It does not establish live freshness or tracking continuity.
The executor's SAM dispatch/limits are covered by mocked integration tests;
the real retained replay exercises decoding, binding, FK and surface extraction.

## Next Execution Work

Wire fresh synchronous SAM results into the native capture path, pin one tracker
selection for the probe, and verify imports/model pins in every child environment
before launching acquisition. Do not run another detector-only acquisition.
Measure live capture-to-command age and preserve failures instead of refreshing
timestamps. No strict phase has advanced from this contract work.
