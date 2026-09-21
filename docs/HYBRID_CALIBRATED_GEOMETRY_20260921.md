# Calibrated Hold, Odometry And Robot Geometry

## Scope

A fresh ordinary radio reset (public instance 301, seed 0, pinned BEHAVIOR
`b1979916ec1549b10a4e65e630bc6504a9af1b00`) repeated the stationary hold with
camera intrinsics captured at each observation boundary. Five controller actions
produced five consecutive settled samples, exactly as in the earlier run.
This is same-seed reproducibility, not independent scene/start replication.

No VLA inference, GPT call, object-pose input or task-success claim was made.
The native worker exited. Thirty-five receipt/evidence files were SHA-256
verified after transfer; the native log and private analysis outputs were retained.

## Calibration And Stationary Localization

All six captures (initial plus five post-action observations) contain intrinsics
bound to session/epoch/sequence, capture timestamp and RGB/depth evidence IDs.
Only native intrinsics are read; no camera/world extrinsics are admitted.
They match the earlier calibration. Maximum torso/arm hold drift remains
`9.059906e-6` in native joint units.

Existing stride-2 Open3D RGB-D odometry was replayed independently for each camera.
Robot-only FK converts camera motion to episode-local base motion, compensating
for articulated camera movement. The existing two-second wall-gap gate remained
active; measured capture gaps were 0.434-0.725 s.

Predeclared diagnostic bounds were 5 mm translation and 0.5 degrees rotation:

| Camera | Maximum estimated base translation | Maximum estimated base rotation |
| --- | ---: | ---: |
| Head | 3.806 mm | 0.105 degrees |
| Left wrist | 3.188 mm | 0.326 degrees |
| Right wrist | 1.899 mm | 0.200 degrees |

All passed those **stationary-only** bounds. Integrated legal base-speed
magnitudes indicated approximately 0.116 mm of path length and 0.000158 rad of
absolute yaw over 0.166667 simulated seconds. These velocity integrals are not
independent ground-truth position measurements. The discrepancy cautions against
treating odometry as exact at millimetre scale. This does not qualify moving
localization or establish a calibrated pose-uncertainty distribution.

## Planning Spheres Do Not Enclose The Authored Robot

The robot-only USD asset was opened separately from the simulator scene. At the
retained legal joint posture, 164 enabled authored collision meshes contained
9,639 vertices. **4,053 vertices lay outside the combined 79 upstream planning
spheres**, with a maximum distance of **53.206 mm** beyond that sphere union.

This disproves conservative enclosure of those authored vertices at this posture.
It does not quantify collision rate or prove anything about contact with scene
objects. Runtime collision cooking, wheel substitutions, contact offsets and
payload geometry still require inspection. Checking that vertices lie inside a
nonconvex sphere union would not, by itself, prove full mesh enclosure either.
The upstream spheres must not be silently promoted to a certified full-body bound.

## Accumulation Does Not Remove The Blind Regions

The fresh same-boundary calibration reproduced the earlier sphere-based coverage
counts. A separate diagnostic then used authored per-mesh convex-hull vertices
and face centroids rather than the smaller sphere approximation. For hypothetical
5 cm translations it sampled exposed final surfaces outside the original hull
union. It compared the latest RGB-D capture with all six causally accumulated
captures, aligned using the head-camera odometry estimate and robot-only FK.

| Direction | Exposed mesh samples | Depth-supported, latest capture | Depth-supported, accumulated |
| --- | ---: | ---: | ---: |
| Forward | 14,007 | 151 | 163 |
| Backward | 12,063 | 664 | 670 |
| Left | 12,986 | 643 | 653 |
| Right | 13,030 | 840 | 846 |

These are discretized sample counts, not area/volume coverage or collision
probabilities. The small gains may include estimation noise and subpixel effects;
they are not evidence of meaningful new viewpoint coverage. Even after
accumulation, 765 of 1,153 low forward samples (below 40 cm in the base frame)
remain outside every camera view.

No swept-volume clearance or motion authorization follows from either diagnostic.
Repeated stationary frames do not solve the near-robot observation gap.

## Consequence For Experiments

Keep benchmark admission unchanged and fail closed on unknown clearance. Separate
base response/braking calibration from benchmark navigation: the user authorized
a bounded test in a purpose-built empty simulator scene. That component test
must not be represented as an ordinary radio start, sensor-cleared radio motion,
or an A/B task result. Qualified benchmark motion still needs a usable online
coverage strategy, conservative robot bounds and measured pose uncertainty.

## Private Receipt Hashes

Run directory: `hybrid-calibrated-hold-20260921-r1`.

- Native audit: `7c6b2662448ffcf4cff8c544beec0b5d8c30c49d3fbe32bc01ced1344327484c`
- Odometry: `d82f0bf97420eb1c812ec0f9673a9ceaf0214f18367f6d0fd4a5065780fe1717`
- Proxy audit: `e7620fd927b135007924c8d437b1386b4a2b7abe5d28bc72864439736f4a3214`
- Accumulated coverage: `a28d7457929e4aacdc7fe61c5ec720da5eff2f881290f59c6d535f444339eb7b`

Raw sensor data, licensed robot assets and host details remain private.

## Sustained Radio Follow-Up

`hybrid-sustained-radio-hold-20260921-r1` extended the real radio hold to 60
controller ticks, without exiting after the first five settled samples. It
passed for 2 simulated seconds; all 60 post-action captures met the radio hold
criteria. This contrasts with the [unqualified empty-scene fixture](HYBRID_EMPTY_BASE_DIAGNOSTIC_20260921.md),
but does not establish moving-base stop performance.

The same odometry analysis over this longer trace yielded:

| Camera | Maximum estimated translation | Maximum estimated rotation | Original diagnostic bounds |
| --- | ---: | ---: | --- |
| Head | 7.185 mm | 0.091 degrees | Translation exceeded 5 mm |
| Left wrist | 4.140 mm | 0.493 degrees | Within bounds |
| Right wrist | 3.110 mm | 0.672 degrees | Rotation exceeded 0.5 degrees |

Integrated proprioceptive speed magnitudes were 2.379 mm of path length and
0.003106 rad absolute yaw; these remain consistency diagnostics, not independent
ground-truth positions. The short-trace passes must not be generalized to a
calibrated uncertainty bound or moving navigation. No thresholds were enlarged
after observing the longer-trace failures.

The 364 native receipt/evidence files were hash-verified locally. Receipt hashes:

- Native: `83915db7925ec16be9bebc387203303955de161ac78d9138966db82bb2c7fdbd`
- Odometry: `c92caac52e05501d98053850e8cbfd3d949d210db39eb76950c325c3b8fe40a7`
