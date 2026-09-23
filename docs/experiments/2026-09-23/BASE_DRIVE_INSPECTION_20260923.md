# Read-Only Base Drive Inspection

## Scope And Attempts

Following the negligible-response base pulse, inspect the pinned R1Pro drive
configuration without additional commanded actions, gain changes or model calls.
Ordinary evaluator fixture initialization/reset still advances setup physics.
These inspections do not measure drive targets or forces during a pulse.

- **r1 failed:** the diagnostic called nonexistent
  `ControllerView.get_use_impedances()`. No actions were sent. Isaac exited zero,
  but the receipt remained incomplete and the log recorded the AttributeError.
  Preserve this attempt as failed, not successful.
- **r2 completed:** use the source-verified controller `_use_impedances` field.
  Add inner exception persistence before evaluator shutdown. Tests no longer
  mock the nonexistent API. This corrective repeat was announced beforehand.
- **r3 completed:** an announced expanded read-only snapshot distinguishes raw
  PhysX limits from the public joint property's fallback values.

All attempts and logs are retained. No motion approval was reused.

## Native Findings

The active controller is `HolonomicBaseJointController`, motor type `velocity`,
with robot control enabled and `use_impedances: false`.

| Setting | Observed value |
| --- | --- |
| Configured `vel_kp` | 150 |
| Actual joint stiffness | 0 on x, y and yaw |
| Actual joint damping | 10,000,000 on x, y and yaw |
| Joint friction property | 0 on x, y and yaw |
| Input command limits | +/-1 for each axis |
| Output command limits | +/-0.75 m/s for x/y, +/-1 rad/s for yaw |

The configured `vel_kp` applies to the impedance branch, not the active direct
velocity-drive branch. Joint friction zero does not establish zero surface or
contact friction.

### Wrapper Limits Are Not Raw Limits

| Axis | Wrapper effort | Raw effort limit | Wrapper velocity | Raw velocity limit |
| --- | ---: | ---: | ---: | ---: |
| x | 100 | 3.402823e38 | 1 | 3.402823e38 |
| y | 100 | 3.402823e38 | 1 | 3.402823e38 |
| yaw | 100 | 3.402823e38 | 15 | 5.939047e36 |

Pinned `joint_prim.py` substitutes defaults when raw limits are unspecified or
above its infinity thresholds. Thus the wrapper's 100 cannot be cited as the
physical actuator effort cap, and its velocity values cannot be cited as
physically enforced safety limits. The raw numbers are effectively unbounded
at this scale. Software command limits remain a separate mechanism.

The robot initialization source contains explicit base-limit assignments, but
the post-reset native snapshot contains these sentinel-scale raw values. The
lifecycle/reset reason for that discrepancy is not yet established. Do not
silently rewrite limits or gains: that would change the frozen native recipe.

### Local Lifecycle Audit

The following source audit uses BEHAVIOR commit
`b1979916ec1549b10a4e65e630bc6504a9af1b00`. Paths below are relative to its
`OmniGibson/omnigibson` directory. This audit ran locally, with no additional
simulator launch or interference with the user's separate CPU workload.

1. `robots/robot.py:1265` assigns finite velocity and effort limits to the six
   virtual base joints during initialization, then reloads controller limits.
2. `prims/joint_prim.py:348` delegates velocity assignments to the articulation
   view. In `utils/deprecated_utils.py:278`, `set_max_velocities()` writes to the
   live PhysX view when playing; only its stopped branch authors the USD
   `MaxJointVelocity` attribute. The playing branch does not also persist USD.
3. `eval/evaluator.py:101` loads the environment and robot before applying robot
   evaluation settings. `_apply_robot_eval_settings()` at line 221 explicitly
   stops simulation, sets the standard R1/R1Pro base-footprint mass to 250 kg,
   and plays again. This is an existing evaluation recipe, not our intervention.
