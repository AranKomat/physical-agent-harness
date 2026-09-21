# Empty-Scene Base Response Diagnostic

## Result

The separate, explicitly authorized empty-scene test did **not qualify base
response or stopping**. Do not proceed to a classical-to-policy handoff on the
strength of this result. This is not a learned-policy trial, not an ordinary
radio start, and not evidence that a particular checkpoint failed.

The calibration fixture uses the pinned R1Pro controller configuration in an
otherwise empty floor-plane `Scene`, a `DummyTask`, and only legal proprioception
as controller input. No model service or global-pose feedback is used. Whole
native 23D commands preserve fixed initial arm/torso/gripper targets. The benchmark
clearance gate is unchanged. All failed attempts remain available privately.

## Fixture Checks

| Run | Difference from previous setup | Counted controller ticks | Nonzero base-command ticks | Result |
| --- | --- | ---: | ---: | --- |
| r1 | Initial standalone fixture, spawn z=0.01 m | 120 | 0 | Initial stop failed, bounded recovery also failed |
| r2 | Apply evaluator's base-footprint mass adjustment | 120 | 0 | Same stop failure |
| r3 | Also match pre-trial physics settling/snapshot initialization | 120 | 0 | Same stop failure |
| r4 | Same as r3, spawn z=0 m | 120 | 0 | Same stop failure |
| r5 | Same as r3, spawn z=0.05 m | 120 | 0 | Same stop failure |
| r6 | Same as r3, explicit non-admitting response characterization | 510 | 90 | Six responses recorded; none passed, no stop acknowledged |
| r7 | Same as r3, but initialize only joint positions from the settled radio hold | 120 | 0 | Same stop failure |

The mass adjustment is part of the pinned evaluator, not a tuned improvement:
the reported footprint mass changes from approximately 47.63 kg to 250 kg.
The later setup reproduces the evaluator's 25 physics-only ticks with robot
`keep_still`, snapshot/reset, followed by environment reset. Those operations
occur **only during disclosed fixture initialization**, never during a pulse or
braking measurement. Setup physics is separate from the controller counts above.

Changing mass, initialization, and spawn height did not resolve the stop failure.
These tests do not establish the root cause. In particular, the floor-contact
hypothesis is not confirmed by the height comparison. Do not tune acceptance
thresholds until the discrepancy with the stationary radio hold is understood.
Copying the measured joint posture also failed to resolve the discrepancy. No
base/world pose or scene state was copied, and this was never a benchmark start.

## Characterization Protocol

Strict qualification stops after failed settling. The subsequent characterization
was deliberately different: its purpose was to measure command response despite
the known failed baseline, not turn that failure into a pass. The driver always
sets `passed=false` in this mode, and never grants motion or benchmark authority.

After 60 initial hold ticks it applied six fixed 15-tick (0.5 s) pulses, each
followed by 60 hold ticks. Translation commands were +/-0.03 m/s; yaw commands
were +/-0.05 rad/s. The 510 ticks total 17 simulated seconds. Abort limits remained
0.08 m/s translation norm, 0.15 rad/s yaw, 0.03 arm/torso target drift in native
units and 0.006 m gripper drift. No abort bound was exceeded.

Response checks use the last five pulse observations, comparing the commanded
axis against a declared tolerance (20% plus 0.003 m/s or 0.005 rad/s) and checking
uncommanded-axis leakage (0.005 m/s translation, 0.01 rad/s yaw).

| Pulse | Commanded x, y, yaw | Mean measured x, y, yaw | Response result |
| --- | --- | --- | --- |
| Forward | 0.030, 0, 0 | 0.0200, 0.0056, 0.0306 | Failed |
| Backward | -0.030, 0, 0 | -0.0612, 0.0164, -0.0983 | Failed |
| Left | 0, 0.030, 0 | -0.0124, 0.0414, 0.0451 | Failed |
| Right | 0, -0.030, 0 | -0.0038, -0.0161, -0.0145 | Failed |
| Positive yaw | 0, 0, 0.050 | -0.0087, 0.0089, 0.0790 | Failed |
| Negative yaw | 0, 0, -0.050 | -0.0146, 0.0016, -0.0566 | Failed |

