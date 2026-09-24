# Phase 9A Gripper Readiness Decision

## Decision

The simulated R1Pro left hand is ready for hash-pinned, proposal-only
GraspGen-X experiments. It is not qualified for native grasp execution. Stop
proposal generation and gripper-only diagnostics here; the next execution gate
is legal current whole-body clearance and closer staging in Phases 5--7.

This decision separates three interfaces that had previously been conflated:

1. The released `sweep_volume_v2` checkpoint consumes the open and half-open
   sweep-volume annotation. It does not require the point-cloud, TSDF, VAE or
   mesh cache fields used by other GraspGen-X backbones.
2. The harness production `Gripper` profile additionally owns native joint
   positions, maximum opening, asset identity and `T_grasp_tcp`. Those fields
   are required for execution even when proposal inference does not consume
   them.
3. Contact, attachment and safe motion require independent native evidence.
   Neither a model score nor successful empty-hand aperture tracking supplies
   that evidence.

## Proposal-Only Readiness

The pinned GraspGen-X checkout was clean at
`b9429097728cb1c430dd78b92edf17ba318aad03`. The active probe verified the
released checkpoint hashes and both configured backbones as
`sweep_volume_v2`, then constructed `XGripperInfo` with the source's
`make_sweep_volume_gripper_info` helper. The model received the candidate
annotation directly:

- open inner box: 96 x 10 x 20 mm;
- half-open inner box: 46 x 10 x 20 mm;
- candidate fingertip depth: 60 mm;
- candidate config SHA-256:
  `5d07fb782bb14f250e3b06cc2140019779d634cf72405158999815c2d88fa299`.

This path already generated 32 proposals and retained eight from frame 704 in
0.858 seconds, with 591.7 MiB peak allocated GPU memory. The reference geometric
branch generated 272 candidates; 176 contained retained target support and all
eight highest-scored candidates did. Numerical IK, endpoint, dense-target,
closure and sampled-path rejection screens leave candidate 0 as the sole
retained offline survivor. No new proposal run was needed for this audit.

The exact simulated hand export remains the geometry reference: 36 meshes,
32 independent authored convex colliders, native 0--50 mm finger-joint limits,
and a loadable URDF. The open and half-open annotation boxes intersect none of
the corresponding authored colliders in 64 linear-program checks. These facts
qualify frozen proposal conditioning, not physical contact.

## Native Empty-Hand Aperture Probe

A bounded simulator-only diagnostic used ordinary radio instance 301. It held
all other controller channels, closed the left gripper in ten commands, held,
reopened in ten commands and held again. External clearance remained explicitly
unknown. There were no model or paid API calls.

| Measurement | Result |
| --- | ---: |
| Completed actions | 35 / 35 |
| Initial mean finger position | 0.049999014 m |
| Final closed mean position | 0.000000188 m |
| Reopened mean position | 0.049999006 m |
| Maximum finger asymmetry | 0.000001315 m |
| Maximum held-channel drift | 0.000011761 |

All three five-action hold windows met the declared one-millimeter position and
position-derived stop checks. The simulator environment and script hashes were
unchanged across the run.

The first launch is retained as a setup failure: a policy callback keyword
mismatch stopped it at one attempted and zero completed actions. No motion was
applied. The corrected `r2` run is the result above.

Private evidence:

- `runs/native-gripper-aperture-20260925-r1/receipt.json`, SHA-256
  `676ad93accffbdc274c5c50f595ed1bfaae11e07fe0eee9a5560ea9c90c0bb69`;
- `runs/native-gripper-aperture-20260925-r2/receipt.json`, SHA-256
  `b0c440c4c4f98353530aae51c3aeb297b56444b7b55965a8f614f7fb4254acdc`;
- `scripts/probe_gripper_aperture.py`, SHA-256
  `07f5c76ad00a62cd5a26aae410c9f37a28246f26583b44ab50a578ab78a73bd6`.

## What Remains Unqualified

The candidate canonical-to-native transform is algebraically consistent with
the authored hand and native TCP definition, but it is not an independent
learned-frame or contact calibration. Empty-hand tracking does not establish
pad contact, forces, friction, attachment, payload stability or release.
Accordingly, no production `Gripper` profile is promoted by this result.

More importantly, gripper calibration cannot make the retained candidate
executable. Candidate 0 is about 1.225 m from the fixed shoulder, exceeding the
optimistic held-torso arm bound by about 0.354 m. Its solution requires large
torso or base staging. The retained coverage audit found 44,033 of 116,020
exposed moving-geometry samples outside every contemporaneous camera view.
Separately, the fixed-camera Phase 5 screen left 20 of 171 voxels unseen even
for a 5 mm segment.

Therefore:

- do not generate another GraspGen-X batch;
- do not populate a production execution profile from the candidate annotation;
- do not run a contact probe from the retained frame;
- resume only after a different legal current-clearance authority admits closer
  staging and an independently checked free-space path.

Phase 9A is complete for proposal-only research and partial for execution
readiness. Phases 9B--9D remain blocked by Phases 5--7, not by proposal scarcity.
