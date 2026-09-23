# Simulated Gripper Closure Geometry

CPU-only preparation for the missing R1Pro GraspGenX profile. No inference,
downloads, robot actions, paid calls or shared-host modifications. This is not
Phase 9 execution or a promotion of any motion capability.

Using the pinned private robot USD and processed URDF, extracted all eight
enabled convex-hull colliders on each of four fingers: 32 total. Validated
meter units, parent links, opposed prismatic axes, 0--0.05 m joint limits,
mesh topology and unchanged input hashes. Coordinates use each hand's gripper
link frame, not an invented learned grasp frame.

For each collider, exported the convex hull of its closed and open vertices.
For a rigid convex body under pure linear translation, this encloses the entire
continuous closure sweep, rather than just sampled postures. Endpoint transforms
were checked to differ only by the expected 50 mm translation. The private NPZ
contains hull vertices and plane equations, with a source-collider manifest in
the receipt. This is authored geometry without native cooking/contact inflation;
it is not upstream GraspGenX closure metadata or external-world clearance.

Whole-finger projection along the closing axis gives identical results for both
hands: -104.404 mm at closed limits and -4.404 mm at open limits, increasing by
100 mm. Negative projection separation is not evidence of collision: components
at different X/Z positions can overlap in Y projection. It demonstrates that
whole-finger extents cannot substitute for contact-pad aperture. Accordingly,
`max_opening_m` remains unset and `graspgen_profile_ready` remains false.

Remaining prerequisites include identifying pad/contact geometry, defining the
learned grasp-to-TCP transform, exporting the full upstream gripper package,
provisioning reviewed model artifacts and validating proposal-only inference.
Strict clearance and stopping remain separate execution gates.

Private artifacts: `runs/gripper-closure-geometry-20260923-r1/`.

- Receipt SHA-256: `2097d5d5711ae6a6b3cd283adcaff9e6f5f93a46ca9b2eefd43a0ae538c8cbc6`.
- Geometry SHA-256: `88344168211e22c3fa00c3222e5343538a461514060b81c0f83d124463e000ce`.

Two focused tests pass: continuous-translation containment on a known solid and
rejection of nontranslating, mismatched or nonfinite geometry. Changed code passes
Ruff. Derived robot geometry stays private under the original asset terms.

## Inner-Volume Follow-Up

Read the actual upstream wizard at pinned revision
`b9429097728cb1c430dd78b92edf17ba318aad03`:
<https://github.com/NVlabs/GraspGenX/blob/b9429097728cb1c430dd78b92edf17ba318aad03/scripts/gripper_config_wizard.py>.
Downloaded source SHA-256:
`dd07cb86cb1be4d7c020f8eda707b6a3ebd0253c8cd9cedf2cdcf72635ed2272`.
The upstream source was read, not imported or executed.

Its conditioning boxes describe the **inner space between fingertips**, at open
and half-open configurations, not occupied finger closure hulls. The wizard uses
+Z for approach and +X for closing; `base_rotation` aligns the asset accordingly.
It writes `sweep_volume.extents/offset/extents2/offset2`, with `fingertip` copied
from the open box center and `standoff` derived from its Z extent. These are
annotation conventions, not evidence that the native EEF is the learned origin.
Do not copy the closure-hull archive into these fields.

A new private section measurement intersects the authored convex finger hulls
with Y-directed lines at X = -5, 0, +5 mm and Z = -70, -65, -60, -55, -50 mm
in each gripper-link frame. It records all intersected colliders at closed,
half-open and open joint limits: 90 sections across both hands.

At X=0, Z=-60 mm (the native EEF point), left-hand inner separation is:

| Joint position per finger | Authored section separation |
| --- | ---: |
| 0 mm | -1.685 mm |
| 25 mm | 48.315 mm |
| 50 mm | 98.315 mm |

Across the 15 left-hand sections, open separation ranges from 98.314 to 98.527 mm.
Negative closed separation means the authored hull intervals overlap on these
lines; it does not establish actual native contact behavior. Cooking, contact
offsets, collision filtering, palm/camera obstacles and material properties remain
outside this measurement. Finite section samples do not certify a continuous
free-volume box. No production gripper profile or opening limit was populated.

Receipt: `runs/gripper-inner-sections-20260923-r1/receipt.json`, SHA-256
`42a5738cd8af5bd380870641aa571a95b5592a23d7ef6259065a660fe2199a90`.
Four geometry tests pass, including known-box section intersections, misses,
translation and invalid input rejection. Ruff passes. No GPU or motion used.

## Standalone Hand Export

The retained processed URDF referenced unavailable standalone mesh files; the
pinned USD contained the actual authored mesh data. Exported a private left-hand
URDF with four links: palm, both fingers and the attached wrist-camera housing.
The package contains four visual triangle meshes and 32 authored convex collider
meshes. The camera housing is included rather than omitted from the hand shape.

