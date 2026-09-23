# Measured Single-Arm cuRobo FK

## Protocol

Robot-only check under the existing isolated cuRobo preparation approval. No
simulator, planner, collision query, policy, API call or commanded motion.
Use the pinned cuRobo V2 revision and processed R1Pro URDF from the earlier
[FK check](CUROBO_R1PRO_FK_20260923.md), and legal proprioception from the
fresh [stationary capture](STATIONARY_SAM_JOIN_20260923.md).

Prepare two independent models, left-only and right-only. Each has seven active
arm joints and fifteen numeric holds: torso, opposite arm and four finger joints.
Reject out-of-limit measured values rather than clipping them. For each model,
test the measured posture and +/-0.01 rad perturbations of each active joint
(perturbations bounded by URDF limits). Thirty configurations total. Compare all
29 retained upper-body link poses against independently evaluated yourdfpy URDF
FK, including the opposite arm and fingers, not merely the active tool endpoint.

Wheel/steering links are excluded because their state is not measured by the
current proprio mapping. No collision spheres are loaded. This exclusion cannot
be used as a full-robot collision or clearance model.

Frozen input preparation SHA-256:
`487374a8f701d11eabad4a170c14b9c29cbb8f341c5c2650d74ef364ee803a61`.
Declared agreement bounds: **0.0001 m and 0.001 rad**. Models are constructed
with numeric `lock_joints`; no legacy null holds or live mutation assumption.

## Results

| Active arm | Configurations | Link comparisons | Max position error | Max rotation error |
| --- | ---: | ---: | ---: | ---: |
| Left | 15 | 435 | 1.355e-6 m | 4.072e-7 rad |
| Right | 15 | 435 | 6.484e-7 m | 2.393e-7 rad |

All 870 comparisons pass. GPU active-joint names exactly match the intended seven
joints in each model. Measured holds, source/URDF/input hashes and GPU environment
fingerprints remain unchanged. Exit code zero; independent NVML query finds no
remaining compute workers. Artifacts copied locally with empty checksum rsync
comparison. Preparation tests pass (four cases); full private suite before the
GPU run: 886 passed, one existing skip; changed scripts pass Ruff.

Private artifacts:
- `runs/curobo-single-arm-inputs-20260923-r1/preparation.json`
- `runs/curobo-single-arm-fk-20260923-r1/receipt.json`

## Interpretation

Numeric measured holds reproduce upper-body FK for this retained posture and
bounded perturbations. This removes one configuration uncertainty for Phase 7.
It does not establish collision enclosure, dynamic held-posture refresh, swept
path validity, native endpoint accuracy during movement, stopping, full-robot
kinematics or task success. The measured posture is historical, not live action
authority. Collision/world preparation and execution qualification remain open.
