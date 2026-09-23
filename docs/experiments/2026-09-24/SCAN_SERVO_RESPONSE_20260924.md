# Retained Scan Servo Response

## Scope

CPU-only analysis of `native-sensing-scan-20260924-r3`. No new robot actions,
paid calls, controller changes, or motion authorization. The failed action is
included, not discarded. This is preparation for phases 5/7, not completion.

Private reproduction:

```sh
.venv/bin/python scripts/analyze_scan_servo_response.py runs/native-sensing-scan-20260924-r3
```

Inputs (SHA-256):

- `receipt.json`: `db34600e74752ef02c565a417a971edb1a03750ea7619b69c2f93845611291c2`
- `joint-substeps.jsonl`: `1136064e5ae5846347424f75a3af71cc3bb807f7779f7e5a4838d6f1a0357132`

## Direct Evidence

At action 40, left joint 7's commanded interval-average rate was
-0.06478766 rad/s. Its position-derived average was -0.06465420 rad/s,
but its four substep rates were -0.15100501, -0.06562918, -0.02912342,
and -0.01285918 rad/s. The first exceeds the unchanged 0.15 rad/s monitor
limit. This is consistent with the controller tracking a stepped position
target rapidly and settling during the remaining interval.

Joint 3 also has a transient: command -0.04873866 rad/s, first-substep
rate -0.14401986 rad/s. Its peak/own-command ratio is approximately 2.95.
Ratios must be weighted by each joint's share of the path rate: joint 7
still sets the largest absolute observed speed in the last five intervals.

Audited BEHAVIOR source `b1979916ec1549b10a4e65e630bc6504a9af1b00`:

- `simulator.py`, `_on_pre_physics_step`: steps controller groups and flushes
  controls before each physics step.
- `controllers/controller_base.py`, `step`: position mode writes position
  targets and zero velocity targets.
- `controllers/joint_controller.py`, `compute_control`: optionally applies a
  configured smoothing filter; otherwise the non-impedance path passes targets
  through. This source review does not establish the live smoothing setting.

## Conditional Budget Estimate

Maximum measured substep speed / maximum commanded joint rate over the final
five intervals is 2.33076796. If that ratio persisted across the untested path,
the path-rate ceiling would be 0.06435647 rad/s before any safety margin.

For the full 1.50404024-rad path with 20 preflight and 60 reserved holds:

- Constant-rate, zero-ramp lower estimate: 782 actions.
- Trapezoid with existing 0.1 rad/s-squared acceleration: 801 actions.
- Existing cap: 600 actions.

These are extrapolations, not safety bounds. The observed path covers only a
small initial displacement; dynamics may change later. They establish why
blindly lowering the command rate is not a credible full-sweep plan under
the unchanged cap, not that an 801-action run would succeed.

## Next Decision

Do not repeat r3 or increase the speed threshold. First inspect the live
controller's smoothing configuration and callback ordering to determine whether
a classical-only interpolated setpoint path can be qualified without changing
the frozen VLA recipe. If not, explicitly revise the bounded full-sweep protocol
or search for a genuinely useful shorter sensing pose; do not truncate the goal
just to obtain a passing motion test. Native repetition remains undeclared.

Two focused diagnostic tests pass, covering known substep amplification,
budget estimation, retention of a failed interval, and missing-substep rejection.
This analysis does not qualify collision clearance, stopping, or task success.

## Controller Configuration Follow-Up

The pinned `eval/r1pro.yaml` selects absolute position control with
`use_impedances: false` and no smoothing override for both arms. The generic
arm joint-controller defaults also omit smoothing, and the constructor defaults
`smoothing_filter_size` to `None`. This supports the unsmoothed-setpoint
hypothesis, but the old receipt did not serialize live filter state.

The private read-only controller audit now records whether live response
configuration was observed, impedance mode, smoothing width, and filter presence.
Unavailable internals are explicitly unknown, never interpreted as disabled.
This changes telemetry only; it does not change gains, targets, or filters.

Do not enable upstream moving-average smoothing as a quick fix:
`MovingAverageFilter.estimate_batch` retains earlier targets in its circular
buffer. On an abort, that history can continue pulling toward the previous
target even after a fresh hold target arrives. Changing the shared controller
configuration would also risk changing frozen-policy behavior.

A prospective classical-only interpolation design must therefore demonstrate:

