# Scan Physics Callback Integration

The private `scripts/native_scan_joint_subscription.py` connects the 22-joint
scan monitor to the existing native PhysX post-step subscription API. It uses
the audited controller joint-name/index mapping, no global poses or scene
state. It has no actuator-dispatch methods.

Before subscription, measured joints must match the monitor's initial state.
Subscription uses the established `pre_step=False, order=100` pattern. Each
callback records named positions, raw velocities, engine time, timestep,
callback count and action number to a flushed JSONL stream. The monitor
separately checks interval completeness and the tightened tracking limits.

Failures latch and are raised through `check`, `begin` and `finish`. Remaining
callbacks preserve finite telemetry after a threshold failure, but cannot clear
the failure or certify the action. Closure is idempotent and blocks further use.

Seven adapter tests cover subscription/cleanup, threshold failure with continued
evidence, upstream errors, nonfinite joints, missing callbacks, samples outside
an action, and detached initial state. Combined adapter/joint-monitor tests:
18 passed. Full private suite: 1,192 passed, one existing skip. Ruff passes.

These are API-contract tests with injected robot/PhysX objects, **not native
simulation execution**. They do not establish live callback timing, tracking or
braking. A substep failure does not interrupt an already issued control interval;
the actuator wrapper must check the latch before another action. Reserved
emergency holds need a separate bounded path, not a cleared failure latch.

Next: integrate the callback and legal base observer into the single-owner
native runner, preserving fresh-episode geometry and the approved action/hold
budget. No GPU work, model calls or robot actions occurred in this follow-up.
