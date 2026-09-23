# Geometry Restoration And Paused Recapture

## Results

The existing geometry pins were restored on the single RTX 4090 host, including
Open3D 0.19.0. A 33-frame retained pose replay admitted all 33 captures without
rejection. Its transforms match the old result to a maximum element difference
of `4.996003610813204e-16`. This verifies restored execution compatibility, not
localization accuracy. Fourteen focused geometry/queue tests passed remotely.

A subsequent **new native sensor-only diagnostic** captured three fresh renders
on reserved Halloween development instance 301, seed 0: initial, immediate, then
after an explicit three-second wait. No policy, model call or commanded action.
Normal initialization/settling physics preceded the captures; no simulation step
was issued afterward. The process exited zero and released the GPU.

| Measurement | Initial | Immediate | After wait |
| --- | ---: | ---: | ---: |
| Actual simulator time, seconds | 0.3416666845 | 0.3416666845 | 0.3416666845 |
| Render/get-observation, ms | 72.3 | 53.5 | 60.9 |
| Artifact writing, ms | 257.5 | 258.4 | 265.5 |
| Capture completion to publication, ms | 291.9 | 294.0 | 300.3 |

Capture IDs were distinct. Proprioception was exactly unchanged. Calibration
and RGB-D references were bound to each capture, with measured capture,
artifact/calibration, publication and pose-completion clocks. Simulator time
was read directly, never fabricated from capture sequence.

Both head-depth point-to-plane comparisons returned identity transforms, within
the predeclared 5 mm/0.5 degree stationary diagnostic bounds. **The underlying
head-depth pixels were identical across captures.** Distinct evidence IDs include
capture provenance; they do not imply different pixels. This is paused-scene
consistency, not noisy-sensor drift, motion accuracy or calibrated uncertainty.
Pair processing took 1.871 s cold and 0.568 s warm. These two samples are not a
latency distribution. Registration ran after all captures, not as a live fresh
pose publisher; the first timing includes lazy Open3D initialization.

Public RGB-D odometry initialized once and rejected both later captures with
`Odometry received stale observation` because simulation time did not advance.
That is expected current behavior, **not a passed localization update**. No
stale-decision bypass, clock rewrite or per-frame tracker reset was introduced.

## Protocol And Verification

Private protocol: `docs/PAUSED_RECAPTURE_PROTOCOL_20260923.md`, written before
execution. One attempt, three captures, 900-second timeout plus 30-second kill
grace, no automatic retries. Public baseline `f859b63`; clean BEHAVIOR source
`b1979916ec1549b10a4e65e630bc6504a9af1b00`, verified datasets and Isaac Sim 5.1.
No oracle object/robot poses or scorer state were needed. No captured knowledge
is reused as advance mapping for subsequent task episodes.

New private runner: `scripts/native_paused_recapture.py`, SHA-256
`574876bbd5dce07fbb62f9cf6b17e57e0291d3d91b11949377f146fb0bf9fe42`.
Hash matched before/after execution. Nineteen focused tests and Ruff passed;
full private suite: **648 passed, one existing skip**. One test initially named
the wrong Halloween task; its expectation was corrected before execution.
No public runtime code changed, and the public suite was not rerun for docs.

The numeric installation and replay are retained at
`runs/geometry-restore-20260923-r1`. The initial retained-data rsync failed due
to a missing parent directory; after creating it, transfer and checksum dry run
succeeded before replay. Known Pillow/websockets/packaging metadata exceptions
remain; numeric pinning does not conceal them.

Native evidence: `runs/native-paused-recapture-20260923-r1`, including initial
non-passing receipt, three capture records, two pose records and RGB-D files.
Copied locally; final receipt SHA-256:
`d275e90c274dc972180c59de1e33c79af18d2cd5c822b50db32fb020ad35e8fa`.

## Next Gates

Basic sensing and numeric runtime restoration no longer block experiments.
Full loss/reappearance and similar-object association remain unqualified. Phase 5
still needs moving-pose accuracy, lower-body clearance and whole-robot stopping.
Paused repeatability cannot replace them, and it grants no motion authority.
Paid shadow discovery/context work still requires separate budget authorization.