1. Interpolated targets installed before the simulator's order-0 pre-physics
   controller update, with observed callback order checked rather than assumed.
2. Four substep targets per 30 Hz action, ending at the original target, using
   the unchanged native position controller and monitored joint limits.
3. Immediate cancellation of pending interpolation before reserved holds, with
   holds based on fresh proprioception rather than the failed command endpoint.
4. Exclusive ownership, callback removal on every exit, and no persistent
   change to the VLA controller, codec, reset semantics, or gains.
5. Separate native qualification of actual speed, tracking and stopping before
   the full useful sensing sweep; synthetic interpolation tests are insufficient.

No interpolation callback has been installed and no native repeat has run.

## Offline Substep Preparation

Private `scripts/scan_substep_targets.py` now implements a disconnected target
sequencer. It uses four evenly spaced position targets per action, rejects
overlapping actions and duplicate/missing/mistimed callbacks, checks joint limits,
1.6-rad departure and 0.1-rad/s commanded speed, and preserves the outbound action
budget. Cancellation clears pending targets permanently. It cannot issue holds,
dispatch motion, or resume after cancellation. The native owner must independently
construct fresh measured-position holds.

Eleven focused tests pass, including cancellation at each of the five boundaries
before/within/after a four-substep interval, output aliasing, excess command speed,
and callback sequencing. Ruff passes.

A CPU-only check reconstructed the full candidate67 profile from r3's endpoint
receipt and the pinned processed URDF joint limits:

- Endpoint receipt SHA-256:
  `7b90c10b4d4b0fb2038a4eaedc5fa18fb025b0019e7feb90688019c843f54fc5`.
- 20 preflight + 482 motion actions, expanded into 2,008 substep targets.
- 60 reserved holds remain separate; total planned actions remain 562.
- Maximum interpolated command rate: 0.09983653 rad/s.
- Final target exactly equals the original useful sensing endpoint.
- No new native actions.

This verifies only target construction. Actual speed amplification, tracking,
callback ordering, cancellation latency, base behavior, collision clearance and
stopping remain unqualified. In particular, the current joint monitor compares
feedback to the control-interval endpoint; native integration must explicitly
resolve that contract when introducing intermediate targets without increasing
the geometric tracking-error allowance. This code is not connected to the runner.

## Explicit Monitor Contract

The private joint monitor now supports an opt-in `linear_substeps` mode. Each
physics sample must supply a complete named applied command, independently
checked against the exact linear fraction between the preceding and current
action endpoints. Missing commands, endpoint substitution, or held-joint changes
latch failure. Tracking error is measured against that checked substep command;
endpoint error is retained separately. The 0.003-rad tracking allowance and all
speed/departure/held-joint drift thresholds remain unchanged.

Default mode still uses interval endpoints, and the native runner still uses
that default. Retained r3 replay reproduced the exact failure at action 40,
callback 157, measured speed 0.1510050069 rad/s. Thus the old abort has not been
reclassified as a pass. The monitor/sequencer suite has 34 passing tests; Ruff
passes. This is not evidence that any native intermediate command was applied.

A read-only host check found the existing RTX4090 reachable with 0 MiB allocated.
No workload was launched, stopped, or modified. Native callback integration and
its fail-safe behavior remain the next prerequisites, particularly ensuring an
interpolation callback failure cannot expose the already queued full endpoint
to the upstream position controller for that physics step.

## Dispatch Failure Preparation

Private `scan_substep_dispatch.py` adds an injectable dispatch boundary, still
disconnected from native subscriptions. `begin` returns only the preceding
target for the ordinary evaluator action; the endpoint remains exclusively in
the substep sequencer. Each substep requires paired feedback before another
target can be written. Detected sequencing/write failures cancel pending motion
and attempt a fresh measured-position hold; hold-write failure is explicitly
fatal, not reported as a stop. The caller must retain exclusive arm ownership.

Sixteen dispatch/sequencer tests pass, including an entirely missing callback,
missing feedback, failed target writes, failed hold writes, and cancellation.
Ruff passes. These mocked-write tests do not prove PhysX callback exception
containment or actual stopping. No native callbacks have been installed.

Source review also found that `robot.apply_action` can wrap the holonomic base
joint using a direct setter. Therefore the prospective interpolation callback
must update only the active arm's existing ControllerView goal, not call the
whole-robot action wrapper at every physics substep. The ordinary evaluator path
and frozen-policy recipe are unchanged. Before native use, verify the written
goal after float32/backend conversion as well as callback order, rather than
mistaking a Python target return value for evidence of applied control.

