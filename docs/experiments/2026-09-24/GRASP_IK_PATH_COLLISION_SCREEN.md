# Grasp IK Path Collision Screen

**INVALIDATED AS GRASP EVIDENCE 2026-09-24:** these paths came from the
frame-invalid IK r1. Their sampled collision counts describe those joint
paths, not paths to the intended grasps. See `GRASP_FRAME_CORRECTION.md`.

This Phase 9A follow-up checked the measured-to-goal joint-space paths for all
eight numerical torso-plus-arm IK solutions. Each path was sampled at 65
postures and tested against 11,003 reviewed authored convex-hull mesh pairs,
for 715,195 pair checks per candidate.

## Result

All eight sampled paths had zero authored-hull self-intersections. Minimum FCL
separation across the paths was 22.65--22.95 mm. No robot actions or paid calls
occurred; motion remains unauthorized.

Receipt: `internal/physical-ai-lab/runs/grasp-ik-path-collision-20260924-r1-receipt.json`  
Receipt SHA-256: `a044a55c01cb279f73d3ad7088afc2cd97545382e355f7425756a6c0e6c7a828`

## Scope And Remaining Gate

This is stronger than endpoint-only screening, but it is still a sampled
authored-hull result. It excludes native cooked geometry, wheel/floor and
external scene clearance, object/contact geometry, pose uncertainty, and a
continuous swept-volume proof. The pinned grasp/TCP and camera timing
assumptions also remain unqualified.

The eight candidates may proceed to a carefully bounded feasibility review, not
to execution. The next Phase 9 gate is current close-range reacquisition plus
native/cooked whole-body clearance and contact/TCP validation. A pose match and
clean self-path do not authorize approach or grasp.
