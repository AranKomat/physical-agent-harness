# Hybrid V0: classical transit, frozen-policy handoff

Implementation overlay prepared 2026-09-21 for public commit
`641cc313dc3bb30b9311e1f3c74bcda178e7f01c`.

## Integration record, 2026-09-21

Integrated additively on top of `f90d69e24985c5317b05489e409a7f91fb294665`.
The bundle's pinned upstream interface hashes still matched. All 16 payload files
were inspected and added; no existing native policy adapter was replaced.
Source archive SHA-256:
`88c92faf42c8e196ac35b325fe2d19b60796b4d1e61755e5e575a03e345f6cd6`.

Integration review added interrupt-safe fault handling and per-sink journal
namespaces so reopening a journal does not collide with old event IDs. Tests now
exercise the actual public `NativeBindings` class and persistent `Journal`, not
only stand-in contracts. There are 135 hybrid tests and 538 full-suite tests;
Ruff and the offline numerical fixture are checked in the real checkout.

The original handoff described the matched radio pair as pending. That pair has
since completed: both candidates failed native task completion, as recorded in
[the current progress report](EXPERIMENT_PROGRESS_20260921.md). This integration
does not rerun or overwrite those experiments and adds no new benchmark result.

Hybrid V0 remains an opt-in library, not an enabled replacement inside
[`experiments/behavior`](../experiments/behavior/README.md). That runner and its
frozen policy recipes remain unchanged. Native controller/gate callbacks are
still required; the qualification template deliberately authorizes nothing.
No paid calls, GPU motion, checkpoint downloads or license acceptance were
performed during integration. The next native milestone is a qualified short
base move and A/B handoff comparison, not simultaneous staging/retreat changes.

## Status and scope

Subsequent native work: the [hold-codec and stationary-settling diagnostics](HYBRID_NATIVE_QUALIFICATION_20260921.md)
passed on radio instance 301. Nonzero base movement and the A/B policy handoff
remain unqualified; this does not promote the template to motion authorization.

This is an executable, opt-in **simulator-only** extension. It is not a claim of
BEHAVIOR success, a qualified R1Pro controller, or a reproduction of SkipVLA.
There are no model calls, checkpoint downloads, training jobs, GPU services or
robot actions on import or in the bundled demonstration.

The implementation provides a composite motor backend, two numerical classical
executors, an optional bounded numerical IK solver, strict handoff/reset protocols,
and tests. Real R1Pro use still needs
private implementations of legal sensor capture, native command encoding,
observed target/IK resolution, swept collision checks and qualified handoff gates.
Those are substantive robotics tasks, not hidden magic in this overlay.

## Why this version

The supplied progress handoff and public `EXPERIMENT_PROGRESS_20260921.md` say that
several multitask policies have functioning native interfaces but have not
completed the reported radio/trash trials. Behavior-Skill approaches and contacts
the radio; Corvid demonstrates some bin grasp/carry behavior but has task-adherence
concerns. Memory has controlled-replay evidence, not a live task-success benefit.
No new training is authorized. The work should remain on BEHAVIOR/R1Pro with legal
RGB-D/proprioception and one frozen multitask motor. Private experiments and
adapters are not all in this public checkout.

Consequently this extension does not add another memory store, a new executive,
a new policy, a task-specific expert selector, or a new neural router. It asks:

> Can a legal classical movement/staging phase improve the usefulness of the
> same frozen motor, without changing its native action interface or recipe?

**Navigation alone will not solve a radio-contact failure.** If the robot already
reaches and pushes the radio, the unresolved issues can include contact location,
precision, progress feedback and observable verification. This overlay does not
implement a radio-toggle primitive, infer electrical state from an appearance,
or substitute a simulator state edit for contact.

## Execution path