## Native Empty-Simulator Callback Check

`native-callback-order-20260924-r1` passed on the existing RTX4090 host using
the audited BEHAVIOR source. This was a separately declared no-robot diagnostic,
not a repeat of the aborted sensing sweep. Three simulator ticks produced 12
physics steps and 36 callback records. Every step had this order and lifecycle:

1. Pre-physics order -100: `currently_stepping=false`.
2. Pre-physics order +100: `currently_stepping=true` after the upstream order-0 callback.
3. Post-physics order +100: `currently_stepping=false`.

Observed physics dt was 0.00833333376795 seconds. No scene, robot, controller
write, robot action or paid call was used. A five-minute process timeout, scan
lock, low process priority, CPU affinity 19-22 and two-thread limits bounded
the diagnostic. The process exited normally; GPU allocation returned to 0 MiB.

Receipt and full native log were copied locally. Source and receipt hashes
match on host and Mac:

- Receipt: `e3be384935f9711888f93bb5a719e343cc205d9df76dd8e8b3073b3ffeb3fb80`.
- Diagnostic source: `34ca2c9739a733e7e37a258acc199a1d6cb7df4ef1ab1d12139b20cf85c1f087`.

This verifies the candidate callback insertion order in the empty runtime only.
Robot-loaded ordering, arm-goal readback, exception containment, actual joint
response and stopping remain unqualified. No full sensing sweep was repeated.

## Native Paused Arm-Goal Check

`native-arm-goal-20260924-r1` passed after ordinary radio-instance301 reset/load
settling. It wrote the current seven-joint hold target once through the active
arm's `ControllerView.update_goal`, without a subsequent physics step or
evaluator action. It did not call the whole-robot action wrapper.

- Live arm configuration: absolute position, impedances disabled, smoothing
  width `None`, no active filter. This closes the earlier live-configuration gap.
- Seven stored target values exactly equal the float32 command.
- All other controller goals unchanged.
- Full measured joint vector unchanged.
- Simulation time unchanged at 0.3416666844859719 seconds.
- Zero robot actions and paid calls; one internal arm-goal write.
- Normal process exit and GPU allocation returned to 0 MiB.

Receipt and full log copied locally. Receipt SHA-256 agrees on host and Mac:
`44b123ef4077d9a21a64f07921008dd4de52099313ba9c249a798a5ab5f1841e`.
Diagnostic source SHA-256:
`3fe95478e9bf78d319efcabf77d0513a84394225e61ac478541f6200582a3ae0`.

The 49 focused local controller/monitor/dispatch/sequencer tests also pass.
This does not establish interpolated physical response: no non-hold target was
written, no physics tick consumed the diagnostic write, and no abort/hold
callback was exercised on the robot. Next is an integrated native callback
test with explicit failure handling, before repeating the full sensing sweep.

## Native Precision Contract

Offline integration now supports explicit float32 substep references. The monitor
requires exact agreement with the rounded prescribed target, rejecting even the
adjacent float32 value rather than adding an arbitrary numerical tolerance.
It checks both stored-target error and ideal-path error against the unchanged
0.003-rad allowance, so target rounding does not expand the geometric envelope.

Dispatch can now read back the controller goal after every write, including
fresh holds. It returns that stored target for monitoring instead of reporting
the unrounded proposal as applied. A mismatched goal cancels interpolation;
failure to write/read back the hold remains fatal. Native integration must supply
this readback callback; the no-readback mode exists only for isolated sequencing
tests and is not evidence of applied control.

Forty-three focused sequencing/dispatch/monitor tests pass, including rounding
at a 1-rad joint position and mismatch-triggered cancellation; Ruff passes.
No new native experiment was run for this change.

## Native Callback Fault Injection

`native-callback-failure-20260924-r1` completed two predeclared fault-injection
conditions in an empty simulator, without robots or controller writes:

| Condition | Outer `sim.step()` | Physics substeps after injection |
| --- | --- | --- |
| Raise `RuntimeError` inside early pre-physics callback | Returned normally | 4 |
| Set `sim.pre_step_exception` inside that callback | Raised with the injected cause | 4 |

