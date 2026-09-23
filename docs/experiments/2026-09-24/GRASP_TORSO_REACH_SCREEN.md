# GraspGen-X Torso Reach Screen

This is a no-motion Phase 9A follow-up on the eight retained GraspGen-X
proposals. It optimizes the four torso joint values for each proposal against
the distance from the torso-adjusted shoulder to the proposal translation,
then compares that distance with the previously measured 0.87155 m arm-chain
reach radius.

## Result

Only 1/8 proposals falls inside the conservative reach-radius screen when all
four torso joints are allowed to vary: candidate 2, residual -23.7 mm.
Candidate 6 has a positive 12.8 mm excess, not a negative margin. The other
seven remain outside in this numerical search by 12.8--225.1 mm. The screen therefore
does not support treating torso staging as a general solution for the retained
proposal set.

Correction: the original report and user-facing summary incorrectly counted
candidate 6 as inside. The receipt itself was unchanged and has the correct sign.

Receipt: `internal/physical-ai-lab/runs/grasp-torso-reach-20260924-r1-receipt.json`  
Receipt SHA-256: `4e5bb338882873238882aa2e8c266379e61b3e6a66b3f64fa2ceef5b54b1ca89`

## Limits

This is an optimistic numerical position screen, not IK. It does not check
gripper orientation, joint limits on the arm, self/external collision,
balance, swept paths, TCP calibration, camera timing, or contact geometry.
The optimizer's minima are not certified global bounds. No actions or paid
calls occurred, and `motion_authorized` remains false.

## Decision

Keep the retained proposals as shadow candidates only. The next Phase 9 step
should reacquire the object at a close legal view and run full arm/gripper IK,
collision, TCP and contact checks. Do not attempt native grasp execution based
on this reach screen.
