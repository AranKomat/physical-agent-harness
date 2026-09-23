# Approved Exploratory Wrist Probe

## Authorization And Protocol

The user explicitly approved one simulator-only wrist probe of at most 0.01 rad
out/back and 60 total control actions, contingent on actuator/stop preflight.
Unknown external clearance is logged, not treated as certified free. Strict
benchmark gates are unchanged; no task success or no-contact claim is made.

One attempt used the standard radio development instance 301 and native actuator
commands, not direct simulator position/state mutation. No paid model was called.
The existing codec audit verifies absolute joint commands, controller classes,
channel layout, normalization and gripper conversion. An additional live joint
name check binds channel 13 to `left_arm_joint7`; native joint limits are checked.

Predeclared protocol:

- Target +0.008 rad, leaving headroom below the approved 0.01 rad cap.
- At most ten hold actions to obtain five consecutive stopped initial samples.
- Ten ramp actions, then at most ten outbound-hold actions requiring five
  consecutive stopped/reached samples.
- Only after that gate, ten return-ramp actions and at most ten return-hold actions.
- At most ten emergency feedback-hold actions; both driver and native wrapper
  enforce the overall 60-action cap. No automatic retry.
- Stop checks include the existing settled predicate, base linear speed <=0.002
  m/s, yaw speed <=0.005 rad/s, wrist speed <=0.006 rad/s, and endpoint error
  <=0.001 rad. Feedback aborts monitor wrist excursion, held-joint/gripper drift
  and base/wrist speed. Limits were not changed after seeing the result.

Initialization/reset settling precedes counted actions. This is not a claim
that loading/resetting the simulator involves no physics.

## Result: Outbound Tracking, Failed Stop Verification

- Native actuator/codec preflight passed. Five initial stopped samples passed.
- Ten outbound actions closely tracked the ramp. Maximum wrist displacement was
  **0.007999839 rad**, within the approved bound.
- During outbound hold, position error stayed within approximately **1.63
  microradians** of the target.
- Maximum held arm/torso drift across the attempt was **9.525 microradians**.
- The outbound stop gate did not obtain five consecutive qualifying samples
  within ten actions. The return leg was therefore **not attempted**.
- Ten emergency feedback-hold actions also failed the five-consecutive-sample
  stop test. Stop acknowledgement remains false; simulator execution then ended.
- **35 attempted and completed actions**, 36 observation captures, approximately
  **1.166667 seconds of controlled simulation time**. No extra actions or retry.

Intermittent wrist-speed readings explain most failed stop samples. During the
outbound hold they include roughly -0.01036, -0.00946 and -0.01077 rad/s despite
nearly unchanged sampled positions. Two samples also exceeded the 0.002 m/s base
linear-speed threshold. The maximum wrist speed over the complete attempt was
0.01551 rad/s. These are below the emergency motion abort caps, but above the
stricter stopped-state threshold.

The pinned source obtains arm velocity channels directly from joint velocities;
there is no discovered text/model issue or evidence here that the wrist ignored
the command. Substep dynamics, velocity readback semantics and controller behavior
remain possible explanations. **Do not relabel these readings as harmless noise
or loosen the stop threshold without a separate qualification.**

## Evidence And Verification

Private run: `runs/wrist-joint-probe-20260923-r1`.
Receipt SHA-256:
`5595635524d5bd18f8f388f80cddefbcfb4fa2fc78cb6f06489d7fb471e20688`.

Native source check passed before/after; GPU environment unchanged; executed
script hash unchanged. Simulator exited with no remaining GPU compute process.
The roughly 166 MB run and log were copied locally and checksum-verified.
The completed receipt deliberately reports `passed=false` and
`stop_acknowledged=false`; process exit code alone is not a pass criterion.

Six driver tests cover bounded success, failed preflight, unresponsive motion,
overshoot and invalid initial state. Full private suite after coverage/probe work:
**931 passed, one existing skip**; Ruff clean. Public production code unchanged.

## Decision

This is useful evidence of a working small joint-position command path, not a
completed free-space staging/return qualification. Do not extend the action budget
or repeat the excursion automatically. The unused numerical allowance does not
turn this one-attempt approval into permission for a fresh trial after reset.

Next inspect the saved position/velocity/timebase data and pinned controller
readback implementation. A future bounded hold/substep diagnostic should separate
true oscillation from sampling/readback behavior before another out-and-back
attempt. External clearance is independently unresolved as shown by the retained
depth-support audit. Phase 7 and the matched task experiments remain incomplete.