4. `simulator.py:1272` handles play-after-stop by refreshing handles, restoring
   controller modes, resetting the robot and keeping it still.
   `robots/robot.py:632` restores gains/control modes, not maximum velocity or
   effort. `prims/entity_prim.py:825` reinitializes articulation handles without
   rerunning the robot's initialization-time limit assignments.

**Hypothesis:** the evaluator's stop/play cycle can discard live-only base
velocity limits while restoring gains, producing the measured post-reset
combination of sentinel velocity limits and high damping. Source inspection
identifies a concrete candidate boundary, not a measured before/after change.
The inherited Isaac effort setter was not audited here; do not assume its
persistence behavior merely from the velocity setter.

This does not explain the negligible pulse by itself: removing a velocity cap
does not establish why a small velocity target failed to move the robot. The
250 kg mass is also not evidence of the cause. Neither parameter should be
changed as a speculative fix.

The next native diagnostic should combine two questions in one authorized run:

- Read raw limits and gains immediately before/after the evaluator's existing
  `_apply_robot_eval_settings()` call, then after its normal reset/load/reset
  boundaries. Observe the existing lifecycle; add no extra stop/play cycles.
- Record controller goal, computed output and PhysX target during the bounded
  command, distinguishing a dropped command from a plant-response problem.

If limits are already sentinel before evaluation settings, reject that boundary
as their origin. If they change across it, report the transition without yet
claiming it caused the motion failure. If PhysX receives the intended target
but the base stays still, investigate the native physical response rather than
altering semantic prompts. Any commanded diagnostic needs a new scoped
approval; earlier single-run approvals are consumed. Strict gates stay intact.

### Follow-Up Preparation

The private pulse diagnostic now wraps the existing evaluator settings,
reset and task-load calls with read-only snapshots and records the prepared
drive telemetry at substeps. It preserves the original 30-action schedule,
0.005 m/s maximum requested forward speed, preflight, abort and braking checks.
Exceptions are persisted inside the evaluator context before shutdown can
obscure them. No native repeat has been launched by this preparation.

Local verification: **1031 passed, one existing skip**, plus focused Ruff checks.
Four new lifecycle tests check order/arguments/return values, exactly one call
per operation, and persistence without retry for failures before, during or after
an operation. These unit tests do not prove native telemetry correctness.
The protocol explicitly requires preserving the user's unrelated CPU workload
on the shared GPU host and a fresh single-attempt motion approval.

## Interpretation And Next Step

This eliminates an unsupported explanation based on a 100-unit effort cap. It
does **not** establish friction, collision, saturation or a dropped command as the
cause of negligible motion. The earlier pulse did not log applied drive targets.

Prepared, unit-tested private telemetry can now separately record:

- controller goal;
- computed controller output;
- PhysX velocity target;
- raw measured joint velocity;
- projected joint forces, explicitly not asserted to be drive force alone.

This telemetry has not yet run in a native pulse and confers no qualification.
Before escalating speed, audit the native reset/limit lifecycle and instrument
the command-to-actuator path under a separately approved bounded protocol.
Strict stopping and clearance remain unresolved; no extra pulse was issued.

## Verification And Evidence

Private runs: `runs/native-base-drive-inspection-20260923-r1`, `-r2`, `-r3`.
Receipt SHA-256 values:

- r1: `a13e4edc6b5e9a9da2e6cf4ef95f4e890385477539ca0f20c1195a5d06bc979d`.
- r2: `e232e6cfd15ee0c12ed63b18de2c5c54272c64ce633477b3540fa2521b086a73`.
- r3: `0b707be830f54f56c5a92ce8652fa28f7403238e3ae531ac8dc0b7627019db7b`.

Source snapshots match recorded hashes; environment snapshots match before/after
for all three attempts. All report zero commanded actions. Raw runs and logs
were copied locally; directory checksum comparisons reported no differences.
Private suite: **1027 passed, one existing skip**. Focused scripts pass Ruff.
