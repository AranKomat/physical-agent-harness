# Hybrid V0.1 experiment utilities

Base reviewed commit: `f2a55805265f5038216dae05c78a4903adb3db55`.

This additive update fills four experiment-support gaps without claiming native
R1Pro qualification or changing the frozen policy recipe.

## Integration Record

Integrated against `fec5a1d014cd2f51f13db5bbbc95b2f8b6fb6c8e`, preserving the
native hold/settling qualification. All delivered payload hashes and the three
reviewed Hybrid V0 blob hashes matched. Archive SHA-256:
`28867fc7215c76f7076d9d484ee4b45ca158c8bb3d1ceb8bf496e53c53c4afa4`.

The supplied installer was truncated at `patch_integration` (`addition = r`),
without the route implementation, executor patch or executable apply/check
entrypoint. It was not run or included in the repository. The standalone modules
were integrated manually; the missing route constructor, package exports and
optional executor callback were implemented from this handoff and its tests.

Integration hardening bounds the candidate search itself (4096 evaluations, not
just the retained list), preserves observation/depth-reference lineage, validates
plan/target snapshot agreement, and rejects recapture calibration or confidence
changes and regressed capture times. Telemetry type, boundary, deadline, freshness
and loaded policy identity are checked before policy dispatch. Existing stop,
reset/history, ownership and interrupt-fault handling remain intact.

The full suite passes 580 tests, including 155 hybrid tests. Ruff passes. These
are offline checks, not a new native movement/handoff result. No GPU trial or paid
model call was launched while integrating V0.1. The
[experiment sequence](../experiments/qualification_queue.md) is the current empirical queue.

## 1. Legal target point -> staging pose

`physical_harness.planning.staging` adds a small geometric staging resolver.

It can deproject a detector-selected pixel plus measured depth through the already
legal pose camera, producing an evidence-bound target point in `local_map`. It then
samples a finite ring of candidate base poses on the robot's current side of the
target. A candidate is retained only when injected callbacks establish:

- full-robot clearance;
- manipulation reachability;
- useful target visibility.

Unknown is rejection. The selector does not read simulator object poses, perform
detection, invent wrist-camera extrinsics, command motion, or replace the existing
navigation/collision gates.

The default radii and angles are engineering candidates, not a policy handoff
distribution. For real experiments, estimate a candidate envelope from permitted
demonstrations and legal live observations, then retain all rejected handoffs in
the denominator.

The private depth reader must verify that the supplied depth actually comes from
the selected pixel in the named source asset. Recording an evidence reference
alone does not prove that measurement. Candidate callbacks must bound their own
execution; the resolver cannot preempt a hung collision or IK service.

## 2. Structured policy-handoff telemetry

`HandoffTelemetry` records the state at a classical -> frozen-policy boundary:
target/base and target/EEF distances when available, target image fraction,
localization/pose confidence, gripper state, controlled joint state, reset
generation, policy fingerprint, and source evidence.

The Hybrid executor records this automatically when a policy backend supplies a
`handoff_telemetry` callback. Telemetry is diagnostic only; it does not satisfy
`handoff_envelope` or any motion gate.

This is intended to answer the key zero-training question:

> Does the frozen checkpoint continue to behave normally after a classical
> intervention, and which handoff states correlate with recovery or failure?

## 3. Equal-policy-exposure diagnostic routes

`policy_exposure_diagnostic_routes()` creates:

- `A-short`: policy only from ordinary reset;
- `B-short`: bounded base transit + the same number of policy-controlled actions;
- `C-short`: base transit + arm/torso staging + the same number of policy actions.

Unlike the existing A/B/C/D end-to-end comparison, **total robot horizons differ**.
These short routes therefore must not be reported as end-to-end success-rate
comparisons. Their purpose is to isolate handoff-distribution effects.

These are equal policy-action *ceilings*, not a guarantee of equal executed
exposure. Record early termination, gate rejection and wall-time censoring. The
helper does not set a policy chunk prefix; the original checkpoint adapter owns
that recipe. Behavior-Skill retains its 32-action prefix.

Suggested first use with Behavior-Skill:

- 384 policy-controlled actions in every short condition;
- a small independently qualified base transit in B/C;
- no GPT, no memory, no retreat;
- full original policy action interface after handoff.

## 4. Paused-world recapture helper

A GPT call can take much longer than the observation freshness limit while the
simulator itself remains paused. `paused_world_compatibility()` compares the
decision-time and dispatch-time legal snapshots while intentionally allowing a
different observation ID and wall capture time.

It requires unchanged simulator time, localization frame epoch, geometry revision,
camera set, proprioception, and estimated pose.

It also requires unchanged intrinsics, camera-frame conventions and pose
confidence. It compares structured state, not image equality, and does not itself
establish that either capture is fresh or that the scene was actually paused.

**It is not wired as an automatic stale-decision bypass.** The current executor
continues to reject an unexpected source observation. The private runner may only
use this predicate after explicitly qualifying a paused-world recapture protocol.
This avoids globally weakening the existing freshness rule merely to accommodate
model latency.

## Recommended immediate experiment order

1. Qualify base action encoding, holds, stop and fresh per-tick evidence.
2. Validate target point + staging pose offline against out-of-band ground truth.
3. Run A-short vs B-short with Behavior-Skill; determine whether handoff causes
   pathological policy behavior before spending on full episodes.
4. Run the equal-total-action A/B comparison.
5. Only after B is healthy, qualify arm/torso staging and run C-short, then A/B/C.
6. Add GPT only after the hybrid motor has demonstrated useful controllability.

No new model, training, memory layer, neural router, contact primitive, or
challenge-success claim is introduced by this update.