This is direct native evidence that a callback exception alone cannot be used
as an execution stop. Explicit upstream error latching delivers the failure to
the owner, but in this rendering configuration only after the full 30 Hz interval.
The four subsequent substeps occur in both conditions; neither test proves an
immediate physical stop.

Integration requirement: cancel pending interpolation and write/read back a
fresh measured-position hold inside the detecting callback, then explicitly
latch the upstream error for the owner. Remaining callbacks in the same interval
must remain in terminal hold/error mode and cannot issue outbound targets.
Preserve the first error and retain any hold-write failure. An inability to write
a hold remains an unqualified failure, not something an exception can repair.
The existing reserved-hold sequence is still needed after control returns.

Receipt SHA-256 verified equal on host and Mac:
`41fc8a5ebc329901bb958a8050e7a1a4a7c0d3f05f87781debc1e3d814b01681`.
Diagnostic source SHA-256:
`01d306f5fdb608e4af000136eb6953b4ba1c5d26640ed412a32bb9cbbc5cb0b7`.
Full native log retained locally, normal process exit, GPU allocation returned to
0 MiB. Zero robot actions, controller writes, and paid calls. This result changes
the native adapter's required failure handling; the full sensing sweep remains
unrepeated and phases 5/7 remain incomplete.

## Declared Integrated Trial

Next attempt: `native-interpolation-abort-20260924-r1`. Fresh native radio start
and the same candidate67 geometry admission, with no relaxed collision,
tracking, speed, departure, base-feedback or freshness checks. Interpolation
updates only the active arm goal, verifies float32 readback, and explicitly
latches callback errors. The ordinary evaluator queues the preceding target,
never the full new endpoint. Frozen-policy configuration is unchanged.

Budget: 20 preflight holds, at most 20 outbound actions, then 60 reserved holds
(100 total). Deliberately cancel at action40/substep2 before writing its outbound
target. Cancellation must install a fresh measured hold inside that callback;
remaining substeps cannot resume interpolation. The separate 60-hold owner path
then uses fresh proprioception and the original departure origin. No paid calls
and no automatic retry. Unknown external clearance remains exploratory.

Diagnostic acceptance requires the exact injected failure, no preceding monitor
failure, no immediate-hold error, all 60 reserved holds with measured raw settling,
and a preserved failed-scan receipt. It does not require or claim outward scan
completion. This trial is preparation for useful coverage, not task success.

### Integrated Result

The diagnostic completed its declared injected abort and all 60 reserved holds.
100 actions were dispatched; 99 returned normally because action40 raised through
the explicit callback error latch. The scan remains `scan_completed=false` and
`execution.failed=true`. No automatic replay occurred.

Before the injected cancellation, 157 physics samples passed the monitor:
maximum measured speed 0.06331712 rad/s, maximum ideal-path tracking error
0.00041434 rad. Action40's four measured substep speeds were 0.06331712,
0.01386668, 0.00847958, and 0.00380985 rad/s. No outbound target was written after
the injected cancellation. The hold write/readback succeeded.

The outbound monitor then latched `Applied command differs from declared linear
substep`, as expected when the aborted interpolation was replaced with a measured
hold. This occurred after sample157, not before the injected fault. All remaining
raw substeps were retained. A separate original-origin hold monitor accepted
240 samples, with maximum speed 0.00112709 rad/s and maximum departure
0.02011654 rad. All 60 hold observations were raw-settled. The legal base observer
accepted 40 captures without an error; it still does not run during reserved holds.

This supports native interpolation/cancellation over the initial segment only.
Whole-sweep response, complete stopping and clearance remain unqualified.
Private suite: 1,260 passed, one existing skip before the trial.
Full archive SHA-256 on host:
`078eb0bfdefdfc8f4a3442dc52fe8fcb6811f8663d8467e8be7a37d8a42619c3`.
The full archive was copied to the Mac, matched that checksum, and extracted
locally. The native process terminated and GPU allocation returned to 0 MiB.

## Declared Full Interpolated Sweep

`native-interpolated-sweep-20260924-r1` follows the successful injected-abort
diagnostic. One fresh instance301 start, same candidate67 and fresh admission,
20 preflight holds + 482 motion actions + 60 reserved holds (562 planned, 600
absolute cap). No injected fault, no automatic retry, no paid calls. All existing
geometry, speed, tracking, departure, base and freshness limits remain unchanged.
External clearance is still unknown/exploratory. Primary endpoint is reaching
the useful sensing posture with retained RGB-D evidence; later coverage analysis
must establish usefulness independently. A completed command path alone is not
strict clearance, stopping qualification or task success.

