# Development Grasp-And-Lift Gate

**Date:** 2026-09-25

**Scope:** explicitly non-benchmark, exploratory R1Pro contact/lift fixture using
normal robot commands after scripted initialization

## Result

The first semantically useful physical-effect gate passed. One soda can from
`picking_up_trash` was scripted into the open left gripper at a retained
robot-only IK configuration. After the initial legal observation, the fixture
sent only ordinary 23-DoF R1Pro action commands: eight close actions, four
closed holds, ten interpolated lift actions, and eight lifted holds.

All 30 actions completed. The run retained three legal RGB-D/proprioception
boundaries: `pre_close`, `post_close`, and `post_lift`. It made no model or paid
API calls.

Evaluator-only scoring, unavailable to control, measured:

- 50.015 mm object-height increase from post-close to post-lift;
- 17.945 mm final object-to-grasp-center distance;
- 0.003 mm change in that relative distance during the lift.

An independent fixture-specific verifier then used only retained legal left-wrist
RGB-D, legal proprioception, and robot-only forward kinematics. The same orange
surface remained fixed in the wrist view while the grasp center moved upward:

- grasp-center vertical displacement: 50.010 mm;
- lateral grasp-center displacement: 0.281 mm;
- post-close/post-lift mask IoU: 0.9967;
- mask centroid displacement: 0.452 pixels;
- mask area ratio: 1.000288;
- median surface-depth change: 0.014 mm.

The legal-evidence verifier passed. This is sufficient to unlock exploratory
Phases 10-12; it does not unblock strict clearance or establish benchmark task
success.

## Boundaries

- The initial robot and can poses were scripted and disclosed.
- Exact object poses were written only to an evaluator sidecar and were never
  read by the controller.
- No object pose, simulator segmentation, collision state, task truth, reward,
  or future frame authorized an action.
- External clearance remained `unknown` and `motion_qualified=false`.
- The color verifier is fixture-specific evidence of retention, not a general
  object detector.
- The result does not qualify navigation, release, placement, collision-free
  manipulation, or physical-hardware operation.

## Private Artifacts

- run receipt: `runs/development-grasp-lift-20260925-r1/receipt.json`, SHA-256
  `275e0b2b3db2f7be4ff73f6a02ea9fe85865272e4571d01bb645a8d19baf28a9`;
- evaluator sidecar: `runs/development-grasp-lift-20260925-r1/evaluator-sidecar.json`,
  SHA-256
  `543ab7e84658df2c5a1005045c319456d1995790d2658babf74ad0dd72f13b5b`;
- legal verifier: `runs/development-grasp-lift-20260925-r1/legal-visual-verification.json`,
  SHA-256
  `b9682781087a864f2798fa92c93a3b0324c9f686f0658083b443c3e5e9714af3`;
- runner: `scripts/run_development_grasp_lift.py`, SHA-256
  `e1e3ade709421b15aee9bf09b8979ba385b398ea529ee05b1cc792a4e2acb17e`;
- verifier: `scripts/verify_development_grasp_lift.py`, SHA-256
  `eebbc605bb5fdd1210916c25736f55e5204c2e90ef5b2f190112fd3aab3cff86`.

## Next Experiment

Run a matched exploratory comparison on this executable fixture:

1. fixed routing/control;
2. compact-V3 recurrent GPT executive with the same initial state, action menu,
   action budget, verifier boundary, and evidence rules.

Do not claim a GPT benefit unless the treatment changes an independently verified
physical outcome. After that comparison, inject one predefined recoverable failure
and then run the M0/M1/routed-M2 execution comparison.
