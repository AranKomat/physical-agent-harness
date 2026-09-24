# Phase 5E Legal RGB-D Voxel Gate

**Date:** 2026-09-25

**Scope:** offline falsification of strict whole-body clearance using only legal
RGB-D, legal 61-D proprioception, legally estimated head-camera poses, and pinned
robot-only geometry.

## Result

The bounded Phase 5E gate failed. Even the intentionally optimistic variant,
which retained every causal historical view, assumed exact poses, used no depth
margin, and applied no age or geometry-revision invalidation, did not cover the
robot geometry newly occupied at legal capture boundaries.

This closes the current strict-clearance sensing branch for the default R1Pro
cameras. It does not show that collisions occurred. It shows that legal evidence
was insufficient to certify the tested motion.

## Source Run

The source was a no-paid fixed-routing Behavior-Skill radio run:

- policy: `pi05-pt50-skill`;
- policy actions: 256 in eight 32-action chunks;
- settling actions: 9;
- stop condition: five consecutive legal settled samples;
- simulator steps: 265;
- legal RGB-D captures: 18;
- legal proprioception samples: 266;
- motion label: exploratory;
- `motion_qualified=false`;
- `clearance=unknown`;
- hidden evaluator state read only after control ended;
- task result: false, final Q score 0.0;
- paid model calls: zero.

The public harness completed normally after a private adapter fix kept diagnostic
telemetry outside the exact three-field RPC receipt metadata contract. An earlier
`r1` run executed the same action exposure but failed harness bookkeeping at that
contract boundary; it was retained rather than overwritten.

## Gate Construction

For every consecutive legal capture boundary, the analysis:

1. reconstructed the R1Pro configuration from legal proprioception;
2. inferred base-to-local-map pose from the legal head-camera odometry estimate
   and audited robot/camera forward kinematics;
3. derived wrist-camera poses from the same robot-only kinematics;
4. projected newly occupied authored collision vertices into causal RGB-D rays;
5. separately voxelized authored convex hulls at 3 cm as a conservative volume
   proxy;
6. kept unobserved space unknown;
7. compared current-only, two-second age-limited history, all-history optimistic,
   and revision-invalidated uncertainty-inflated variants.

Any robot action may change scene geometry. Without a qualified world-change
detector, the conservative variant invalidated older views. The optimistic variant
retained them only to provide an upper bound.

## Aggregate Evidence

| Variant | Authored vertices free | Convex-hull voxels free |
| --- | ---: | ---: |
| Current-only, zero error | 9,966 / 21,472 (46.4%) | 129 / 3,816 (3.4%) |
| Age-limited causal history, zero error | 10,683 / 21,472 (49.8%) | 187 / 3,816 (4.9%) |
| All causal history, optimistic upper bound | 11,504 / 21,472 (53.6%) | 719 / 3,816 (18.8%) |
| Revision-invalidated, 3 cm pose uncertainty | 7,026 / 21,472 (32.7%) | 56 / 3,816 (1.5%) |

Seven of 17 capture transitions contained authored vertices outside the previous
robot envelope after a 1.5 cm jitter allowance. Representative optimistic results:

| Transition | Newly occupied vertices | Still unknown |
| --- | ---: | ---: |
| step 0 to 32 | 996 | 933 |
| step 32 to 64 | 4,808 | 4,808 |
| step 64 to 96 | 6,044 | 1,221 |
| step 96 to 128 | 4,187 | 1,193 |
| step 128 to 160 | 2,947 | 1,098 |
| step 192 to 224 | 2,375 | 627 |
| step 224 to 256 | 115 | 88 |

The legal pose trajectory was checked as a confound. It showed approximately
7.6 cm net translation and less than 1.3 degrees of rotation, rather than a large
odometry discontinuity.

## Boundaries

- No simulator object pose, segmentation, scene geometry, collision state, contact
  state, task state, or future frame entered the analysis.
- No action or model call was issued by the offline gate.
- Capture-boundary endpoints were checked. Intermediate swept volume was not
  certified.
- Authored vertices form the blocker test. Convex-hull voxels are a conservative
  volume proxy and are not native cooked collision geometry.
- The 3 cm uncertainty value is a declared sensitivity setting, not a calibrated
  sensor bound.
- The result does not qualify an ESDF, native collision model, or motion authority.

## Artifact Identity

- successful fixed run owner report:
  `1528e5ed4fb0c4a34135c61253a32ddbdeb87f7f59a6e80e46a6658a102fb25d`;
- legal observation trace:
  `8535bbe5cc9ae037766a0f6f990c91bf6391d1c14b2c26b68f1a656b206a1825`;
- legal motion trace:
  `f938425585b3c32ff44014bc84fc3efff88b030e5d7011c1a95696cdcdd73933`;
- Phase 5E analysis:
  `566df5e31dafc8f9fc146d3a601f503d647dca1c4900be482816ed577a95d2bd`.

## Decision

Do not build a permanent 3-D mapping subsystem or run more nearby camera/posture
searches for this embodiment. Strict Phases 6-9 remain blocked. Continue BEHAVIOR
only on the clearly labeled exploratory track, and use hidden simulator truth only
for retrospective scoring.

Before paid recurrent-GPT comparisons, demonstrate one semantically useful,
independently verified physical effect in a development fixture with a visible,
easily reachable object. A grasp and short lift, visible displacement to a target,
or verified press is sufficient. This fixture is an integration qualification, not
a BEHAVIOR benchmark success claim.
