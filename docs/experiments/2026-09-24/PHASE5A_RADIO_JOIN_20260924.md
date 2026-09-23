# Phase 5A Radio Fusion Attempt

## Result

One no-action stationary run used a legal RGB-D capture, the derived local
pose, and the SAM 3.1 radio prompt at the same capture boundary. The capture
and lineage checks passed, but SAM returned no radio mask support. The join was
therefore rejected with `support=0`; no target geometry was published and no
motion was authorized.

- Actions: 0
- Paid calls: 0
- Capture binding: valid
- Pose scope: single-camera local origin only
- SAM radio support: 0
- Join: rejected

The failed receipt is retained on the GPU host as
`runs/stationary-sam-radio-20260924-r2/`. It is not silently retried. The
owner receipt initially reported the default prompt name even though the child
used `radio`; that bookkeeping defect is fixed in the local runner for future
runs.

## Decision

This does not qualify Phase 5A. It isolates the immediate missing condition:
the stationary scene/capture did not provide a radio-bearing mask. A future
positive-fusion run must first acquire a legally observed target-bearing frame
or use a predeclared retained target-bearing capture, then require matching
RGB, depth, pose, and result lineage. Do not interpret this as a SAM quality
ranking or repeat it as a generic prompt sweep.
