# Grasp Coverage And Staging Decision

## Decision

Return the native-execution critical path to Phases 5-7: sensing, stopping and
closer staging. Retain the geometric grasp candidates; do not generate another
batch or spend time tightening self-collision sampling on an externally unseen
whole-body path. Phase 9 has viable offline proposals, not qualified execution.

## Candidate-2 Coverage

The [sampled path screen](GRASP_OBB_FEASIBILITY.md) had no hits for candidate 2.
A subsequent source-bound coverage check projects moving authored-hull vertices
at 16 fractions into the three fixed, contemporaneous depth cameras. Samples
within 20 mm of the starting robot body are marked ambiguous and excluded from
the exposed-sample counts, not declared free space. Camera poses are held at the
capture boundary; no future camera image or hypothetical new depth is invented.

Across fractions (repeated vertices, NOT unique surface/volume coverage):

| Diagnostic | Samples |
| --- | ---: |
| Exposed vertex samples | 116,020 |
| Outside every camera view | 44,033 |
| Valid depth without 20 mm beyond-sample support | 1,177 |
| Depth beyond sample | 70,810 |

At the first fraction, 755/3,114 exposed samples are outside all views. The
largest blind groups are left arm links 2/3/5 (244/238/134 samples). At the final
posture, 3,488/8,342 are outside all views, dominated by the right hand, wrist
camera and distal arm. Fixed right-arm JOINTS do not imply a fixed right arm in
the base frame: the shared torso moves it. That motion cannot be ignored.

This is only a retained-view diagnostic. Depth support is not a swept-volume
certificate, and unsampled/occluded space remains unknown. No continuous
self-separation certificate was attempted after this external-coverage blocker.

## Why Not Lock The Torso?

An independent reach upper bound used the measured torso posture from the pinned
IK receipt and the processed native URDF. The shoulder origin is the measured
parent transform times `left_arm_joint1.origin`. Summing translation lengths
from its child through joints 2-7 and the fixed `left_gripper_joint` gives an
optimistic 0.871549808 m radius for the native gripper-link origin. All seven arm
joints are revolute; the final gripper attachment is fixed. This ignores joint
limits, orientations and collisions, so it is an upper bound, not a reach claim.

| Surviving candidate | Target-to-fixed-shoulder distance | Excess over upper bound |
| --- | ---: | ---: |
| 0 | 1.225302 m | 0.353752 m |
| 1 | 1.198442 m | 0.326892 m |
| 2 | 1.225302 m | 0.353752 m |

These three target poses cannot be reached with this torso and base fixed.
This does not prove every possible grasp is unreachable. It does explain why
the current useful candidates demand large whole-body changes. A closer base
start or different torso staging is needed before treating them as local grasps.

## Evidence And Next Work

Private local backup:
`internal/physical-ai-lab/runs/grasp704-obb-coverage-20260924-r1/receipt.json`.
It records per-fraction/per-link results and hashes of the depth, geometry,
configuration, proposals and IK. Script: `grasp_endpoint_batch.py --candidate-set
obb --coverage`. Reach arithmetic uses the same IK measured state and pinned URDF;
the formulas and complete contributing joint chain are given above.

Next audit the current native stopping/localization evidence and choose a
staging strategy that changes the coverage situation. Do not repeat the old
blind wrist-observer sweep, weaken unknown-space gates, or execute from this
retained frame. All commanded motion still needs current legal observations.

Zero actions, zero paid calls, no new inference. Phase 9 stays partial. The
coverage result narrows the next action; it is not another completed phase.