```text
Existing GPT executive selects a predeclared semantic action
    |
Existing EpisodeRunner / HarnessRuntime
    |
HybridExecutor (one whole-robot lease across the entire composite)
    |
    +-- NAVIGATE: bounded sensor-derived local waypoint following
    +-- STAGE: bounded collision-checked named-joint transit
    +-- POLICY: original frozen motor, full native action interface
    +-- RETREAT: optional, separately gated classical executor
    |
Existing fresh post-action observation / independent verifier / task ledger
```

Successful internal boundaries do not invoke GPT. An unestablished gate or an
ambiguous native result stops instead of inventing a recovery. The executive is
still the semantic decision-maker; it does not supply raw joint targets or set
`collision_world=True`. Gate callbacks belong to the reviewed private driver.

This first version is **sequential at phase boundaries**. It does not introduce
background executive planning, an objective queue, continuous VLA/classical
blending, a contact classifier, or real-time world advancement while GPT thinks.
The current paused-world experiment remains the baseline.

## Files

| File | Implemented responsibility |
| --- | --- |
| `hybrid_v0/contracts.py` | Immutable legal snapshots, phase/route contracts, evidence-bound gate reports, exact policy identity and reset acknowledgements |
| `hybrid_v0/executor.py` | Whole-robot ownership, phase sequencing, bounded counters/deadlines, stop/recapture/gate/handoff, fault latching and receipt aggregation |
| `hybrid_v0/classical.py` | Local holonomic waypoint follower; rest-to-rest quintic joint trajectory generation and streaming; tracking/collision/step guards |
| `hybrid_v0/ik.py` | Optional finite-difference damped-least-squares IK with joint limits, line search, deadlines and explicit nonconvergence |
| `hybrid_v0/integration.py` | Existing NativeBindings/Journal adapters and A/B/C/D route-budget constructors |
| `hybrid_v0/fixture.py` | Explicitly synthetic numerical test world, not BEHAVIOR or a VLA |
| `hybrid_v0/__main__.py` | Offline demonstration command only |
| `tests/hybrid_v0/` | Contract, controller, handoff, failure-path and integration-contract tests |

Paths in the first column are under `physical_harness/` unless otherwise shown.
The executor and local controllers use only the standard library and existing
repository modules. Optional `ik.solve_ik` uses NumPy, already declared in the
repository's development/localization extras. It is imported only when used.
Existing setuptools discovery includes the new package automatically.

## Frozen-policy contract

`PolicyIdentity` pins checkpoint/revision, a weights or shard-manifest digest,
observation codec, action codec, normalization, inference recipe and instruction
contract. The operator's policy backend must report the **actually loaded**
identity. A change is rejected; merely returning a configured label is not an
independent audit of the serving process.

The wrapper does not mask joints, zero selected VLA outputs, change normalization,
replace temporal ensembling, alter camera ordering, pad a cross-embodiment vector,
or choose another checkpoint by task. The same original private `run_skill`
implementation owns each policy phase.

History/queue reset is required on entry from classical motion, first policy
entry, or a changed instruction. It is **not** repeated between consecutive,
unchanged policy blocks. Reset acknowledgement must confirm old action chunks,
temporal history and outstanding inference have been drained. A stateless server
may legitimately acknowledge a no-op reset, but an adapter must establish that it
is stateless; `lambda _: True` is not a valid implementation.

A reset must not reset the simulator, relocate an object, retrain weights, or
change the published noise/prefix/ensemble recipe. Budget caps may truncate an
episode, but the policy's internal serving recipe remains unchanged.

## Handoff admission is not baseline admission

A full-task checkpoint starting from an ordinary benchmark reset may need to
search before its target is visible. `policy_entry="ordinary_start"` therefore
requires `ordinary_start_or_uninterrupted_policy` plus the interface/settled
checks, not target visibility or a pre-grasp condition. Use this for condition A.

After classical movement, `policy_entry="handoff"` requires current target
observation and a qualified handoff envelope. The engine refuses to use the
ordinary-start exemption after a classical phase.

