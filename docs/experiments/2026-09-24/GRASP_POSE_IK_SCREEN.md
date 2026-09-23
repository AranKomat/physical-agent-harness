# GraspGen-X Pose IK Screen

This Phase 9A follow-up evaluates the eight retained GraspGen-X poses with a
bounded numerical torso-plus-left-arm IK search. It uses the retained measured
R1Pro posture, URDF joint limits, and the pinned candidate grasp-to-TCP
transform. It does not call the planner or command the robot.

## Result

All `8/8` proposals reached the requested position and orientation in the
numerical screen. Position residuals were below `4e-10 m`; orientation
residuals were below `5e-9 rad`. The solutions stayed within the supplied URDF
limits and required 34--57 solver evaluations each.

Receipt: `internal/physical-ai-lab/runs/grasp-pose-ik-20260924-r1-receipt.json`  
Receipt SHA-256: `a9ee24400dad1201b288d7da61e07cf61b96b3a026f88e5a932fa40cd7c85fee`

This supersedes the interpretation that six proposals are necessarily
unreachable. The earlier fixed-torso reach screen was a useful conservative
filter, but allowing torso motion changes the kinematic result substantially.

## Limits And Next Gate

This is numerical local IK, not a global proof. It does not check self or
external collision, swept paths, balance, native TCP calibration, camera timing,
grasp-frame correctness beyond the pinned transform, or observed scene
clearance. A pose match therefore does not authorize staging, approach, contact,
or grasp execution.

The next meaningful Phase 9A gate is to run collision-aware IK/path validation
for these solutions with the reviewed full-body geometry. Only candidates that
survive that check and close-range target reacquisition should proceed to a
positive free-space compiled-action test.
