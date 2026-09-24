# Coupled Execution Preparation

Latest update: native wiring was completed and one exploratory attempt ran.
It aborted at the base-rate monitor, completed all reserved holds and did not
return. See `NATIVE_COUPLED_ROUNDTRIP.md`. Earlier sections below retain the
preparation history; Phase 7 is still incomplete.

Phase 7 remains incomplete. No new simulator run has occurred.

Inspection of the existing private native scan runner found that the telemetry
monitor and interpolation adapter were hard-coded to seven left-arm joints.
The staged right-arm-plus-torso candidate cannot be sent through that runner
unchanged: torso commands would violate its held-joint contract and its
substep writes target only the left-arm controller.

## Local Changes

`scripts/sensing_scan_monitor.py` now accepts an explicit unique active-joint
tuple and a departure bound no larger than the existing 1.6 rad limit. Defaults
remain the original left-arm scan. The coupled candidate uses torso4 + right7
and a 0.25 rad bound; fingers cannot be declared active. Held-joint checks,
sample ordering, speed/tracking thresholds and latched errors remain intact.

`scripts/native_scan_interpolation.py` explicitly rejects a non-left-arm
monitor before opening its log or preparing controller writes. It does not
implement coupled dispatch or silently reuse the wrong controller.

Focused private tests: **59 passed**, covering the monitor, native interpolation
fixture, substep dispatch and substep targets. These tests do not qualify any
native capability. Changes are local and have not been deployed to the host.

## Next Execution Work

Implement and verify coordinated torso/right-arm substep dispatch with the
exact native controller layouts, float32 goal readback, shared failure latch,
and fresh measured holds for both groups. Reuse the existing single-owner
subscription/abort scheme, not two independently progressing controllers.

Before an actual out-and-return trial, recapture and bind the current pose,
recompute the candidate and geometry checks, declare endpoint/stop tolerances,
and resolve strict scene admission or label a permitted exploratory protocol
explicitly. Retained candidate joints must not be replayed as a live command.
The external coverage and full-geometry limitations remain as documented in
`STAGED_SCENE_SCREEN.md` and `STAGED_SWEEP_SCREEN.md`.

## Coordinated Dispatch Boundary

Local preparation now includes `scripts/coupled_controller_goals.py` and an
explicit 11-joint mode in the existing substep sequencer/dispatch. The original
seven-joint mode remains the default. The coupled mode uses torso4 followed by
right-arm7, one substep sequence, a 0.25 rad departure bound and float32 goal
readback checks. It does not install native callbacks or grant motion authority.

Controller writes are ordered within one call, not claimed to be atomic. Any
partial-write failure reaches the shared terminal latch; its hold path reads
one fresh complete position vector and attempts both group holds even if one
group write fails. A failed hold is reported, never treated as successful stop.

**65 focused tests passed**, including first/second controller failures,
permanently unavailable controller during hold, readback, interpolation and
the smaller departure bound. The next missing integration remains the native
two-controller adapter and fresh-state out/return owner. These fixture results
do not complete a phase or permit replaying retained joint targets.

## Native Callback Adapter Implemented Locally

`NativeScanInterpolation` now has an explicit `coupled=True` mode. It binds the
`trunk` and `arm_right` controller goals to the shared dispatcher, checks the
exact torso4/right7 joint order and action channels, rejects overlapping joint
indices, and requires unsmoothed non-impedance absolute position controllers.
The default remains left-arm-only and still rejects a coupled monitor.

Both group writes occur before a physics step; they are not claimed atomic.
Partial failures enter the shared abort/hold path and set the simulator
pre-step exception. Goal readback is checked against float32 commands and the
monitor receives the declared active-joint commands.

**69 related fixture tests passed**, including paired callback writes,
partial native-group write failure, reordered layout and delta-command
rejection. No native callbacks have been installed by this work, no deployment
or motion has occurred, and native callback order remains unqualified for the
coupled mode. The fresh-state out/return owner and strict/exploratory admission
protocol are still required before running it.

## Round-Trip Owner Implemented Locally

`scripts/coupled_roundtrip_execution.py` now schedules bounded outward and
return profiles under a single 600-action cap, reserving 60 measured holds.
The existing profile generator supports explicit 11-joint mode with a 0.25 rad
departure bound while retaining its speed/acceleration limits and seven-joint
default. It never compresses a trajectory to fit the action budget.

