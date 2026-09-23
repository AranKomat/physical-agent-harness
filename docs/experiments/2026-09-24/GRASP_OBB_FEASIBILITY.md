# Geometric Grasp Endpoint And Path Rejection Screens

## Outcome

Subsequent [dense-target closure audit](GRASP_CLOSURE_SUPPORT.md) rejects
candidate 1 at its open endpoint. Only 0 and 2 remain endpoint candidates.
The following table is the original coarse-depth result, not the latest admission.

Three of the eight highest-scored reference geometric candidates survive the
bounded offline endpoint and sampled joint-path rejection checks. This advances
candidate feasibility, not Phase 9 completion or motion authorization.

Inputs are the unchanged frame-704 source, candidate hand annotation, measured
start, and [reference geometric proposals](GRASP_REFERENCE_BRANCH.md). The new
batch selector pins both generation and IK receipt hashes independently of the
previous diffusion set. Every endpoint's FK and joint limits are recomputed.

| Candidate | Self-collision records | Sampled scene points inside endpoint robot | Target points in inner box | Interpolated path result |
| --- | ---: | ---: | ---: | --- |
| 0 | 0 | 0 | 33 | No hits at 17 postures |
| 1 | 0 | 0 | 30 | No hits at 17 postures |
| 2 | 0 | 0 | 33 | No hits at 17 postures |
| 3 | 0 | 0 | 30 | Rejected: two observed points at fraction 0.75 |
| 4 | 0 | 2 | 29 | Not screened; endpoint rejected |
| 5 | 0 | 1 | 33 | Not screened; endpoint rejected |
| 6 | 0 | 4 | 31 | Not screened; endpoint rejected |
| 7 | 0 | 4 | 31 | Not screened; endpoint rejected |

The four endpoint overlaps occur at finger geometry. No contact exception was
introduced. Candidate 2 has the smallest maximum joint excursion among the three
survivors (2.117 rad, versus 2.671 and 2.985 rad), still a substantial posture
change. It is a reasonable next offline candidate, not a commanded movement.

## Scope

The screen uses 161 authored convex shapes, 11,003 eligible shape pairs, native
explicit and connected-joint exclusions, and 61,200 sampled depth points from
three contemporaneous cameras. Endpoint scene checking excludes no target points.
Path screening ignores scene points within 20 mm of the starting robot hulls as
ambiguous robot returns; those points are NOT certified free space.

Each eligible path is straight interpolation in joint coordinates at fractions
0, 1/16, ..., 1. Screening stops at the first sampled self-collision or observed
intrusion outside the ambiguous start region. This is not a trajectory planner,
continuous swept-volume certificate, time parameterization, or contact model.
No wheel, floor, balance, unseen-space, localization, or stopping qualification
is supplied. No-hit samples cannot establish physical safety or grasp success.

## Reproducibility

Private local backups under `internal/physical-ai-lab/runs/`:

- `grasp704-obb-endpoints-20260924-r4/receipt.json`: all eight endpoints.
- `grasp704-obb-paths-20260924-r1/receipt.json`: repeated endpoints plus four paths.

Private script: `grasp_endpoint_batch.py --candidate-set obb --path-screen`.
IK receipt SHA-256: `0183c86083f1a6d7c3e1b5527f1f4b13122772e8211f9f0271558445f0336901`.
Generation receipt SHA-256: `6de194bc9b69a53fa2d1025198a48abfe5ed58d875c509085e85c44e0678f17d`.
Receipts record geometry/depth/script hashes, every endpoint, and checked path samples.

Endpoint launch r1 failed at missing Pydantic, r2 at missing public-repo Python
path, r3 at an unnecessary helper import for SHA-256. All stopped before screening.
The isolated grasp environment now uses the lab's Pydantic 2.13.5 (plus its
dependencies); the command supplies private/public module paths and the script
uses hashlib directly. No system packages or unrelated workload were changed.
The successful path run used approximately two CPU cores and no GPU inference.

Zero robot actions and zero paid calls. No full regression suite was rerun.

## Next

Use candidate 2 for a combined continuous self-separation and sensor-coverage
assessment, retaining candidates 0 and 1 as alternatives. Do not generate more
grasps unless these checks identify a reason. A native approach still requires
current legal observations, qualified execution/stop behavior and external
clearance; this retained trace cannot itself authorize current motion.
