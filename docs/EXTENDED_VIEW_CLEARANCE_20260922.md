# Extended Radio View: Coverage, Not Clearance

## Decision

Sequence 768 improves **upper-body sampled depth support**, but does not
establish clearance for a bounded 10 cm target-directed base segment. Every
exposed final-surface sample below 40 cm is outside all three latest views.
This audit does not authorize strict motion or permit interpreting unknown space
as free. The later, separately authorized simulator-only exploratory probe is
documented in `EXPLORATORY_TRANSIT_20260922.md`; it does not change this finding.

This is an offline sidecar using retained legal RGB-D/proprioception and
robot-only assets. No simulator, remote process, API/model call, runtime motion,
scene/world/object pose, or new acquisition was used. The ongoing acquisition
work was not changed.

## Method

- Latest input: `grounding-radio-extended-20260922-r1/A`, sequence 768, all
  three contemporaneous head/left-wrist/right-wrist RGB-D pairs.
- Comparison: sequence 0 from that run, processed independently in its own
  base frame. No temporal fusion or estimated transform between moving frames.
- RGB/depth URI, content and stamped identity checks use the existing checked
  replay reader. Intrinsics match each capture's stamp/time and evidence IDs.
  The latest accepted radio mask is hash-checked and capture-bound; its camera
  surface median is recomputed from observed depth before robot-only FK maps
  it into the current base frame.
- The hypothetical fixed-orientation, fixed-joint translation is 10 cm toward
  that observed surface in XY: approximately **9.312 cm forward and 3.645 cm
  right**, with no yaw. It is not an executable navigation command or an object
  pose. The same robot-relative vector is used for the sequence-0 diagnostic,
  not as a claimed sequence-0 target estimate or the same world-space path.
- Reuse the private `joint_config`, `offset_matrix` and
  `robot_collision_vertices` helpers. Hash-check URDF, configuration and
  robot-only USD against the previous calibration/proxy audit; check the prior
  fixed-camera calibration receipt. Maximum EEF FK/proprio discrepancy across
  both boundaries: less than 0.8 micrometers and 0.7 microradians. These numerical
  consistency results do not establish pose uncertainty or moving localization.
- Use the 164 enabled authored collision meshes (9,639 vertices), not the
  upstream sphere proxies that previously failed enclosure. As in the prior
  calibrated coverage script, sample per-mesh convex-hull vertices and face
  centroids and exclude original/interior points when forming the exposed
  final surface. That exclusion never declares original interiors free.
- Call unchanged `classify_depth_support`: native-resolution depth, conservative
  3x3 neighborhoods, and the unchanged 2 cm depth-beyond margin. Separately
  evaluate all authored surface samples at translation fractions
  0, 0.25, 0.5, 0.75 and 1. These are discrete samples, not a swept-volume test.

## Results

Exposed final-surface samples for the hypothetical 10 cm segment, all cameras:

| Capture | Samples | Depth-beyond support | Valid depth, no beyond support | Outside all views |
| --- | ---: | ---: | ---: | ---: |
| Sequence 0 | 16,299 | 293 (1.80%) | 270 | 15,736 |
| Sequence 768 | 15,445 | 7,647 (49.51%) | 1,855 | 5,943 |

All in-view samples had valid depth neighborhoods. "Valid depth, no beyond
support" can mean occlusion, a nearby surface or self-geometry; it is **not** an
occupied-cell or collision label. Outside-view samples remain unknown.

Latest-view camera contribution:

| Cameras | Depth-beyond support | Valid depth, no beyond support | Outside views |
| --- | ---: | ---: | ---: |
| Head only | 7,579 | 1,923 | 5,943 |
| Both wrists only | 1,858 | 7 | 13,580 |
| All three | 7,647 | 1,855 | 5,943 |

The wrist views add **68** supported exposed samples beyond the head view.
They do not close the low-body gap:

| Capture, below 40 cm | Samples | Depth-beyond support | Valid depth, no beyond support | Outside all views |
| --- | ---: | ---: | ---: | ---: |
| Sequence 0 | 1,334 | 140 | 270 | 924 |
| Sequence 768 | 1,347 | 0 | 0 | 1,347 |

The five-position surface diagnostic gives the same qualitative result:
depth-beyond support increases from **1,903/141,290** to
**35,811/141,290**, but all **11,315** latest low-body samples are outside all
views (versus 657 supported out of 11,170 at sequence 0). Samples can repeat
across translated poses; these counts are not unique volume, area or probability.

A 5 cm forward control using the prior exposed-surface method reproduces
**151/14,007** supported samples at sequence 0, matching the earlier calibrated
hold result. At sequence 768 it gives **5,474/12,635**, but **0/1,170** low
samples supported. Robot posture and sampled surface geometry changed, so this
is a comparison of actual posture/view combinations, not a controlled estimate
of camera-view improvement alone.

## Missing Clearance Evidence

No actual known-free/occupied/unknown **grid-cell** counts are reported. The
public `OccupancyMap.integrate` contract assumes a horizontal camera at zero
base-relative XY offset. These articulated-camera transforms do not satisfy
that contract. It was not called with fabricated calibration or odometry, and
no private occupancy grid was invented. Public occupancy and coverage APIs
remain unchanged.

Full-body clearance remains missing because:

- Point depth-beyond support does not certify surrounding volumes; occluded
  and unseen low geometry remains unknown, not free.
- The authored meshes and per-mesh convex hulls do not qualify live physics
  cooking, wheel substitutions, contact offsets, carried payload or attached
  geometry. The old sphere proxies remain explicitly disqualified as full-body
  enclosures.
- The translation assumes fixed joints and yaw. Articulated motion during
  transit, braking overshoot, current settled state, uncertainty margins and
  moving localization have not been qualified.
- Surface samples at five positions do not certify continuous swept-volume
  clearance. No cell-state, collision-probability or motion-success claim follows.

The useful result is improved visibility of some upper-body exposed samples,
not sufficient evidence for this base move. All-camera coverage is still
missing precisely where low obstacles could matter.

## Reproduction

Private script: `scripts/coverage_extended_radio.py`.
Private artifacts: `runs/coverage-extended-radio-20260922/report.json` and
`validation.json`. Run from the harness checkout:

```sh
../internal/physical-ai-lab/.venv/bin/python -B \
  ../internal/physical-ai-lab/scripts/coverage_extended_radio.py
```

The report retains source/code/asset hashes, camera transforms, FK discrepancies,
all category counts and the bounded hypothetical translation. All **170** source
run files were unchanged. **36** category partitions and camera-union support
checks passed. The existing depth-coverage tests passed **14/14**; private-script
Ruff passed. No other public source files were changed by this sidecar.

Report SHA-256:
`0a0fbceed5f7230fcb3e13b86ed009a5bca34e94b748ae9b5b9271e93cd2b877`.
