# R1Pro Frozen Single-Joint Path Audit

## Scope

CPU-only robot self-collision diagnostic using the pinned authored convex hulls,
the existing measured active/held-joint preparation, and native r4 filtering.
No new GPU run, model call, command, scene geometry or motion authorization.
This advances the robot-model part of Phase 7, not native execution or world
clearance. The three unresolved wheel spheres remain excluded explicitly.

The frozen set contains 28 paths: each of seven arm joints changes by +/-0.01 rad
on each arm. Every other measured joint stays fixed, including the other arm,
torso and fingers. These are separate paths from the measured start, not a
concatenated 28-step trajectory. Single-arm FK was previously cross-checked
against cuRobo on these postures.

The diagnostic derives exclusions from 14 verified native explicit filters and
disabled connected-joint collision flags. It does not edit/union lists into the
legacy planner configuration. Same-owner compound shapes are not tested against
each other. There are 161 convex meshes and **11,003 eligible pairs** per posture.

## Failed Numerical Assumption

Initial r1 reported all paths passing using FCL distances as starting clearances.
That result is superseded, not promoted. R2 added independent endpoint checks and
failed. R3 preserved the exact contradiction: on `left_arm_joint2:-0.01`, the two
wrist-camera meshes had a baseline FCL distance of 0.504117451 m, endpoint distance
of 0.496267146 m, and displacement-derived lower bound of 0.496825143 m.
The endpoint was **0.557998 mm below the bound**, despite the independent hull
vertex displacement check passing.

The solver-level cause remains unestablished. Raw FCL distances are therefore
not qualified lower bounds. Earlier authored-convex distance values remain
diagnostic values, not certified clearances; their independent disjoint-AABB
witnesses remain useful. No FCL tolerance or acceptance threshold was relaxed.

## Revised Continuous Bound

R4 uses explicit hull support bounds instead of raw FCL distances:

- At the start, calculate the largest positive separation between the two hulls'
  axis-aligned coordinate intervals. This is a lower bound on Euclidean distance.
  Overlapping intervals provide zero, not an inferred clear gap.
- For one rotating subtree against a stationary shape, subtract `R * abs(angle)`,
  where R is the maximum hull-vertex distance to the fixed rotation axis.
  This bounds displacement over the entire arc, not only the endpoints.
- When both shapes share the same rigid rotation, their mutual distance is
  invariant; stationary/stationary pairs are invariant too.
- Independently verify endpoint vertex motion against the arc bound and check
  endpoint FCL results for contradictions. FCL remains a diagnostic check, not
  the source of the lower-bound certificate.

The diagnostic pair threshold remains **11.070691 mm**: twice the maximum
measured native contact offset plus a predeclared 1 mm diagnostic buffer.
This is not a calibrated physical safety margin or tracking-error allowance.

## R4 Result

- All **28/28** paths pass the revised diagnostic.
- Minimum whole-segment lower bound: **20.907308 mm**.
- No reported baseline or endpoint intersections.
- Maximum endpoint point-bound residual: zero; no endpoint distance contradicts
  its conservative bound at the unchanged consistency tolerance.
- Source/input fingerprints unchanged. Runtime approximately 4.86 seconds on
  the Mac, not a controller latency benchmark.
- Ten focused tests pass, including axis-gap conservatism, full-arc movement,
  same-subtree invariance and invalid inputs. Full private suite: **917 passed,
  one existing skip**; Ruff clean. Public production code unchanged.

All four attempts remain in private local `runs/r1pro-joint-path-audit-20260923-r*`.
Authoritative r4 receipt SHA-256:
`894da724219772ab9046f25430fdba34f91bd3fd362a204c4c4dd75d846b4a57`.

## Next Gate

This establishes a bounded conservative self-separation result for the frozen
non-wheel geometry and ideal joint interpolation. It is not a certificate for
fresh starts, simultaneous multi-joint trajectories, policy motion, actuator
tracking, braking or contact. It does not complete Phase 7.

Next resolve the wheel/active-shape scope and construct a sensor-derived external
clearance check for a selected free-space arm path. Then qualify native control
timebase, held-joint tracking and stopped endpoint/return behavior under a bounded
approved trial. Do not run another geometry/model bake-off merely because these
execution gates remain open.
