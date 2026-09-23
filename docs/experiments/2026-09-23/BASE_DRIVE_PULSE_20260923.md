# Instrumented Base Drive Pulse

## Scope

Run `base-drive-pulse-20260923-r1` followed the user's authorization to proceed
with bounded simulator diagnostics without repeated approval requests. It kept
the preceding schedule: five holds, ten forward commands at 0.005 m/s, fifteen
braking holds. Unknown clearance remained explicitly exploratory. No paid calls,
automatic retry, policy inference, mass/gain/limit changes or instance lifecycle
operations. The process used nice priority 15 and four CPU cores on the shared
host; its process exited and GPU compute allocation cleared afterward.

## Results

All 30 actions completed, with 120 physics samples plus an initial drive
snapshot, eight lifecycle snapshots, no callback errors and unchanged recorded
environment/source hashes. Final raw stop acknowledgement remained false.

| Measurement | Result |
| --- | --- |
| x/y raw velocity limit before evaluator settings | 1.5 m/s |
| x raw effort limit before evaluator settings | 1000 |
| x raw velocity and effort limits after evaluator settings | 3.4028234663852886e38 |
| x damping before and after | 1e7 |
| Maximum controller-output / PhysX-target absolute difference | 0 across all 121 snapshots |
| Forward displacement during pulse, evaluator-only | 2.0671843 micrometres |
| Nominal forward command integral | 1.6667 mm |
| Maximum sampled planar excursion during pulse | 3.6315986 micrometres |

The previous pulse's legal-joint and evaluator-pose files have identical hashes
to this run. This is same-start deterministic diagnostic replication, not an
independent seed, broader robustness evidence or new moving-localization cohort.

The lifecycle hypothesis is now measured: finite limits were present before
the evaluator's existing settings call and sentinel limits afterward. That call
contains the standard stop / base-mass assignment / play sequence. Later
reset/load/reset snapshots retain sentinel limits. This localizes the change to
that composite operation; it does not isolate which internal operation causes it.

The controller rotates body-frame forward commands into canonical virtual-joint
coordinates. Pulse goals, computed outputs and PhysX targets agree in those
coordinates (approximately -0.0049701, -0.00054593, 0). A negative canonical x
target here is not a backward body-frame command. No dropped target was observed.

## Interpretation

The unresolved issue is downstream physical response, not evidence that GPT
chose a bad instruction or that the wrapper failed to deliver this target.
Limit loss and weak movement coexist, but this does not establish causation.
Do not restore limits, alter mass/gains, or escalate speed as an unlabelled fix.
Next inspect native base joint/body mapping and solver response before deciding
whether a separately declared experimental physics correction is justified.

Projected joint forces were recorded but are not isolated actuator force.
Evaluator poses remain in a separate retrospective-only stream and never affect
commands or stop checks. No moving/braking accuracy, strict clearance, base
transit or whole-robot stop qualification follows from this near-stationary run.

## Evidence

Private analysis: `runs/base-drive-pulse-analysis-20260923-r1/receipt.json`.
Receipt SHA-256:
`23f852f00b77fc4be11abd2e615bdb6a19b78dc604d1403ed4cbfbad21c03c7c`.
Legal joint SHA-256:
`6bb09938058f5b45bd80ecd8c8dc0eab48424317df39c4e644b9d08a8d11818f`.
Evaluator pose SHA-256:
`73ea7485b92a99a5860fc0607fb143f3800ed291257d0592e9c30ba6567f543f`.
All snapshotted script hashes were checked by the local analysis. Full private
suite before analysis: **1032 passed, one existing skip**. Unit tests alone do
not qualify physical stopping or measurement accuracy.
The raw run and log are backed up locally; a checksum-based directory comparison
against the remote run reported no differences.

## Saved-Trace And Source Follow-Up

Projected x-joint force ranges are -42.58 to 18.92 during initial holds,
-905.14 to -792.85 during the pulse, and -46.63 to 24.90 during braking.
The command therefore coincides with a substantial change in measured joint
loading. These are projected joint forces, not isolated drive effort or a
contact/friction diagnosis. Maximum planar PhysX target magnitude during the
pulse is 0.0050000003 m/s; holds and braking target zero.

Pinned `robots/robot.py:251` emits a floating-base warning but then forces
`fixed_base` for holonomic robots. `objects/usd_object.py:303` creates the world
root joint, and `robots/robot.py:516` sets its anchor. The authored asset has
driven virtual x/y/yaw joints leading to `base_link`; a fixed virtual root is
part of this locomotion scheme, not proof that the physical base is locked.
Do not change fixed-base configuration merely to suppress that warning.

The source default sleep threshold is 0.00005; this is not a directly comparable
velocity cutoff. Neither its effective post-reset value nor sleeping status was
measured in this trace. Sleeping, stabilization and contact resistance remain
hypotheses, not established causes.

The next diagnostic telemetry adds measured virtual x/y/yaw joint positions,
without changing control. Compare their interval displacement against the
separate evaluator body-pose stream to distinguish joint motion from body
motion/readback discrepancy. Existing r1 files are immutable and do not contain
this additional field. No further native run was issued for this source audit.