Translation units are m/s; yaw units are rad/s. Commands affected the intended
axes, but unwanted motion and biased responses were substantial at these low
speeds. Maximum measured translation norm was 0.06345 m/s; maximum absolute yaw
was 0.09866 rad/s. Maximum arm/torso target drift was only `6.048e-5`, and maximum
gripper drift was `5.514e-7 m`, despite reported joint velocities exceeding the
settling criterion. That contrast merits investigation; it does not justify
discarding the velocity signal or silently declaring the robot stopped.

Stopping required five consecutive observations below 0.002 m/s translation and
0.005 rad/s yaw, plus the existing arm/torso/gripper speed checks. All seven stop
windows (initial plus six braking windows) failed. Acknowledgement times are
therefore **null**, not 2 seconds. The saved velocity-integral quantities describe
travel proxies during the capped windows, not qualified braking distances.

## Interpretation And Next Check

There are two distinct unresolved prerequisites:

1. Sensor coverage/robot bounds do not establish a benchmark staging corridor.
2. The standalone native response fixture does not yet establish a reliable
   stop or low-speed tracking baseline.

Neither is a GPT prompt problem. Do not launch a long supervised rollout to
diagnose them. The subsequent sustained radio comparison **passed 60 zero-base
hold ticks (2 simulated seconds)**. All 60 samples met the existing radio hold
criteria, with maximum joint-target drift `9.059906e-6`. This is stronger than
the earlier five-tick check, but it still does not measure moving-base braking.
The radio hold uses translation/yaw limits of 0.01 m/s and 0.02 rad/s, while the
empty-scene stop test additionally requires 0.002 m/s and 0.005 rad/s. Therefore
the two pass/fail labels alone are not an identical-threshold A/B comparison.
The retained raw measurements allow direct comparison; they must not be replaced
by a claim that the policy or simulator is defective.

The fixture discrepancy remains unresolved after the bounded checks above.
Further empty-fixture variants are deferred rather than changing thresholds to
manufacture a pass. An explicitly labeled simulator-only exploratory protocol
was approved by the user. It records unknown clearance explicitly and does not
override strict benchmark gates or certify collision freedom. The first native
radio test is a single bounded forward pulse, without GPT or policy inference.

Public implementations: `base_pulse.py` and `empty_base_audit.py` under
`experiments/behavior/`. Private run directories are
`hybrid-empty-base-20260921-r1` through `-r7`. The r6 response plot is retained
privately as `response.png`; no licensed sensor imagery or robot asset is copied
to the public repository.

## Verified Receipt Hashes

- r1: `3326f163a99bfbfdb57b51daa30172fd62aae813814a3ee9ec43c9d5a0a7b019`
- r2: `008aff2f521121875104d55f7dc2b82ab0914f922366efc5cd0fae466dfefd35`
- r3: `0bd6f0748b0ff4be291d868844ee8bd7edef7c1b27c1fca533cb41d817ba16a9`
- r4: `a203cf246f18f227c6e71eba63be4e321b534ed3ce8310145a072e8233fb2ef8`
- r5: `7dbe06f750c5755872b6deaea5d0320d3ed844946bdb35c9031cd69b802ad73b`
- r6: `d26759b801810e0461c86002a45e7d1c36c64bcfa8e59da4bb5cdcec3a54d120`
- r7: `68fd094163f21eddad1259eef29bf1cc1e8e99af51eae4e4b822810fde91abb2`

The sustained-radio receipt is
`83915db7925ec16be9bebc387203303955de161ac78d9138966db82bb2c7fdbd`;
364 associated receipt/evidence files were SHA-256 checked after transfer.