The handoff envelope is an empirical hypothesis to qualify: normal base/torso/
arm posture, appropriate camera view, target scale, gripper state and acceptable
tracking residual. Do not invent a universal 15 cm or 30 cm switching distance.
Use legal live observations and robot-only geometry; use permitted training/demo
material to choose a candidate envelope, then test ordinary-start rollouts.
Do not silently filter out rejected handoffs from the comparison denominator.

## Classical controllers: what they do and do not do

### Base

`HolonomicNavigation` follows a bounded sequence of `BasePose` waypoints in the
current estimated local map. It converts map-frame XY error to body-frame
velocity, bounds linear/angular speed, checks freshness and progress, and stops
on an unknown/blocked corridor or exhausted budget.

It is **not** a room-scale navigation stack. Supply waypoints from the existing
sensor-derived occupancy/topology pipeline or a qualified native navigator.
`pose(snapshot)` must compose estimated camera pose with calibrated robot-only
transforms to obtain base pose. A camera pose is not automatically a base pose.
Do not copy exact simulator XY or pre-survey the evaluation scene.

The `safe` callback must cover unknown/occupied space, the full robot footprint,
stopping distance, torso/arms and carried objects. Dynamic obstacles and changed
goals must be considered at each step. This local proportional follower provides
no independent dynamic-collision guarantee or acceleration-limit certification.
The audited native controller must enforce its actual limits.

### Arm/torso staging

`quintic_transit` produces a rest-to-rest named-joint trajectory with specified
per-joint velocity and acceleration limits. It checks every **swept segment** via
an injected full-robot collision callback. `JointTransit` rechecks collision and
measured tracking before each streamed controller tick and verifies the endpoint.

`JointTransit` itself is not IK and does not find a path around obstacles. It fails when a direct
joint-space route is blocked. The private engineer can resolve legal observed
targets using the audited robot-only FK and a qualified IK service, or replace the
backend with a qualified cuRobo/VAMP/other planner behind the same phase contract.
Neither an endpoint-only collision test nor a visually plausible SceneArtifact
qualifies swept collision clearance. Unknown geometry remains unknown.

The joint target and untouched-axis holds must be encoded using the **actual
native controller conventions**. On the reported R1Pro setup the action is 23-D,
not a zero-filled 61-D proprioceptive vector. Do not use fixture encoders as R1Pro
encoders. A zero in an absolute joint channel can be a motion, not a hold.

### Optional numerical IK

`ik.solve_ik` can use the private robot-only FK implementation already described
in the handoff. It accepts measured seed joints, an observed target pose in the
same frame, explicit joint limits and per-joint search-step limits. It uses a
finite-difference spatial Jacobian, damped least squares and descending line
search, with deadlines, cancellation, residuals and explicit nonconvergence.
Its SO(3) error handles large rotations including the near-pi case.

This is a local kinematic solver, not an obstacle planner or a calibrated R1Pro
IK certificate. A converged result still needs swept collision checking, native
tracking qualification and the policy handoff envelope. It can stall at joint
limits or singularities; failure does not authorize a guessed pose. Search-variable
clamping is not clipping a learned policy's native action vector.

A private entry guard may compute/cache the IK and transit candidate using its
supplied deadline, bound to the exact snapshot fingerprint. The execution callback
must use that candidate or reproduce and recheck it deterministically; checking
an unrelated trajectory is not admission for a new motion. Do not cache a target
across an observed object movement or a localization-frame change.

`StepPort.step` advances exactly one controller tick. All streamed/hold/settling
steps must be counted in the phase receipt. A `stop` or `observe` callback must
not secretly advance the simulator or perform uncounted corrective movements.
Put needed settle ticks inside the native phase budget, then attest measured
settling at the gate.

## Required gates

| Boundary | Minimum checks |
| --- | --- |
| Classical entry | `robot_settled`, `localization`, `collision_world`, `trajectory_validated`, `payload_model` |
| Classical exit | `robot_settled`, `target_reached` |
| Policy handoff entry | `robot_settled`, `policy_interface`, `target_observed`, `handoff_envelope` |
| Ordinary-start policy entry | `robot_settled`, `policy_interface`, `ordinary_start_or_uninterrupted_policy` |
| Policy exit | `robot_settled`; additional task-specific checks can be required |
| Optional retreat | All classical entry checks plus `safe_release_or_stable_payload` in the supplied D route |

