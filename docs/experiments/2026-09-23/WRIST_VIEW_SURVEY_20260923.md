# Wrist-Only Visibility Survey

## Question

Can modest wrist-camera reorientation resolve the low-body visibility gap before
forward staging? This is a CPU-only hypothetical-view survey, not a new robot
motion trial or external-clearance certificate.

Use the pinned robot meshes, processed URDF, camera mounts, and sequence-416
legal proprioception/intrinsics from `sam31-live-fusion-20260922-r1/stack/A`.
No simulator object geometry or global poses enter the calculation.

From the authored convex robot hulls, take vertices and triangular face centroids,
translate them 5 cm forward, retain points below 40 cm and outside the original
body hulls. This produces 1,031 samples. These are deliberately only a diagnostic
sample set, not a volume enclosure. Three nonconvex wheel colliders remain excluded.

For each wrist independently, enumerate changes of -0.5, 0, +0.5 rad on arm
joints 5, 6 and 7: 54 candidate configurations total. Other joints remain at
their measured posture. Reject out-of-limit candidates rather than clipping.
Project samples through FK-derived camera transforms and the original intrinsics,
requiring positive optical depth and a one-pixel image border.

## Results

- Current three-camera union: **0 / 1,031** samples in the image frusta.
- Union over every candidate view plus current cameras: **184 / 1,031 (17.8%)**.
- Best single additional view: left wrist +0.5 rad on each of joints 5-7,
  covering **95 / 1,031 (9.2%)** samples geometrically.

The union is an optimistic upper limit for this finite candidate set: it ignores
robot/scene occlusion, requires visiting multiple postures, and does not establish
that depth would be valid. No candidate path, self-collision, whole-body stopping,
sensor timing or external clearance is qualified. These configurations must not
be dispatched as a scan program.

## Consequence

A small wrist-only scan is not a sufficient next motion experiment for this
posture. Even granting every candidate unobstructed visibility would leave 82.2%
of the sampled low-body region outside view. Broader arm/torso sensor positioning
or causal observations gathered from other positions must be considered, with
their own approach-path and stop constraints. This does not prove that all
possible robot postures or legal sensor histories are insufficient.

Changing SAM, grasp scores or depth margins cannot fix an outside-frustum gap.
Do not weaken strict motion gates or treat unknown volume as free space to avoid
this requirement.

Private artifact: `runs/wrist-view-survey-20260923-r1/receipt.json`, retaining
all candidates, input hashes and source stamp. No GPU, robot commands or paid
calls. Frustum tests cover camera pose inversion, negative/zero optical depth
and image borders.

## Full-Arm Follow-Up

Expanded the same fixed sample set to 128 Sobol configurations per arm (scramble
seed 0), spanning the seven published arm-joint limits while holding torso,
opposite arm and fingers at measured positions. No search iteration was driven
by task success. Retain every one of the 256 candidates.

For each candidate, test camera-to-sample line segments against the 161 authored
convex robot hulls transformed by that candidate's FK. Ignore and explicitly count
hulls containing the camera origin: collision housing does not model an optical
window. Exclude three wheel spheres as before. This is approximate robot
occlusion, not scene occlusion or optical-mesh qualification.

The union of image frusta covers all 1,031 samples. After the authored-hull
occlusion check, the union covers **770 / 1,031 (74.7%)**. The largest individual
view contains 336 unblocked samples. The remaining 261 are not proved invisible
from all possible postures; this finite survey does not establish that bound.

The raw survey's legacy `scope` text still says no occlusion; its explicit
`full_arm_sobol`, `unblocked_union`, per-candidate rows and limitations identify
the actual extended test. The script label is corrected for future runs; the raw
receipt remains unchanged.

### Endpoint Self-Collision

Preselected the five largest unblocked-view counts, with stable source-order
tie breaking. Checked those five endpoints and the initial posture using FCL
and every non-excluded pair among the 161 authored convex hulls. Exclusions are
the previously audited native connected-link and explicit filters, pinned to
receipt SHA-256 `a738034692ab7c75309ad56c7a6ac1bf6da06e80008888a7b2b0241029932ba3`.

| Survey index | Arm | Unblocked samples | Intersecting pairs | Minimum checked separation |
| --- | --- | ---: | ---: | ---: |
| 33 | Left | 336 | 0 | 22.71 mm |
| 67 | Left | 299 | 0 | 22.89 mm |
| 3 | Left | 236 | 0 | 23.35 mm |
| 63 | Left | 221 | 0 | 4.35 mm |
| 241 | Right | 207 | 0 | 23.50 mm |

Initial posture also has zero intersections. These are endpoint geometric checks,
not continuous paths, scene clearance, native contact-margin qualification or
stop evidence. Candidate 63 has substantially less separation and must not be
treated as equivalently robust. No candidate was commanded.

