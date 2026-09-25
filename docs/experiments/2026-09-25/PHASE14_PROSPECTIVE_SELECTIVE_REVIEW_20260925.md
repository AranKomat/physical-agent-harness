# Phase 14 Prospective Selective Review

Date: 2026-09-25

## Result

The preregistered Sol-first, Astra-on-hold rule passed its first prospective
shadow test on a genuinely new object-category pair. The study used a strawberry
from the official `freeze_fruit` task rather than reusing the earlier soda-can or
apple questions.

Before inference, one bounded source fixture staged `strawberry.n.01_1` in the
left gripper. All 30 native actions completed. Evaluator-only scoring measured a
49.931 mm lift with 0.334 mm change in gripper-relative distance. Independent
legal RGB-D and robot-only forward kinematics measured a 50.023 mm lift.

Two M2 packets were then frozen and preregistered:

- positive: strawberry evidence with `strawberry` required;
- negative: the identical evidence with `apple` required.

Sol ran first on each packet. Astra was invoked only when Sol returned `hold`.
The rule remained shadow-only and authorized no robot motion.

| Case | Expected | Sol | Astra review | Selective result |
| --- | --- | --- | --- | --- |
| Strawberry positive | lift | lift | not triggered | correct lift |
| Strawberry evidence, apple required | hold | hold | hold | correct hold |

| Profile | Correct | Calls | Astra calls | Sequential latency | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| All Sol | 2/2 | 2 | 0 | 8.438 s | `$0.00695100` |
| Selective review | 2/2 | 3 | 1 | 12.401 s | `$0.02345975` |

The reviewer triggered on one correct Sol hold and preserved it. Thus this
prospective pair adds one false-correction opportunity with zero observed false
corrections. It did not contain a new Sol error, so the earlier frozen blue case
remains the only observed Astra correction.

## Verifier Generalization Fix

The original legal visual verifier rejected the strawberry before scoring
continuity because it required 100,000 valid color-mask depth pixels. That
absolute threshold had been fitted to the much larger soda-can/apple fixture
surface.

The private experiment verifier now requires at least 1,000 valid pixels and 90%
valid depth support inside the retained component. Its centroid limit is
object-scaled at 3% of square-root mask area, never below 3 px, and mask IoU must
remain at least 0.90. The existing 5% area-ratio and 5 mm depth-stability bounds
remain unchanged.

The strawberry then passed with:

- mask IoU `0.93404`;
- centroid shift `4.717` px under a `5.649` px scale-aware limit;
- area ratio `0.96426`;
- median depth change `0.107` mm;
- legal FK lift `50.023` mm.

The retained apple run also passed the revised verifier, preserving its prior
50.016 mm FK lift result. This fixes object-scale generalization without treating
the color mask as general semantic identity.

## Evidence

- source receipt: `7b109e16b8d19aecfbe72219988bf281476b0d3fc7349b75c349f393e53c58cd`;
- evaluator sidecar: `c8bf1494f73badd59c998a05118945d17eb9ef5a8767194f83ac4a3739be82a2`;
- legal visual verification: `afce824894a0c89c71926c6d3ba5a33b05b11e2981d515c789f0dbb83b2a9603`;
- preregistration: `d12e3eca7f07c092a1462280850ad2c7da29dba792d5f516590fd638aa39e943`;
- coordinator: `1c215381f3facba3815a4b73ec892cc2f4876128c4a765e77fe52ea5352deffa`;
- final score: `cf52a5183cabd0e39ee3122fc6a0882b2cf60b4a3660552db3f0047dd4e5a803`;
- versioned campaign ledger commit: `a5b47c5a`.

The calls ended at 4,194 cumulative requests with `$23.87720292140`
confirmed, `$34.979327322900` unresolved, `$58.856530244300` exposure, and
`$16.143469755700` available under the unchanged `$75` ceiling. There were no
retries or provider fallbacks.

## Interpretation And Next Gate

This is prospective evidence that the selective rule handles a new category and
does not automatically overturn a correct negative hold. Together with the
earlier six-case frozen comparison, it supports Sol as the default and Astra as a
targeted reviewer for M2 holds dependent on historical visual identity or
attributes.

It does not justify automatic motion authority. The prospective cohort contains
only two controlled boundaries, one review trigger, and no new Sol error. The
source state and trajectory remained scripted, external clearance remained
unknown, and `motion_qualified=false`.

The remaining Phase 14 work is system duty measurement on an active workload:
VLA-controlled seconds and DOF-time, perception invocations and cache suppression,
and device-energy measurement where instrumentation is available. Do not derive
those metrics from this scripted memory fixture.