Each `GateReport` is bound to the phase, boundary and exact snapshot fingerprint.
Missing, false or unknown checks reject admission. Every check cites evidence
handles; the private provider must resolve those handles and independently
establish the check from allowed sensors/calibration. The dataclass cannot prove
that a caller's collision assertion is true. This is a trusted-adapter boundary,
not a physical-safety certificate or security sandbox.

Do not automatically retreat after a failed grasp, while an object is slipping,
or through unobserved geometry. A successful bounded policy prefix is not proof
of grasp, release, contact, task progress, or safe payload attachment.

## Integrating with the private driver

1. Construct the original native driver and keep a reference to its original
   `run_skill`, `observe` and `stop` callables. Preserve the exact published
   policy observation/action/normalization/horizon/ensemble recipe.
2. Expose `observe_hybrid(deadline) -> Snapshot` using the same current legal
   envelope as the public observer. Supply actual source-capture monotonic time,
   local-frame epoch and sensor-geometry revision. Reading an old frame from disk
   must not refresh its capture time. All clocks must be reconciled on the host.
3. Implement and qualify entry/exit gate providers, native stop/queue-drain,
   policy identity/reset and classical native codecs. Do not return all-true gates
   by copying `FixtureWorld.guard`.
4. Create `Backend` instances for **only** qualified regimes in domain
   `behavior_sim`. No fixture qualification can authorize this domain.
5. Instantiate `HybridExecutor` with motion permission explicitly opted in,
   one frozen policy identity, and an existing `Journal` sink. All actuator
   writers must share the same ownership boundary or be disabled. The Python
   lease does not stop another process from commanding the simulator.
6. Wrap original `NativeBindings` with `wrap_native(native, hybrid)` inside the
   existing native process. `observe` is preserved, and outward receipt metadata
   remains the exact three fields accepted by `ProcessNative`.
7. Let the existing executive select the same predeclared semantic action ID.
   Its `Action` step/chunk/wall caps must cover the whole composite. Route phase
   caps cannot exceed those outer caps. Verification remains downstream.

Sketch of the final assembly (the named private implementations must exist):

```python
from physical_harness.hybrid_v0 import HybridExecutor, journal_sink, wrap_native

# original_native is the existing, qualified NativeBindings.
# backends call ORIGINAL run_skill, never the wrapped method.
hybrid = HybridExecutor(
    episode=episode,
    routes={"press-radio": selected_experimental_route},
    backends=qualified_backends,
    observe=private_driver.observe_hybrid,
    stop=private_driver.stop_and_drain,
    policy=loaded_policy_identity,
    emit=journal_sink(journal, prefix="trial-001-hybrid"),
    domain="behavior_sim",
    allow_simulated_motion=explicit_motion_permission,
)
native = wrap_native(original_native, hybrid)
```

This is an assembly sketch, not a bundled private driver. `native_skill_type` on a
phase can preserve an upstream dispatch string. Parent metadata/destination is
carried through; phase IDs and budgets are overridden explicitly. No new GPT or
provider integration is needed.

A synchronous callback must bound its own wall time. Cancellation is cooperative
and checked between operations; a Python timeout cannot safely kill an executing
robot callback. Unacknowledged stop retains the whole-robot lease. An exception
latches the session until operator review; a later stop acknowledgement alone
does not automatically make the session reusable. Do not erase unresolved leases
or reconstruct a fresh executor merely to continue an ambiguous action.

The public runner treats a pre-dispatch exception as an unresolved/failed run,
not successful `finish`. An all-no-op motion route is not a useful motion request:
use existing passive inspect/verification when a target is already satisfied.

## First experiment, not an architecture expansion

