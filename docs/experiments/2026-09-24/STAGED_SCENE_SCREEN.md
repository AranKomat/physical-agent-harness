# Staged Candidate Scene Screen

Follow-up to `STAGED_NONCONTACT_SCREEN.md`. Neither candidate is authorized
for motion and Phase 7 remains incomplete.

## Method

The fixed left/right torso-plus-arm candidates were screened at 21 interpolated
postures using the final staged observation (sequence 1092). Head and both wrist
depth images were bound to the same observation/calibration boundary and their
content hashes verified. Camera transforms use measured joints and pinned
authored mounts. No future view or simulator object state was used.

Two separate diagnostics were evaluated:

1. Depth samples at pixel stride 4 inside moving authored hulls. Points within
   2 cm of the start body remain ambiguous, not classified as known self points.
2. Newly exposed hull vertices projected into the retained depth images, using
   the existing conservative 3x3-neighborhood depth-support classifier.

## Results

Neither candidate contained any sampled depth points outside the start-body
ambiguity region across the 21 postures. This does not establish free space.

Endpoint vertex coverage:

| Candidate | Exposed samples | Outside every view | Valid depth without beyond support | Depth beyond sample |
|---|---:|---:|---:|---:|
| Left torso + arm | 6,615 | 2,466 | 1,154 | 2,995 |
| Right torso + arm | 7,317 | 2,719 | 1,564 | 3,034 |

All in-view samples had valid depth. The endpoint raw point-in-hull counts
were 31 and 79 respectively, all inside the start-body ambiguity region.
Those points are unresolved evidence, not collisions proven or dismissed.

## Decision

Do not execute these paths under strict gates. About 37% of exposed vertex
samples are outside all views, and only 41-45% have depth beyond them. Even
complete vertex support would not certify surface or swept-volume coverage.

The useful next step is coverage acquisition or an explicitly exploratory
protocol with its limitations intact, not more no-op planner tests. Continuous
self-collision checks remain required, but cannot resolve this external
visibility gap. A no-intersection result on sampled depth must not be promoted
to collision clearance.

No actions, paid calls, GPU work, or remote workload changes were made.

## Evidence

Private script: `scripts/staged_scene_screen.py`

Private receipt: `runs/staged-scene-20260924-r1/receipt.json`

- Receipt SHA-256: `232ce8ec9e7a3e0a8bf062ca78d753ff48d69bf967021eb45e66a9fce9953984`
- Script SHA-256: `9616a290de40dd68bf64a1e87a4b82b891d07388d0fa0f52dc8852cade23e037`

The receipt includes per-posture counts, observation stamp and input hashes.
It deliberately sets `motion_authorized=false`. Geometry comprises 161 authored
hulls, not a complete native-cooked robot/scene model; wheels are omitted.
