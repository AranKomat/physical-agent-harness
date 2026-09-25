# Phase 13 SAM Reset Lift And Phase 14 Learned-Perception Power

## Result

One preregistered exploratory strawberry lift passed after a live SAM 3.1 tracker
reset and current-image reacquisition. The same run retained time-aligned RTX 4090
power telemetry and exact descriptor-cache accounting.

The worker first acquired a source-bound candidate from the legal pre-close
left-wrist RGB-D capture. It then discarded that tracker, created a new session,
and reacquired from the current post-close RGB-D. The SAM worker had no motion
authority. The simulator executor admitted the existing bounded lift only after
validating the new session, source hashes, mask area, and measured depth support.

| Measurement | Result |
| --- | ---: |
| Pre-reset SAM candidates | 1 |
| Post-reset SAM candidates | 1 |
| Pre-reset mask pixels / valid-depth pixels | 42,679 / 42,679 |
| Post-reset mask pixels / valid-depth pixels | 27,725 / 27,725 |
| Pre-reset inference | 526 ms |
| Post-reset inference | 168 ms |
| R1Pro actions | 30/30 |
| Evaluator lift | 50.0069 mm |
| Legal RGB-D/FK lift | 50.0076 mm |
| Legal retained-surface IoU | 0.9847 |
| Legal median depth change | 0.0091 mm |

The evaluator and independent legal RGB-D/proprio verifier both passed. External
clearance remained unknown and `motion_qualified=false`; this is not BEHAVIOR
benchmark success.

## Robustness Interpretation

This closes one declared Phase 13 axis for the controlled fixture:
`discovery/tracker reset`. The action used a current post-reset mask rather than a
reused tracker-local ID. Tracker-local IDs still have no persistent physical
identity authority, and the prompt `a red object` supplied only a region proposal.

This does not establish robustness to room/layout variation, natural occlusion,
object placement, or held-out tasks. Initialization and the grasp/lift trajectory
were scripted, and the run changed no strict-clearance conclusion from Phases 5-7.

## Power And Cache

The device-power monitor sampled GPU 0 every 250 ms. No compute process existed
before or after the cohort. Periodic snapshots contained only the declared SAM
and simulator descendants.

| Interval | Duration | Gross device energy | Mean power |
| --- | ---: | ---: | ---: |
| Full coordinator span | 331.779 s | 3.5635 Wh | 38.67 W |
| SAM load + simulator startup to pre-close | 318.088 s | 3.2405 Wh | 36.67 W |
| Close + closed hold | 2.873 s | 0.0720 Wh | 90.22 W |
| SAM reset/reacquisition + lift + lifted hold | 4.015 s | 0.1150 Wh | 103.14 W |
| Post-lift shutdown | 6.803 s | 0.1359 Wh | 71.94 W |

Cold startup again dominated: 95.9% of sampled time and 90.9% of gross energy.
The result strengthens the case for a resident simulator and resident learned
perception service during comparisons.

The public exact-dependency representation cache recorded two fresh misses and
two subsequent exact hits with zero evictions. These hits reused derived mask
descriptors for the gate consumer. They did **not** reuse SAM neural embeddings
and therefore do not demonstrate neural feature-cache savings.

The pre/post idle estimate exceeded some low-power active samples, so
baseline-subtracted energy is not reported as a result. The defensible values are
the gross sampled intervals above. The SAM-reset interval also contains physical
lift actions and cannot isolate model-only energy.

## Preflight And Fixes

The new GPU host initially lacked the approved SAM runtime. The official Meta
checkpoint was restored with published SHA-256
`0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`
and source revision `2345a4ad109ac29c569da749c91d84f10dc08c40`.

The first isolated venv used Python 3.10 with Python 3.11 PyTorch binaries and was
rejected before inference. It was rebuilt on the simulator's Python 3.11 runtime.
A retained no-motion preflight then passed the exact 480x480 wrist-frame path.
One disposable preflight packet had a literal escaped newline and stopped after
model load but before inference; the corrected fresh preflight is retained as
the compatibility evidence, not as a Phase 13 outcome.

The streaming adapter now accepts an explicit native size of 480 or 720 pixels,
with 720 remaining the default. The lift runner gained a source-bound external
SAM gate; invalid, stale, depth-unsupported, or failed-reset evidence resolves to
hold or abort rather than motion.

## Evidence

```text
preregistration
2f71c9fd1bcedd05e5a833fef029538d2d1339ddc1537690cfc39f0311aafdbe

coordinator
3a5f0bf160260cb63b2d93cb41715f3da93f2d2097447ab5f517210ef337c671

workload receipt
021e8797606323eb2076c06c9b91209dbc8af44f24f3155a971e84555a76e665

evaluator sidecar
59fc246fb198a6550e875f751fc2981c711c794131bc95709217613188edc13c

SAM gate / diagnostics
983f0bbbef698c7a40856097857d4561e1a73279529ca72d9432ca85ede186e4
ed0a108f028e94a86fe5d9db71ed2c5aa5e13ce942a45f7fe155558df4b16251

legal RGB-D/FK verification
9e7707af8ac4826023bdebca639d0574ed309be6fefde458806e30fdbafa462d

power telemetry
f9cf00b69f27636f01cdd840e5ee6896403031d78feb262b00098d8429ef0e98

final analysis
f010a1e993aa936c253a5829fd6b6bb1d14b7d7f98ddbf170852fb328487ae4c
```

## Next Gate

Phase 13 still needs a broader natural axis such as room/layout variation or
natural partial occlusion; more nearby scripted object/category variants are low
value. Phase 14 now has successful classical and learned-perception power
baselines. Learned-policy/GPT energy and actual SAM neural-representation reuse
remain open, but should be measured only on another successful workload rather
than by replaying this fixture.