### Full-Sweep Result

The run reached the candidate endpoint and completed all 502 outbound actions,
with 539 legal capture boundaries recorded. It was then censored by the owner
20-minute worker timeout during reserved holds: 34 of 60 holds completed. The
owner terminated the worker with SIGTERM. This is not a completed sweep and was
not retried. Future capture-heavy runs need a longer owner timeout or a cheaper
hold protocol while retaining the evidence requirements.

The fixed-stride depth report used captures 0, 25, 50, ..., 525 and 538 and 1,020
fixed low-body proxy samples in each capture's current-base frame. It is a
current-frame support diagnostic, not a world-fixed map or clearance test:

- Start: 623/1,020 samples outside all camera views; 92 with depth beyond the
  sample by the 2 cm support margin.
- Near endpoint (capture 538): 302/1,020 outside all views; 408 with beyond
  support.
- Intermediate minimum outside-view count: 219; maximum beyond-support count:
  446 at capture 425.
- Every retained in-view sample had valid 3x3 depth; this does not imply the
  unobserved region is free.

This is the first useful sensing-coverage result from the sequence: the pose
materially increases observed low-body support. It advances Phase 5 preparation,
but Phase 5 still lacks qualified clearance and stopping, and Phases 6/7 cannot
be claimed complete. The 81.6 MB local subset archive contains metadata plus
every 25th and final RGB-D capture; SHA-256:
`f6ae64ea3d3d524c09e3a5c8ac6e918aab80c944a2f65b23591217324bc4401d`.

The owner timeout was a harness defect, not a motion result. The launcher now
requires an explicit integer timeout of at least 1,200 seconds and defaults to
1,800 seconds for capture-heavy scans. It still validates the worker receipt,
terminates owned processes on failure, and never retries. Eight launcher tests
pass and Ruff is clean. The updated launcher was installed on the GPU host for
the next separately declared run.

## Completed Full Sweep r2

`native-interpolated-sweep-20260924-r2` completed with the 1,800-second owner
timeout. All 562 dispatched actions completed: 20 preflight holds, 482 motion
actions and 60 reserved holds. The receipt reports `scan_completed=true`,
`outward_complete=true`, `hold_complete=true`, and `failed=false`. All 60 reserved
hold observations were raw-settled. The outbound joint monitor retained 2,008
physics samples and the hold monitor retained 240, both without errors.
Interpolation, hold-write and base-observer error fields are null.

There are 565 capture boundaries. The fixed every-25th-plus-final depth analysis
uses 24 captures. At the final capture, low-body support is 408/1,020 compared
with 92 initially; outside-view count is 302 compared with 623 initially.
This independently confirms useful sensing gain in the completed protocol.
These are per-frame proxy samples, not accumulated world-fixed free volume.

The metadata plus fixed-stride RGB-D archive was downloaded, checksum-verified
and extracted on the Mac. Size: 85,494,262 bytes. SHA-256:
`538166aeafd69fe44b73344c00f3f018e1cd3b2878081a828e1fad62db8146b6`.
The depth report is also local. This is not a complete raw-data backup; remaining
frames stay on the host. No paid calls were made.

### Phase Decision

The exploratory sensing sweep is complete. Phases 5 and 7 remain partial:
external clearance is unknown, reserved holds do not have independent legal base
observer coverage, and no arm return was executed. The receipt explicitly keeps
`motion_qualified=false` and `stop_qualified=false`.

Do not repeat the sweep solely to accumulate passing runs. Next evaluate the
actual arm staging/return swept geometry against the retained camera evidence.
The low-body proxy result neither qualifies that arm path nor proves it blocked.
Any world-fixed fusion must bind legal estimated poses, observation times and
uncertainty; current-base-relative counts cannot be pooled as a clearance map.
Strict base transit remains unsupported by this result.

## Return-Path Evidence Decision

Read-only `native-interpolated-sweep-20260924-r2-return-support` evaluates 17
fractions from measured final left-arm posture back to measured initial arm
posture, holding other joints and the final base frame fixed. It uses final-view
RGB-D, calibrated FK, pinned robot geometry, and vertices/face centers outside
the final robot hulls. No temporal fusion or simulator truth is used.

