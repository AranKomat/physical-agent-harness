# Staged Endpoint Torso Screen

This is a retained-data, no-motion screen after
`sam-live-staging-20260924-r1`. It asks whether changing only the four torso
joint values can close the final endpoint gap to the visible SAM surface. It is
not an IK, collision, balance, or execution result.

## Input And Lineage

- Source: `SAM_LONG_STAGING_RECEIPT.json` and the final fresh capture in
  `sam-live-staging-20260924-r1/stack/A/hybrid_short.json`.
- Source receipt SHA-256: `aff718fe3398df136d3079b31755d6df33cbfd135912f0c2c20c02240725dc25`.
- Target surface median in the final base frame: `(0.79938, -0.24945, 0.59187)` m.
- Processed R1Pro URDF: the same pinned asset used by the staging reach screen.
- Actions: 0. Paid calls: 0. Motion authorization: false.

## Result

The optimizer searched the URDF-bounded four-torso-joint space for each
shoulder independently, while leaving the arm joints fixed conceptually. The
arm radius is the same optimistic translation-length upper bound used by the
bilateral reach screen.

| Side | Initial shoulder distance | Best sampled distance | Radius | Residual |
|---|---:|---:|---:|---:|
| Left | 0.99570 m | 0.07932 m | 0.87155 m | -0.79223 m |
| Right | 0.90613 m | 0.07871 m | 0.87104 m | -0.79233 m |

Both numerical searches converged. The selected torso configurations involve
large changes from the measured posture, so this result should be read as
"torso motion may remove the distance gap," not "the torso can safely move
there." In particular, the screen does not test arm joint limits in a coupled
IK solve, tool orientation, self or scene collision, balance, actuator limits,
camera coverage, stopping, or return-path clearance.

## Decision

Do not extend the base blindly and do not execute these torso configurations.
The next Phase 7 gate is a fresh legal endpoint observation followed by a
coupled torso-plus-arm IK/planner solve against a declared free-space pose, with
the complete current collision world and a return trajectory. A successful
numerical screen would still be only a planner proposal until native stop and
clearance gates pass.
