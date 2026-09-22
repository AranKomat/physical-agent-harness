# Dense Async Observation and Pose Replay

Date: 2026-09-22. Fresh policy-only native acquisition followed by CPU audits.
This advances bounded sensor timing, not strict hybrid motion admission.

## Protocol

Used the existing frozen Behavior-Skill approach: seed 1, 768 policy actions,
32-action chunks, unchanged instruction and codec. Added the existing opt-in
dense capture schedule, every four actions at 384-512, to the corrected SAM 3.1
asynchronous shadow configuration. No new classical actions, GPT calls, policy
training, model replacement or relaxed gate.

Capture uses lossless PNG level 1. SAM still receives only the usual 25 boundary
captures; the additional 28 captures are retained for sensor analysis, not sent
to SAM or used as extra policy inputs. Thus the dense window contains 33 views
and 32 intervals. This does not claim continuous dense perception for the entire
episode or a new faster segmentation model.

The owner retained its 23,552 MiB sampled-memory cutoff, bounded lifetimes and
worker cleanup. The native run passed with 768 policy actions, 25 boundary
captures and all 28 additional captures. All owned workers exited.

## Timing and Geometry

The comparison is to the earlier dense acquisition with synchronous grounding.
Both use the same declared window and existing thresholds, but they are separate
trajectories, not a matched-input or statistically replicated latency experiment.
The bundle of pipeline changes is not decomposed into individual causal effects.

| Check | Earlier dense trace | New async dense trace |
| --- | --- | --- |
| Adjacent depth-fit passes | 32/32 | 32/32 |
| Existing camera step-bound passes | 32/32 | 32/32 |
| Wall-time gap at most 2 s | 28/32 | 32/32 |
| Stateful replay captures admitted | 1/33 | 33/33 |

New maximum capture gap: **1.642 s**. Median gap is 1.215 s away from policy
boundaries and 1.508 s at boundaries. Independent pair checks keep the original
identity-initialized point-to-plane ICP, fitness/RMSE gates, 5 cm translation
and 5-degree rotation bounds. Robot-only FK/proprio checks also run locally.
No detector targets or target-consistency residuals enter this sensor-only audit.

The stateful audit uses the existing `HeadDepthShadow`/`RGBDOdometry` path with
explicit `reference_mode="previous"` for adjacent accumulation, rather than
the fixed-first reference used for tiny stationary diagnostics. It keeps the
two-second wall-time guard, 5 cm/5-degree bounds and information-diagonal bound
of 10. The old trace latches lost at 384->388. The new trace admits all 33 views
without a reset or rejection. Its estimated endpoint camera displacement is
0.163 m with 47.58 degrees accumulated orientation change relative to the first
view; these are estimates, not independently measured errors or base motion.

## SAM and Capacity

| Measure | Result |
| --- | --- |
| Boundary observations processed | 25/25, zero dropped |
| Verified current-frame raw reads | 50/50 |
| Warm tracking median / p95 | 243 / 285 ms |
| Ingress-to-mask/depth-ready median / p95 | 486 / 563 ms |
| Radio-positive boundary captures | 11, actions 448-768 |
| Peak sampled total GPU memory | 23,112 MiB |

The lineage auditor checks RGB/depth hashes, output stamps, causal timestamps,
mask artifacts and valid masked-depth pixel conservation. These are not semantic
accuracy or contact-geometry scores. Boundary SAM cadence remains sparse even
inside the dense sensor window. No 300 ms end-to-end or video-rate claim follows.

## Qualification Boundary

The **bounded capture window now passes the tested timing and pose-replay gates**.
It is not yet live camera-pose integration: pose computation happened after the
native episode, and replay processing delay did not affect control. Fit confidence
is the existing heuristic, not calibrated pose accuracy. There is no independent
drift estimate, persistent map across the whole episode, qualified base pose,
low-space clearance, or contact/motion authority.

Next run the same pose updater concurrently in shadow mode on the dense window,
recording observation-to-pose-ready age, backlog, loss and reset epochs. Keep
results out of control. Only then join current masks/depth to those legal pose
estimates for metric multi-view checks. Existing clearance/stopping gates still
precede strict short-handoff comparisons. Do not return to policy/SAM model search
on the basis of this result.

## Receipts and Validation

- Private run: `sam31-dense-shadow-20260922-r1`; native receipt, video, sensor
  evidence, masks, logs and CPU audit reports retained locally.
- Source receipt SHA-256:
  `9cda435bed38eef493d2dafb09a0ef33d41fef5e767413ce726b689a4e288957`.
- SAM report SHA-256:
  `6b55329d555dea5c79c749370ebb60156b938c3da2addc47cce78c64608bf564`.
- All 318 sensor-file content hashes pass. A checksum rsync verified the backup
  after concurrent audit-file creation caused a directory-change tar warning.
- Remote optional FK audit lacked `yourdfpy`; no dependencies were installed.
  The complete FK/pair audit succeeded in the existing local environment.
- Focused launcher/dense-schedule tests: 53 passed. Focused localization,
  observer, receipt and audit tests: 42 passed. Sets overlap; do not add counts.
- Ruff passes on changed private scripts/tests. Public runtime code is unchanged.
- GPU memory returned to 0 MiB; the instance remains running as requested.
