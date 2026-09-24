# R1Pro Custom Camera Coverage Screen

## Question

Can one or two fixed downward RGB-D cameras on a disclosed custom
R1Pro-compatible embodiment observe the robot volume newly occupied by a short
target-directed base segment well enough to justify building that embodiment?

This is a sensor-layout screen, not motion qualification. It sent no actions,
made no paid calls and did not build or render a custom robot asset.

## Protocol

- Start state and target direction: pinned sequence-768 legal RGB-D/proprioception
  boundary from the retained `turning_on_radio` run.
- Geometry: authored R1Pro convex collision hulls at the pinned joint state.
- Sample definition: 2 cm voxel centers in the union of ten translated robot
  hull states, excluding voxels already occupied at the start.
- Segment lengths: 5, 10, 20 and 50 mm along the same target direction.
- Candidate screen: 114 mount positions and 228 occlusion-aware fixed camera
  poses, using the retained native head-camera intrinsics.
- Visibility: image-frustum inclusion followed by ray occlusion against the
  authored robot hulls.
- Decision rule declared before the run: proceed only if one or two low front
  cameras fully cover a short segment. If any voxels remain occluded at 5 mm,
  stop the fixed-camera branch.

The 50 mm control repeated the preceding screen exactly: 1,387 newly occupied
voxels, 1,161 visible from the best single pose, 1,277 from the best pair and
1,347 from the union of every screened pose. The matching `40`-voxel residual
confirms that the parameterized runner preserved the earlier protocol.

## Result

| Segment | New voxels | Best single | Best pair | All screened poses | Missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5 mm | 171 | 124 | 142 | 151 | 20 |
| 10 mm | 286 | 197 | 240 | 260 | 26 |
| 20 mm | 565 | 417 | 495 | 533 | 32 |
| 50 mm | 1,387 | 1,161 | 1,277 | 1,347 | 40 |

At 5 mm, even the union of all 228 screened poses leaves 20 newly occupied
voxels unobserved. Their base-frame bounds span approximately `x=-0.03..0.17`,
`y=-0.31..0.31`, `z=0.05..0.39` metres, so the residual is not confined to one
small front corner that a second symmetric camera resolves.

Private immutable artifact hashes:

| Artifact | SHA-256 |
| --- | --- |
| Screening script | `fc6b410dc95ff79988f3bea72bf93b564c01434227d30ae0045867233e114b7b` |
| 5 mm receipt | `e10921294f60b22c9c11c37795298eb5a3e09023767cbf4d6b805ae233f7bd5a` |
| 10 mm receipt | `fe46e1ec1d3a20b62ffad7ad1e2d1d345e13757e5bdc9f0aba5e0dba445de5a4` |
| 20 mm receipt | `67a76b089b01836ebde6a1908813acd7c41e76d4d137c20f674d4c1ab21f30e9` |
| 50 mm control receipt | `b8675c159530b7704d781694014ae26421f819e490a55ecc32c3f44fa8da7e6b` |

Every receipt records `actions=0`, `paid_calls=0`,
`collision_qualified=false`, `depth_support_tested=false`,
`scene_occlusion_tested=false` and `motion_authorized=false`.

## Decision

Stop this fixed-camera branch under its declared rule. Do not build a custom
fixed-camera asset or broaden the mount grid merely to search for a favorable
pose. The finite grid and convex-hull occlusion proxy do not prove that every
possible fixed-camera design is impossible, but they fail to establish a
promising one even for a 5 mm receding-horizon segment.

Strict Phase 5 therefore still needs a different legal current-clearance
authority. Until one is qualified, Phases 6-9 cannot claim strict execution.
Policy-controlled trials may continue only as a separately labeled non-strict
condition with clearance unknown; they must not be reported as strict transit
or manipulation qualification.

## Limitations

- Convex authored robot hulls approximate optical occlusion and exclude three
  nonconvex wheel colliders.
- The 2 cm voxel grid is a conservative protocol sample, not continuous-volume
  proof, and is coarse relative to the 5 mm segment.
- Scene geometry, rendered depth, camera housings, calibration, latency and
  custom-asset collisions were not tested.
- The finite pose grid does not establish a global optimum or minimum sensor
  count.