- At fraction 0.0625, 6,033/7,106 exposed samples are outside all camera views;
  963 have depth beyond the 2 cm margin. All exposed samples on arm links 1-7
  are outside the views at this fraction.
- At fraction 0.5, 5,206/11,127 are outside views and 5,921 have depth support.
- At the return endpoint, all 11,290 exposed samples are outside all views.
- Fraction zero has no exposed samples by construction, not a clearance pass.

This rejects final-view-only evidence as a basis for qualifying this return.
It does not demonstrate collision or physical impossibility. Samples are not
surface-area percentages, and the check lacks continuous swept-volume and
uncertainty bounds. The report is retained locally; no robot actions or paid
calls occurred. The script passed Ruff after import formatting.

Next decision: assess whether existing chronological views, correctly transformed
with legal estimated base poses, observe the missing arm corridor. Do not pool
per-frame counts or assume a previously traversed path remains free. If retained
views cannot cover it, change the sensing strategy rather than repeating this
scan or claiming strict staging success. Whole-body stopping remains a separate
unresolved requirement.

## Pose-Bound Historical Coverage

`native-interpolated-sweep-20260924-r2-history-support` uses capture 500 as its
anchor because it has a recorded legal base estimate. The final reserved-hold
captures do not; they are not silently assigned the last known pose. Twenty
fixed-stride captures through that anchor have exact stamp/time/evidence joins
to base estimates. Their camera transforms are mapped into the anchor base
frame with `inverse(reference_from_anchor) @ reference_from_capture`.

The 60 camera views span 0-15.8333 seconds of simulated age. Their union is an
optimistic historical visibility diagnostic, not current free space: dynamics,
calibrated uncertainty and swept-volume bounds are not established.

- First nonzero fraction: 6,037/7,110 exposed samples remain outside all views;
  all samples on arm links 1-7 are outside views.
- Midpoint: 5,215/11,126 outside views; 5,911 depth-supported samples.
- Return endpoint: 11,005/11,289 outside views; only 229 depth-supported samples.

The anchor differs slightly from the settled final frame, so these are not
exact paired differences against the preceding final-frame test. Nor is this
an exhaustive all-frame coverage proof. Nevertheless, this sampled historical
evidence does not support qualifying the return. No motion or paid calls were
made, and the report was downloaded locally.

Decision: stop repeating this sensing sweep as a route to strict arm return.
Evaluate an observer-camera posture aimed at the proximal-arm corridor (with
its own reach/clearance requirements), or a different directly observed staging
path. Better segmentation and more model calls do not resolve out-of-view arm
geometry. Do not substitute an exploratory return for Phase 7 qualification.

## Opposite-Wrist Observer Search

The first offline attempt failed before candidate evaluation because the host
lacked the existing `survey_wrist_view_coverage.py` helper. The helper was copied
and a separately named `native-interpolated-sweep-20260924-r2-observer-survey-r2`
completed. No native simulator run or paid request was launched.

The deterministic search evaluates the measured right-arm baseline plus 128
Sobol joint-limit samples (seed 0), holding the measured final left-arm posture.
The target is every 16th exposed return-surface sample from the 17 return
fractions: 10,725 samples, not surface-area coverage. Top three camera-frustum
candidates receive authored robot-hull ray-occlusion checks.

| Candidate | In frustum | Unblocked by robot hulls |
| --- | ---: | ---: |
| 71 | 9,742 | 193 |
| 10 | 2,262 | 2,167 |
| 8 | 1,653 | 1,459 |

The baseline right wrist sees zero target samples. Candidate 10's improvement
is mainly distal: it has zero unblocked samples on arm links 1-6. None of the
three checked candidates observes samples on arm links 1-2.

This search does not establish impossibility. It is sparse, uses collision
hulls rather than optical geometry, skips camera-origin-containing hulls, holds
the left arm at the anchor for occlusion, and does not check candidate collision,
reach paths, scene occlusion or actual depth. Those limitations prevent both
motion authorization and claims that all observer postures fail.

Decision: no candidate from this bounded search merits a native observer move
yet. Strict Phase 7 remains unqualified. Do not escalate to a new motion trial
on optimistic frustum counts alone. The receipt is local. Twelve existing
frustum/occlusion/depth-binding helper tests pass with the configured script
path; an initial unconfigured local test invocation failed collection. Ruff
passes for the added observer helper and return-support script.