All 36 meshes pass export/reload vertex and face checks (1e-12 m vertex tolerance).
The standalone URDF loads with both visual and collision meshes enabled, resolving
all its mesh dependencies. Sixteen full-robot-versus-exported-hand FK comparisons
pass with zero matrix discrepancy: four links at closed, half-open, open and an
asymmetric finger configuration. Original joint axes, limits, origins and inertial
records are preserved. Input hashes are unchanged.

Private directory: `runs/simulated-gripper-export-20260923-r1/`.
Receipt SHA-256:
`a37bbc15fa395f4bb0ff32aaf9bb87b8d5c1cad2a8938b202be7995d137f6c1f`.
Its manifest covers the generated URDF and every mesh. Assets remain private;
visual textures/materials are omitted. No upstream model or wizard was executed.

This resolves mesh dependency closure for the selected hand, not the remaining
inner-volume annotation, learned-frame/TCP calibration, native contact behavior,
model provisioning or execution qualification. No `config.json`, inferred model
opening limit, or ready-to-run GraspGenX worker configuration was generated.

## Candidate Frame Convention

Read-only inspection of upstream `grasp_server.py`, `x_grippers.py` and
`scripts/demo_object_pc.py` at the same pinned revision confirms that the sampler
restores the object centroid and the demo applies the returned grasp directly
to the canonical gripper mesh. The `tool_tcp_transform` metadata is not applied
by that sampler return path. Do not add the object centroid or fingertip offset
again before the adapter's single TCP composition.

For this exported hand, a candidate canonical rotation maps native +Y to model
+X, native +X to model +Y and native -Z to model +Z. It is a proper rotation,
not a reflection. With column vectors, let B map native-root coordinates into
canonical coordinates. Then `T_world_tcp = T_world_grasp * B * T_native_tcp`.
The pinned robot configuration defines native TCP translation (0,0,-0.06) m
and xyzw quaternion (0,1,0,0). Under this candidate alignment:

```text
B = [0  1  0  0]       T_grasp_tcp = [ 0  1  0  0   ]
    [1  0  0  0]                     [-1  0  0  0   ]
    [0  0 -1  0]                     [ 0  0  1  0.06]
    [0  0  0  1]                     [ 0  0  0  1   ]
```

Private `gripper_frame_candidate.py` implements this explicit candidate. Four
tests check axes, TCP translation, world-frame composition at three rotations,
double-offset disagreement and rejection of nonrigid input. Ruff passes.
The candidate has not been adopted: exported canonical mesh/config inspection
and landmark checks are still required before activating a worker profile.

Upstream source SHA-256 values (no imports or model downloads):

- `grasp_server.py`: `72080843fdf303f4c01302b50f0e719fb6abaf7aab8897ec098d9cd075cae8bb`.
- `demo_object_pc.py`: `358f123b8ab98b38539bfd2b420144bc37de050b338897ee29a94498a30e7875`.
- `x_grippers.py`: `a1e60784ee788b3d2b882987847c5671d23c7dd2adff1a8f3b74c4f8962c67cc`.

## Reviewable Configuration Candidate

Generated `runs/gripper-config-candidate-20260923-r3/config-candidate.json` and
`review.png`, not a loadable production `config.json`. Candidate boxes are
96 x 10 x 20 mm (open) and 46 x 10 x 20 mm (half-open), centered at canonical
(0,0,60) mm. They use the explicit candidate rotation above. Symmetry is false
because the complete hand includes the offset wrist-camera housing. The candidate
bbox derives from authored collision geometry rather than upstream visual bounds.

Linear-program feasibility checks find no intersection between these boxes and
any of the 32 independent authored convex colliders at their respective poses:
64 tests, zero intersections. Unlike the earlier line samples, this checks whole
boxes against whole convex hulls at these two poses. It does not check the entire
closing motion, native contact inflation, scene obstacles or forces. Three
orthographic projections per pose were rendered and visually inspected; the
boxes occupy the fingertip region around the native TCP.

Two failed preparation attempts are retained:

- r1: collision scene graph was not enabled in the URDF loader; no result.
- r2: the loader merged collision meshes per link. Taking a hull of the merged
  geometry filled real gaps, yielding four intersections among eight merged
  checks. This is an invalid representation for this annotation check.
- r3: explicitly iterates all independent collider files; input hashes unchanged.

Regression coverage includes a separated-collider example demonstrating why a
convex hull of their union falsely fills the gap. Seven focused geometry/frame
tests and Ruff pass. No upstream inference, robot action or paid call occurred.
The profile remains inactive pending upstream configuration/cache validation;
the result is not Phase 9 completion.

r3 receipt SHA-256:
`b2d514c5e56e576c9dd410adb20489b5f646f53d8ef50c9112c3e88cbcab636a`.
