# Grasp IK Native-Cooked Path Screen

**INVALIDATED AS GRASP EVIDENCE 2026-09-24:** the source IK r1 omitted the
camera-to-base transform and mixed TCP/gripper frames. Neither native-path
attempt qualifies paths to the actual grasp proposals. See
`GRASP_FRAME_CORRECTION.md`. Historical counts below remain recorded only.

The corrected Phase 9A follow-up replayed all eight measured-to-IK paths using
the retained native convex callback representations. It tested 65 postures per
candidate against 11,003 pairs after applying both the 14 explicit filters and
the 42 connected-joint exclusions from the native collision receipt.

## Result

All eight paths had zero sampled intersections. Minimum FCL separation was
22.65--23.52 mm. The run used no robot actions or paid calls and kept
`motion_authorized=false`.

Receipt: `internal/physical-ai-lab/runs/grasp-ik-native-path-20260924-r2-receipt.json`  
Receipt SHA-256: `98b3aab2f2c6551ac3d45163c5a5fa7b856812776c984da47d65756150f3d623`

## Superseded Attempt

An initial run used only the 14 explicit filters and reported thousands of
collisions between connected links. That was an exclusion-inventory bug in the
new screen, not a robot result. It is retained as `r1` for auditability and is
not used as evidence. The corrected `r2` uses the same exclusion logic as the
existing native path audits.

## Remaining Limits

Native convex callbacks are not the full cooked scene; wheel spheres and
external scene/floor geometry are omitted. 65 samples are not a continuous
swept-path certificate, and TCP/contact calibration, pose uncertainty,
close-range reacquisition, and object clearance remain unqualified. This
result supports further offline feasibility work only, not execution.