This establishes plausible sensor endpoints worth a path study rather than
justifying a native arm scan now. Next check continuous self-separation on paths
to informative candidates; external clearance and measured stopping remain
independent gates.

Private artifacts: `runs/full-arm-view-survey-20260923-r1` and
`runs/view-posture-collisions-20260923-r1`. Four frustum/ray tests pass, including
segment bounds, parallel misses and explicit camera-origin hull exclusions.
Ruff passes. All work remained CPU-only, with zero commands and paid calls.

## Continuous Self-Separation Follow-Up

Tested straight joint-space paths from the frozen measured posture to all five
selected endpoints. This is geometry-only, without speed or controller commands.
The fixed pair margin is twice the previously measured maximum native contact
offset plus 1 mm: **11.07069 mm**. It is a diagnostic margin, not a calibrated
physical safety envelope.

For each pair, bound distance change along an interval by summing changed-joint
arc-length bounds. Each point-to-joint radius is conservatively bounded by the
sum of downstream joint-origin lengths and maximum mesh-vertex norm. Shared
ancestor rotations preserve pair distance and do not enter this sum. Held
prismatic-joint limits are included in radius bounds; changed prismatic joints
are rejected.

At interval midpoints, compute world-axis support gaps. For unresolved pairs,
FCL supplies a candidate separating direction, but **the FCL distance itself
does not certify separation**: project the actual hull vertices on that direction
to obtain a geometric lower bound. Subtract the interval motion bound and require
the result above the margin plus 1e-7 m. Otherwise bisect; a sampled intersection
fails the path, and the 512-node cap yields inconclusive rather than pass.
Fixed-relative pairs also pass support-gap checks, not just old FCL distances.

| Candidate | Result | Checked midpoints | Certified path fraction |
| --- | --- | ---: | ---: |
| 33 | Continuous authored-hull self-separation | 93 | 1.0 |
| 67 | Continuous authored-hull self-separation | 35 | 1.0 |
| 3 | Continuous authored-hull self-separation | 41 | 1.0 |
| 63 | Rejected: endpoint below diagnostic margin | 0 | None |
| 241 | Continuous authored-hull self-separation | 69 | 1.0 |

This advances the robot-only path prerequisite for sensing. It does not qualify
external scene clearance, the three excluded wheel spheres, native collision
cooking, controller tracking, observation freshness or stopping. None of these
large arm changes is authorized for execution by this report.

Private preliminary result: `runs/view-paths-20260923-r1`. The strengthened
all-pair result is `runs/view-paths-20260923-r2`, receipt SHA-256
`2bc58e6a4725bce4ed520353c3a66efee58025bd217eda390a2345acbd6e42cf`.
Script SHA-256:
`3600025d8c1d353ff3246080528d5da000648fd2587db0b87f161897bbdbd738`.
Six focused tests pass for radius conventions, support directions and ray/frustum
behavior. Ruff passes. No GPU, robot actions or paid calls.

## Retained Scene-Point Path Check

For the four self-separated paths, test 17 equally spaced fractions including
both endpoints against the original three-camera legal depth. Deproject every
fourth pixel in each axis using source-bound intrinsics and measured-joint camera
FK. Keep finite positive depths, with content hashes and camera lineage checked.
This is a sampled obstacle-rejection diagnostic, not volume clearance.

Each tested point is tagged if it lies inside the starting authored robot hulls
expanded by a 20 mm plane margin. Such points are **ambiguous near-robot evidence**,
not automatically known self pixels or free space. They may contain real nearby
surfaces. Report raw hits and outside-start hits separately rather than removing
ambiguous points from the evidence record.

Maximum raw hits among fractions are 648 for each of the three left-arm paths
and 833 for the right-arm path. All are within the expanded starting-robot
region; outside-start hits are zero on all four paths. These results find no
clearly separate sampled obstacle, but cannot qualify any path: sparse pixels,
unseen/occluded volume, geometry uncertainty and unsampled fractions remain.
No path is promoted by a zero-hit count.

Of the four candidates, #67 has the smallest maximum joint change (1.504 rad)
and 299 potentially visible samples. The others require maximum changes of
2.007, 4.054 and 4.001 rad. These are substantial scan movements, not equivalent
to the earlier 0.01 rad wrist probe. A native scan would require fresh-source
posture/path checks, a bounded controller/abort protocol and explicitly labeled
exploratory treatment of unresolved clearance. The retained source is not live
execution authority, and its camera timing is not qualified.

Private result: `runs/view-path-scene-points-20260923-r1/receipt.json`. No GPU,
commands, model calls or live instance changes. This check narrows known obstacle
evidence but does not resolve strict Phase 5-7 execution gates.