Do not interrupt or restart the active matched policy pair described in the
handoff. First read its completed receipts when available and preserve it as a
separate fixed-menu supervision condition. Do not mix transport/protocol changes
into a run that has already started.

Qualify one short base move and one stopped handoff before a full trial. Keep
staging/retreat disabled until their own native qualification passes. A useful
first hybrid comparison is A versus B, not simultaneous introduction of A-D.

`ablation_routes` constructs these **experimental conditions**, not four choices
for GPT to select within one rollout:

| Condition | Execution |
| --- | --- |
| A | Same original frozen policy from ordinary reset |
| B | Classical navigation/staging-region arrival, then full-interface policy |
| C | B plus classical arm/torso staging, then policy |
| D | C plus separately admitted classical retreat |

Use `routes={"press-radio": conditions["B"]}` for a B trial, for example. Give A
and B the same outer action ID, executive/verifier protocol and policy instruction.
Use independent ordinary resets at matched starts. Do not teleport into a
successful handoff state for the main comparison. Prepared-state tests are
separate diagnostic fixtures, never ordinary-start benchmark outcomes.

All conditions have the same **total** action ceiling. Classical steps consume
that budget; policy exposure is consequently different. Preserve each policy's
own published inference cadence. Do not force Corvid's ensemble to use the
Behavior-Skill 32-action recipe for superficial symmetry. Report actual steps,
simulated time and wall-time censoring, not just a common nominal cap. The default
3224 actions is a handoff diagnostic ceiling from the existing radio experiments,
not a claim that it is adequate for all BEHAVIOR tasks.

No API/GPU budget is authorized by this overlay. The constructor, tests and demo
start no remote services. Use the existing approval/ledger/receipt system for any
new paid or native trial.

## What to record

Phase-start reservations and validated phase receipts flow into the existing
journal. Record admission rejections, true reset acknowledgements, full native
recipe identity and actual counters. `metrics()` separates recorded classical
and policy steps, a policy-controlled simulated-time fraction, policy calls and
unresolved receipts. It marks energy as unknown. These are not GPU joules or
measured neural inference time. Full-interface policy control is retained; this
version does not reduce policy action-space dimensionality.

Keep native scorer/Q out of all agent inputs. Analyze it out-of-band with the
video, contact/displacement evidence and external verifier receipts. The hybrid
returns no observed goal predicates of its own. In particular radio power still
needs a qualified legal observable cue; successful joint motion cannot establish
that the radio is electrically on.

A positive result needs ordinary-start controls and repetitions. A failed
handoff is still useful evidence: distinguish unavailable geometry, unreachable
staging posture, stale observation, policy reset failure, language-contract
mismatch, motor precision, inadequate observation and unknown task verification.
Do not call two binary failures a winner and do not infer no motor ability from
zero final Q.

## Running the software tests

```bash
python -m pytest -q tests/hybrid_v0
python -m physical_harness.hybrid_v0 demo --output runs/hybrid-v0-fixture-001
# After applying to the full checkout, also run its complete existing suite:
python -m pytest -q
ruff check .
```

The demo uses a small synthetic base/joint state with an explicit fake policy.
Its all-true geometry checks and arbitrary 23-wide encoders are ONLY test doubles.
Neither its successful endpoint nor its policy-action fraction estimates R1Pro
performance. Never connect it to a native controller.

## Source basis and reproducibility

Source of current experimental constraints: the user-supplied *Physical Agent
Research: Progress and External Research Handoff*, 2026-09-21, plus the public
progress report at the pinned commit. These are experiment reports, not new
independent replications performed for this overlay.

The design reuses existing `LegalObservation`, `SkillRequest`/`SkillReceipt`,
`JobManager`, native receipt metadata and Journal contracts. The new control
utilities and orchestration are original implementation code; no external
robotics stack or model weights have been vendored. The discussion of hybrid
classical/learned control is inspiration, not a claim to implement a paper's
trained target-selection/switching module.
