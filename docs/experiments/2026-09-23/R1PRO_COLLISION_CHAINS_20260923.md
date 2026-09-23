# R1Pro Conservative Sphere-Chain Comparison

Follow-up to the [single-sphere envelope audit](R1PRO_COLLISION_ENVELOPE_20260923.md).
CPU-only, using the same pinned USD/URDF/generated config and measured posture.
No simulator actions, paid API calls, GPU planning or new collision exclusions.

## Fixed Construction

For each of 161 convexHull colliders, bound the transformed vertices by a
finite cylinder on its longest link-local AABB axis, with deterministic ties.
The cylinder is convex, so it encloses their entire convex hull. Split its
axial interval into K equal slabs; each sphere encloses a complete slab using
radius `hypot(radial_bound, half_slab_width) + 0.001 m`. K=2,4,8 were fixed before
execution. The three boundingSphere-approximation wheel meshes retain the
baseline single spheres, with native cooked coverage explicitly unresolved.

Independent verification reconstructs USD transforms and checks the exact
predeclared construction, 1 mm numerical padding, cylinder enclosure, complete
slab partition, sphere export and 164-mesh inventory. All three pass this
authored-cover proof; before/after hashes match. This is not vertex-only
sphere-union sampling and is not native physics qualification.

## Result At One Measured Posture

| Candidate | Spheres | Overlapping mesh pairs | Link pairs | Worst sphere penetration |
| --- | ---: | ---: | ---: | ---: |
| Baseline, one per mesh | 164 | 128 | 22 | 195.638 mm |
| K=2 | 325 | 77 | 9 | 94.884 mm |
| K=4 | 647 | 49 | 9 | 66.290 mm |
| K=8 | 1,291 | 42 | 9 | 75.481 mm |

Every listed overlapping mesh pair has disjoint transformed authored-mesh
AABBs. Raw sphere-pair counts increase with segmentation (145,218,614) and are
not comparable across K. More segments do not guarantee nested sphere unions
or monotonically decreasing worst penetration.

**None is adopted for planning.** The reduction is useful negative evidence,
not a reason to relax the unchanged 35 symmetric direct exclusions. Native
cooking/contact offsets, wheel shapes, unmeasured wheel/steering defaults,
collision-world construction and swept-path validation remain unresolved.
Stop tuning this cylinder family; the next geometry method needs a materially
tighter whole-volume guarantee or a qualified native collision check.

Private artifacts under `internal/physical-ai-lab/runs/`:

- `r1pro-collision-chains-20260923-r1`: all three candidates, 2.376 s construction.
- `r1pro-collision-chains-audit-20260923-r1`: independent proofs and overlaps.
- Audit SHA-256: `46abbf0edd658262d77a0a79b9042da97eeb469ef407ed273e9c61390fc99f94`.

Builder tests:25; independent auditor tests:47. Full private suite, including
the concurrent Sol migration:818 passed, one existing skip. New scripts/tests
pass Ruff. Licensed coordinates and assets remain private.
