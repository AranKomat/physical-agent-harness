# R1Pro Authored Collision Envelope Diagnostic

## Result

**Authored-mesh enclosure passes; the candidate is not adopted for planning.**
One sphere per authored collision mesh encloses all 164 meshes / 9,639 vertices,
but produces 128 non-exempt sphere overlaps across 22 link pairs at the measured
posture. All 128 pairs have disjoint transformed authored-mesh AABBs. These are
conservative proxy false overlaps relative to authored geometry, not evidence
that native cooked collision shapes are disjoint.

The worst sphere penetration is 195.638 mm between torso link 4 and right arm
link 3. Their corresponding authored mesh AABBs have a 25.128 mm separating
gap on one axis. No collision exclusions were added to hide this result.

## Method And Provenance

This CPU-only diagnostic used the robot assets and fresh measured joint posture
from the [cuRobo FK check](CUROBO_R1PRO_FK_20260923.md). No simulator, planner,
model API or robot action was run. Private licensed assets remain private.

- USD SHA-256: `6029617cdd3aefce981428058a1c82cffe6af20ae61dc5be1da7334342c3bc52`.
- URDF SHA-256: `b0d76760cbedfbcbe1ddc280380dd5f497bbca380313bc096d7239a2c50dae61`.
- Generated source config SHA-256: `d3eb97811138d00edd83bc2be23f8d1d2e2b17c1bbea237a7cf2f9f89752524e`.

The predeclared candidate transforms each mesh into its owning link frame,
centers a sphere on its axis-aligned bounding box, and uses the farthest vertex
distance plus 1 mm numerical padding. All vertices in the same convex sphere
imply containment of that mesh's convex hull and linear/bilinear faces. This
does not rely on the invalid vertex-only coverage test for a nonconvex sphere
union. Nonuniform mesh scales are included before bounding.

An independent auditor does not import the producer. It reconstructs transforms
from USD world matrices, checks exact collider inventory and exported sphere
consistency, and evaluates overlap using the unchanged 35 symmetric direct
ignore pairs, without transitive expansion. Before/after input hashes match.
Wheel/steering joints absent from the measured packet use explicitly reported
URDF defaults; they are not labeled measured.

Private artifacts under `internal/physical-ai-lab/runs/`:

- `r1pro-collision-envelope-20260923-r1`: candidate and builder receipts.
- `r1pro-collision-envelope-audit-20260923-r1`: independent report and manifest.
- Audit report SHA-256: `fd87ba9bcb5855f5d036de214b542adcdc4691b48c79601c6c2e6e20b373e633`.

The builder and auditor add 43 tests. Full private suite: **730 passed, one
existing skip**. Ruff passes for both scripts and their tests. No public runtime
code changed in this diagnostic.

## Limits And Next Gate

161 authored meshes request convex-hull cooking; three wheel meshes request
bounding-sphere cooking. Cooked geometry, contact/rest offsets and native shape
replacement remain unqualified. The 1 mm pad is not a calibrated safety margin.
This diagnostic does not qualify physical collision, a legal scene collision
world, planning, stopping or motion.

The existing sparse spheres under-cover authored meshes; this replacement
over-covers them excessively. The next bounded geometry check needs a tighter
cover with a whole-volume enclosure argument, followed by independent overlap
and native-cooking checks. Do not shrink radii or expand ignore pairs merely to
obtain a passing posture. GPU FK success remains valid in its separate scope.
