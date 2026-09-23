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
