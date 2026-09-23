# Closer Retained Grasp Proposals

## Question And Selection

Can a later legal sensor view provide useful new proposals after the corrected
frame-416 IK batch found no pose matches? This is an offline Phase 9A
source-selection and proposal experiment, not a new robot approach.
Starting public revision: `15194ac`.

All 13 target-bearing boundaries from `live-fusion-dense768-20260924-r5` were
inspected. Each largest-support depth component was deprojected with its own
camera intrinsics and measured joint/FK camera mounting, with source stamp,
RGB/depth and mask hash checks. No shadow local-map pose was used to position
the robot. The largest component is not guaranteed to represent a persistent
physical part or qualified object identity.

Frame 704 was selected for minimum median shoulder-to-surface distance among
these boundaries, before running new proposal inference. Its median was
1.2885 m, versus 1.7416 m at frame 416 of this trace. The earlier frame-416
grasp experiment used a different retained trace, so this is not a matched
causal test of distance alone. Visual review of the 13-frame contact sheet
confirmed a closer visible radio view, not grasp or task success.

## New Inference And IK

The source-bound frame-704 dominant component contains 2,925 points in
`source_head_optical`. The pinned GraspGen-X release and candidate R1Pro hand
recipe generated 32 proposals and retained top eight, seed 0, one attempt.
Inference took 0.858 seconds; sampled peak allocated memory was 591.7 MiB.
These are proposal-inference measurements, not full-stack latency/memory.

The corrected torso-plus-left-arm numerical IK screen found **8/8 pose
matches** for this new set. It uses the measured camera-to-base transform and
canonical-to-native-gripper transform, and solves at `left_gripper_link`.
A separate FK recomputation from the recorded full measured joint state and
each candidate's joints confirmed limits and the 5 mm / 0.02 rad thresholds.
Maximum rechecked position error was below 3e-9 m; angle error below 8e-9 rad.
These residuals measure numerical consistency, not physical accuracy.

Several solutions require large torso rotations. No self-collision, scene,
floor, balance, approach, closure, or path check has been run on this new set.
There is no implied contact support or calibrated TCP. The invalidated old
8/8 IK/path results remain invalid; this new source does not rehabilitate them.

## Artifacts And Next Gate

All directories are backed up under the parent workspace's private lab `runs/`:

| Run | Receipt SHA-256 |
| --- | --- |
| `grasp-source-views-20260924-r2` | `fbbb4fff6c73be9ef4b850f531ee2769797dfece2368c93c185c453ea16b8209` |
| `graspgenx-view704-20260924-r1` | `ea14be05b1c1d23b58fa4e4e6eda23a86e691e5628eff45e13a63dfbc6eef45f` |
| `grasp-ik-view704-20260924-r1` | `9128e25f7892fa7cd5f56b8472982b2be89d2648ef80b3d54ff8e4b62759ede9` |

Private scripts: `inspect_grasp_source_views.py`, `graspgenx_proposal_probe.py`,
`grasp_pose_ik_screen.py`. Earlier cloud pins remain the default; the new path
requires a source manifest/sequence and validates generated-proposal linkage.
All three scripts compile. No full runtime regression suite was rerun.

Next evaluate contact support and endpoint/self/observed-scene feasibility
together on this new frame, preserving the exact source and measured start.
Do not run the old path-screen entry points unchanged: they assume frame 416.
Only consider path planning for viable endpoints; do not execute these
large-posture solutions. Phase 9 remains partial. Zero new robot actions and
zero paid model calls; one local GPU proposal inference.
