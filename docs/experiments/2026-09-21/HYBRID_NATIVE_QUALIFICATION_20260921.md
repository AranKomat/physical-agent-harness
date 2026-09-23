# Hybrid Native Qualification: Hold And Settling

Two bounded native diagnostics were completed on the existing NVIDIA host using
the pinned BEHAVIOR source `b1979916ec1549b10a4e65e630bc6504a9af1b00`, R1Pro,
`turning_on_radio`, ordinary public-test instance 301, seed 0. No checkpoint,
executive, verifier or memory configuration was changed. No GPT calls or policy
inference were made. These are component diagnostics, not task-success trials.

## Results

| Diagnostic | Result | Agent actions |
| --- | --- | --- |
| Native hold/preprocessing equivalence | Passed; maximum absolute hold-vector error `2.9801734e-8` against native no-op | 0 |
| Stationary hold from a fresh ordinary reset | Passed; five consecutive settled samples, `0.166667` simulated seconds | 5 attempted, 5 executed |

The first audit inspected six unexecuted command vectors: hold, forward/backward,
left/right and positive yaw. It checked the resolved controller classes, channel
order, normalization and official preprocessing. Native base inputs map to
`+/-0.75 m/s` and `+/-1 rad/s`; torso/arm commands are absolute positions, not
zero-valued hold offsets. Smooth-gripper commands use the inverse of the loaded
position scaling. Asymmetric/out-of-range finger feedback is rejected.

The initial reset observation was **not settled** under the declared velocity
thresholds. In the zero-action audit, torso velocities included approximately
`0.170` and `-0.359 rad/s`; arm velocities also exceeded `0.03 rad/s`.
Consequently reset completion cannot be treated as a measured stop acknowledgement.

A separate ordinary-reset hold diagnostic used fixed initial joint/gripper
targets and zero commanded base velocity. Its ceiling was 60 explicitly counted
ticks. It exited after five ticks with five consecutive measured settled captures.
Maximum observed torso/arm target drift was `9.059906e-6` in the native joint
coordinates. Final base velocity was approximately
`[-0.000320, 0.000633, -0.000218]` in m/s, m/s, rad/s; final maximum absolute
torso velocity was `0.002846 rad/s`.

Settling thresholds: base translation norm at most `0.01 m/s`, yaw at most
`0.02 rad/s`, arm/torso joint speeds at most `0.03` in native joint units/s,
and gripper speeds at most `0.005 m/s`. Diagnostic abort limits were `0.03`
torso/arm target drift, `0.02 m/s` base speed, or `0.04 rad/s` base yaw speed.
These are explicit diagnostic limits, not physical-safety certification.

## What This Does Not Prove

- There was no nonzero commanded base movement, navigation or policy handoff.
- Stationary settling is not measured braking distance from a moving base.
- Full-robot swept clearance from online depth, unknown-space handling and
  carried-payload geometry remain unqualified.
- Online base localization still needs native integration/qualification. The
  existing 2D occupancy prototype's restricted camera geometry cannot simply be
  assumed to match a moving R1Pro head/wrist camera.
- No radio activation or task-completion predicate was asserted.

Ordinary evaluator loading/reset includes setup physics. Zero agent actions in
the first audit does not mean zero physics ticks. The second diagnostic reports
all five post-reset controller ticks separately. No object pose edits, teleport
staging, scene ground truth, scorer observations or future images were supplied
to a controller. Only the hold targets used current legal proprioception.

## Evidence And Validation

Private evidence was retained locally and remotely. Eight files from
`hybrid-base-hold-audit-20260921-r1` and 35 files from
`hybrid-stationary-hold-20260921-r1` were SHA-256 checked after transfer; native
logs were also retained. Images/depth and host credentials are not published.

Audit receipt hashes:

- Codec: `a9d8e206418992c62bc457c96cf882848f6510ae98c28020620f74246d8e158f`
- Stationary: `561caae4b04a42f739806356a40c95dae1f466e2e85c69f487bbd0080ad13a42`

Both native processes exited; GPU allocations returned to zero. The rental was
left running as requested. No campaign model-call reservations were created.

The public implementation is under `experiments/behavior/base_hold*.py`, separate
from the learned-policy paths. The full offline suite passes 560 tests, including
22 new codec/hold-diagnostic tests. Ruff passes. See the
[runner instructions](../../../experiments/behavior/README.md#hybrid-base-qualification).

Next gate: qualify sensor-derived swept clearance and online local-frame pose,
then a short base move with explicit braking/settling and blocked/unknown-path
tests. Only then connect a measured full-interface policy handoff for A/B trials.
