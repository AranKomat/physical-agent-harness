# Approved Stationary Hold Substep Diagnostic

## Protocol

User explicitly approved the separate simulator-only stationary hold diagnostic.
One attempt, at most 30 actions, no wrist excursion or contact intended, no paid
calls, unknown clearance retained. Existing stop/abort thresholds unchanged.
Native development radio instance 301, seed 0, pinned BEHAVIOR
`b1979916ec1549b10a4e65e630bc6504a9af1b00`. Ordinary setup/reset settling precedes
counted commands. All 30 commands are identical initial-position holds with
zero base twist, using the audited absolute-position codec and live joint mapping.
No direct simulator-state mutation is used for control.

The read-only post-physics callback runs at order 100, after upstream order 0;
installed PhysX docs confirm ascending order. Only this robot's wrist telemetry
is read. Callback errors are latched and checked before another action; the
subscription is removed before simulator teardown. There is no automatic retry.

## Results

**Diagnostic complete; sustained final stop not acknowledged.**

- 30 attempted/completed actions, 31 RGB-D/proprio captures, 120 physics callbacks.
- Exactly four callbacks per action; dt 0.008333333767950535 seconds, about 120 Hz.
- Controlled simulation duration 1.0000000521540642 seconds.
- Estimator history available in all 120 samples; no raw fallback.
- No callback errors, feedback aborts or script/source/environment changes.
- 23/30 post-action samples satisfy the unchanged stop predicate, including early
  consecutive runs. The final sample fails, so final acknowledgement is false.

| Measurement | Maximum absolute value |
| --- | ---: |
| Raw wrist velocity | 0.014425682 rad/s |
| Upstream position-derived velocity | 0.000100438 rad/s |
| Independent consecutive-substep velocity | 0.000066982 rad/s |
| Upstream versus independent difference, excluding first sample | 1.97e-12 rad/s |
| Upstream estimate versus its position-difference formula | 1.97e-12 rad/s |
| Cached versus directly sampled wrist position | 0 rad |
| Held arm/torso drift | 9.060e-6 rad |
| Gripper drift | 3.726e-7 m |

The first upstream estimate uses history before the first recorded callback;
there is no independent counterpart for it. Across all 120 samples, wrist position
spans 7.3873e-7 rad. Maximum wrist drift from initial capture is 6.95295e-7 rad.
Each final action callback position exactly matches its post-action capture.

Raw wrist velocity exceeds 0.006 rad/s at actions 6, 9, 13, 16, 25, 27 and 30.
Base linear speed also exceeds 0.002 m/s at actions 9 and 13, peaking at
0.00243869 m/s. Wrist telemetry alone cannot resolve every stop failure.

## Interpretation

Every exposed physics step was sampled, unlike the earlier 30 Hz trace. This
supports a substantial discrepancy between raw reported wrist velocity and
position-derived motion at 120 Hz; stale cached position does not explain it.
It does not identify the underlying solver/readback cause, exclude within-step
dynamics, qualify base stopping, or validate an estimator during motion/braking.

Do not change the stop predicate based on this stationary run. Next qualify a
proposed estimator during known moving/stopping behavior, retain raw channels,
and separately address base speed. Further exploratory motion requires its own
scope; this approval is consumed. External clearance and out/back remain open.

## Offline Base-Speed Follow-Up

The pinned `robots/robot.py::_get_base_qvel_for_proprioception` reads raw
articulation velocities for the three virtual-base control joints, then rotates
the planar components by base yaw. The audited live mapping is joint indices
0, 1, 5: base_footprint_x_joint, base_footprint_y_joint and
base_footprint_rz_joint. The eval config places this three-value vector first
in proprioception; the harness copies it without rescaling.

The planar rotation is orthonormal and preserves speed magnitude. Therefore
even an incorrect yaw value alone cannot explain these norm threshold crossings.
This is not evidence of a discovered coordinate-conversion or unit bug.

The offline audit validates 30 zero-base commands, 31 consecutive same-session
captures and 30 Hz control intervals. Action 9 has 0.002031619 m/s planar speed;
action 13 has 0.002438690 m/s. Maximum absolute yaw rate is 0.003149396 rad/s,
below the unchanged 0.005 rad/s limit. Both planar failures coincide with wrist
failures, but that correlation does not prove a common cause.

The recorded 61-value proprioception does not contain base position. The wrist
substep callback did not collect independent base motion, either. Do not infer
stationarity from zero commands, integrate the same raw velocity and call that
independent evidence, or silently use simulator global/base virtual positions
as qualified localization. Base validation requires the legal estimated-motion
path; oracle diagnostics, if ever collected, must stay outside control.

Private analysis: `runs/hold-base-speed-audit-20260923-r2/receipt.json`.
R1 failed JSON serialization on a NumPy integer before writing its result;
the explicit scalar conversion was fixed and serialization is now regression
tested. R1's directory remains; no native run was repeated. Five focused tests
and Ruff pass. This follow-up adds no actions, paid calls or threshold changes.

## Evidence And Cleanup

Private run: `runs/wrist-hold-substep-20260923-r1`.
Receipt SHA-256:
`d60f1c4a164941db1d42b1c4770d749dd822176f46a5343987587d01f5e85935`.
Runner SHA-256:
`31a0e63b461a52496a778581e6f76eec578b3ee62920970450c3ddad8ce88661`.
Recorder SHA-256:
`c79abf146f73870bcb4166100fd2de14da46a03d95158414dcb900cbe1625c2b`.

The approximately 148 MB run and log were copied locally; checksum-rsync comparison
is empty. Simulator exited and no GPU compute process remained. Process exit zero
is not treated as stop success. False final acknowledgement and motion qualification
remain in the raw receipt. No paid calls, repeated attempt or threshold changes.