The owner requires fresh leg-specific admission, measured outward endpoint
and stop before return admission, measured return endpoint/stop, and another
final endpoint/stop check after reserved holds. Failed outward execution or
admission never triggers a blind return. Failures remain latched; incomplete
holds cannot report success.

**86 related fixture tests passed.** Native capture/admission and independent
endpoint/stop callbacks are still unwired. The owner's callback interface is
not evidence that those facts hold in the simulator. No deployment, native
motion, phase completion or new clearance claim occurred.

## Endpoint Evidence Verifier

`scripts/coupled_endpoint_check.py` checks fresh same-episode captures against
the declared coupled endpoint and held-joint origin. The native right EEF
feedback (xyz + xyzw at proprio indices 42:49) is compared to independently
supplied URDF FK in the EEF frame, not the gripper-link frame. Endpoint
tolerances are 5 mm, 0.02 rad and 0.003 rad joint error; held-body/finger drift
limits remain 0.003 rad / 0.002 m. Joint/finger velocity readback is checked at
0.01 units/s. These are exploratory diagnostic thresholds, not calibrated
physical safety limits.

The helper refuses to infer a base stop from raw velocity. It requires a
separate current source-bound base-pose settled receipt, which the native
owner must produce and validate. This dependency is not yet wired; a fixture
receipt is not native stop evidence. Fresh capture and FK/base-stop provider
wiring remain required before execution.

**96 related fixture tests passed.** The GPU was observed idle with no task
worker running; no simulator was launched and no actions or paid calls occurred.

## Base-Settling Provider And Endpoint Binding

`ScanBaseObserver.settled_receipt` now requires six consecutive measured RGB-D
base-pose intervals ending at the current source-bound capture. It rejects
stale windows, missing interval rates, changed episode and latched observer
failure. Exploratory settling thresholds are 0.005 m/s translation and 0.01
rad/s rotation across the window. It still reports `stop_qualified=false`.

`EndpointVerifier` connects the round-trip owner's endpoint callback to the
latest native capture, current base observer and independent EEF FK provider.
It rejects reuse of an earlier endpoint sequence. **115 related tests passed.**

A retrospective numerical check of the last six samples in
`runs/scan-reserved-hold-base-20260924-r1/receipt.json` found maximum rates of
0.00005234 m/s and 0.00002169 rad/s. This shows those retained estimates satisfy
the proposed thresholds, not that a fresh robot is stopped or that the pose
estimator's accuracy is qualified.

Remaining integration: instantiate these callbacks in a native owner with
fresh geometry admission, the correct EEF mounting transform and exclusive
actuator ownership, then run the declared out-and-return experiment. No native
run or phase completion is claimed by this preparation.

## Fresh-Candidate Admission Pipeline

`prepare_coupled_endpoint.py` now derives a right-gripper 10 cm base-forward
intent from a supplied paused proprioceptive capture, with orientation held
and all active joints within 0.25 rad. It performs bounded numerical IK and
endpoint authored-hull checks, emitting the existing admission receipt format.
This is a free-space control experiment, not radio manipulation. The generated
candidate is not a command and is not automatically admitted.

The scene checker now selects descendants of **all changed joints**, rather
than only descendants of the selected arm. This is necessary when torso motion
moves the opposite arm and other body links. Coupled admission requires the
exact active-joint list, unchanged held joints, source stamp, pose-match result
and bounded departure in addition to the existing hash-bound geometry chain.

Replay against a retained reset capture succeeded through endpoint generation,
continuous authored self-separation with tracking allowances (7 subdivision
nodes), and 17 scene-point samples (zero outside-start-ambiguity hits). This is
not a fresh simulator trial or proof of external clearance. **137 related tests
passed.**

Private run: `runs/coupled-fresh-generator-replay-20260924-r1/`

- Endpoint receipt SHA-256: `68554b325683ea59d8efc3a0cee27196e5eec5103f0c9975ad458ed622e46f09`
- Path receipt SHA-256: `86a864f938cb6c71e6236a56eaf3605a80a2fa55b7183402555e2e35dd3c52f5`
- Scene receipt SHA-256: `762756dff7af759f6f32bb86a9fa9a1d91e1edde15b7f16d5d1517409c24dfd7`

The native owner still needs to invoke this pipeline for its actual current
capture and wire the coupled execution mode. No robot action or paid call was
made by the replay.
