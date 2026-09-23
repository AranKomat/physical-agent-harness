# R1Pro Authored Convex Collision Audit

## Scope

CPU-only follow-up to rejected enclosing sphere/chain candidates. Use existing
pinned USD, URDF and generated configuration, with the fresh stationary r2 legal
proprioception. No simulator-global/object poses, physics mutation, GPU work,
planner calls, paid inference or commanded actions.

Build solid convex hulls from transformed authored collider vertices using
SciPy ConvexHull; orient faces outward and query FCL collision/distance. Keep
all 35 existing symmetric direct exclusions unchanged. Exclude same-owner pairs
as before. Three wheel `boundingSphere` colliders remain explicitly unresolved,
not silently replaced by their mesh hulls. Test the remaining 161 convex colliders.
Distances <=1 micrometer are not classified as separated; this is a numerical
ambiguity threshold, **not a qualified physical clearance margin**.

Backend: python-fcl0.7.0.10, SciPy1.17.1, NumPy1.26.4, usd-core26.8,
yourdfpy0.0.60. Installing FCL added only python-fcl and Cython3.3.0 to the private
local environment; existing dependency versions were unchanged. Seven synthetic
checks cover known gaps, rotation, contact, overlap, solid containment and invalid
input. This is a diagnostic dependency, not a new production collision backend.

## Result

- 11,259 distinct-owner, non-exempt mesh pairs tested.
- Zero reported intersections; zero numerical-contact/unknown pairs.
- Every pair also has disjoint transformed authored AABBs, providing an
  independent separation witness at this posture. The real-asset run therefore
  does not test FCL's behavior on overlapping AABBs; synthetic cases do.
- Minimum distance: **0.46447 mm**, left finger1 to left wrist-camera link.
- Next minimum: **0.51497 mm**, corresponding right-side pair.
- Exactly two pairs are below 1 mm (also below 2 mm).
- Runtime: 2.26 seconds for the complete diagnostic, not a controller latency.
- Source/input hashes unchanged. No original assets or exclusions modified.

Private receipt:
`runs/r1pro-authored-convex-audit-20260923-r1/receipt.json`, SHA-256
`f18f2538b4398cfd649954b3c2d05d51e679b39d945388e8a453fe5b3dcb7a0e`.
The script subsequently received a lint-only variable rename; the receipt retains
the executed script hash. Full private suite before the additional rotation test:
892 passed, one skip; focused collision tests after it: seven passed. Ruff clean.

## Interpretation And Next Gate

The authored convex shapes do not intrinsically self-intersect at this measured
posture, while the prior conservative spheres created false overlaps. However,
submillimeter finger/camera gaps mean a blanket millimeter-scale clearance claim
would fail. Do not remove these pairs or reduce margins merely to permit planning.

Native cooked geometry, contact/rest offsets, wheel/steering geometry, changed
postures, external obstacles and swept paths remain unqualified. The authored
USD contains no explicit contact/rest-offset overrides found by this inspection;
defaults and runtime modifications must be measured rather than assumed zero.
Next: inspect native robot collision/cooking/margin semantics under a zero-action
diagnostic, then compare frozen candidate trajectories only after those quantities
are established. No planner or motion gate is opened by this report.
