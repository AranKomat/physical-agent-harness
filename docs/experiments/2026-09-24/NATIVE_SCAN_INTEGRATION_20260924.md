# Native Sensing Scan Integration

This is exploratory Phase 5/7 work, not strict navigation, arm qualification,
task success, or a model comparison. Unknown external clearance remains unknown.
No paid inference was authorized or dispatched in this follow-up.

## Integration changes

- Added fresh admission checks for pinned robot assets, linked endpoint/path/scene
  receipts, full certified path-interval coverage, all 17 sampled scene fractions,
  matching depth evidence, and the 0.003-rad tracking envelope.
- Paused recapture must preserve simulation time, exact finite proprioception,
  camera set, intrinsic/extrinsic calibration, and session/epoch. New timestamps,
  sequence numbers and evidence IDs are required/expected, not calibration changes.
- Fixed live tuple versus JSON-list comparison of proprioception. Exact numeric
  equality remains required. The actual retained failure capture passes after
  reconstructing the live Pydantic observation; a 1e-15 value change is rejected.
- Added five consecutive settled preflight observations before outbound commands.
- Emergency hold monitors preserve the original approved joint-departure and
  held-joint drift origins. They cannot clear the outbound failure latch or
  authorize resumed scanning. Raw base feedback is checked during holds.
- Added a single-owner launcher with a scan lock, early worker-exit detection,
  dependency preflight, source hashes, durable owner logs, unique output
  directories, atomic admission publication, and receipt-based result validation.
  Isaac exit code zero alone is explicitly not success.

The native environment was missing yourdfpy. Version 0.0.60 was installed with
`--no-deps` into a separate private dependency directory; existing packages and
system packages were not changed. The three pinned robot geometry files were
copied and hash-verified. FK and Open3D 0.19.0 load in the native environment.
CPU geometry checks use the existing GraspGenX environment, not grasp inference.
That worker currently includes native site-packages for receipt parsing; this is
an environment-coupling limitation, not a new qualified standalone environment.

## Pre-action failures and audit limitation

Repeated setup starts failed on missing deployed helper modules/receipts,
incorrect source-root wiring, duplicate directory creation, and paused-capture
comparison bugs. The actual audited simulator source is
`references/BEHAVIOR-1K` at `b1979916ec1549b10a4e65e630bc6504a9af1b00`,
not the non-git public harness deployment. An initially created self-generated
deployment receipt was not evidence of that revision; its unused checker and
remote receipt have been removed. The real git revision/cleanliness check remains.

Several setup starts incorrectly reused `native-sensing-scan-20260924-r1` and
overwrote earlier captures. Only the final r1 capture/receipts survive locally.
Console failures remain in the work thread, but this is not a complete per-start
archive. Do not treat these starts as independent trials or a success-rate sample.
The launcher now rejects existing output paths; r2 has separate owner logs.

The final retained r1 records zero attempted/completed control actions. Its fresh
geometry checks passed endpoint collision rejection, conditional continuous
self-separation (43 nodes), and the sampled scene test (zero outside-start hits;
335 ambiguous near-start hits). Native admission then rejected the tuple/list
representation mismatch. An earlier bytecode-cache explanation was speculative
and incorrect; exact in-memory/serialized representation was the identified bug.

## Verification and remaining work

Focused admission/monitor/executor/observer/launcher tests: 62 passed.
Full private suite: 1,224 passed, one existing skip. Changed files pass Ruff.
These tests do not prove native motion, stopping, contact safety or task benefit.

## Retained native results

**r2:** Fresh admission passed, but monitor construction rejected NumPy scalars
returned by the FK helper. Zero actions. Scalar normalization now accepts finite
real values without changing their numeric values, while rejecting booleans,
strings, complex and nonfinite values. The complete r2 directory and owner log
are backed up locally with checksum comparison showing no content differences.

**r3:** The scan was admitted and executed, then aborted without retry:

| Measurement | Result |
| --- | --- |
| Preflight holds | 20, accepted |
| Outbound scan actions | 20 dispatched; action 40 triggered the latch |
| Reserved holds | All 60 completed with healthy joint feedback |
| Actual control actions | 100 attempted and completed by evaluator |
| Actions with accepted complete feedback | 99; failed outbound action retained |
| Logged physics samples | 160 outbound/preflight + 240 reserved hold |
| Failure | Joint 7 interval speed 0.151005 rad/s exceeded 0.15 rad/s |
| Command rate at failure | 0.064788 rad/s |
| Whole-control-interval measured average | 0.064654 rad/s |
| Tracking error through failing sample | At most 0.000982 rad, below 0.003 rad limit |
| Maximum recorded departure including holds | 0.022065 rad |
| Reserved-hold interval speed | At most 0.001642 rad/s |
| Reserved holds meeting raw settled predicate | 60/60 |

The speed peak was concentrated in the first physics substep after the new
position command. The following three joint-7 interval speeds were approximately
0.06563, 0.02912 and 0.01286 rad/s. This supports a position-step/servo-response
timing explanation; it is not proof that all commanded speeds or postures are
qualified. Do not raise the speed threshold merely because this miss was small.
Across actions 36-40, peak-to-command-rate ratios were 2.3297-2.3308. This is a
repeatable short-window response pattern, not just one noisy threshold crossing.
It has not been tested across the full posture range. Lowering command rate for
the same 1.504-rad endpoint also lengthens the profile; the 600-action ceiling
must be rechecked rather than silently expanded or the scan truncated.

The first-reference legal RGB-D/FK observer accepted its initial sample and 39
completed control boundaries, with no base-drift rejection. Reported displacement
was near zero (maximum 3.82 micrometers), not a validated accuracy claim. The
failing action skipped visual recapture, and reserved holds had raw base feedback
checks but not continuous RGB-D base estimation. Full stopping remains unqualified.

Native `complete=true` means its bounded routine reached termination; r3 has
`scan_completed=false`, `execution.failed=true`, `outward_complete=false`, and
`hold_complete=true`. The owner correctly reports failure despite Isaac returning
exit code zero. The GPU worker exited and released its GPU allocation. No rental
stop/reboot or system-package change was made.

No full sensing sweep, useful new clearance coverage, grasp, policy comparison,
or task success is established. Phase 5/7 remains partial. The next step is
offline command-response analysis and a re-budgeted sensing profile/viewpoint,
not relaxing the current gate or automatically repeating the aborted sweep.
The two existing survey candidates below 1 rad departure both have zero predicted
unblocked low-body samples, so they are not useful substitutes solely because
they are shorter. Any new candidate still needs fresh geometry and sensor checks.

The broad sequence is unchanged: qualify the native execution path before
matched hybrid trials and task-level GPT/memory work.

## Artifact backup

The complete r3 trace and owner log were archived without model weights (575 MB
uncompressed, approximately 401 MB compressed), downloaded to the private Mac
lab, and verified against the remote SHA-256:

`0c5f6ae6bb1b9ff0064443e50edef943177f255e06ff975ea9d804053392cb2b`

Private paths: `runs/native-sensing-scan-20260924-r3/`, the sibling `.owner/`
directory, and `runs/native-sensing-scan-20260924-r3.tar.gz`. Raw traces and
sensor assets are not added to the public git repository.
