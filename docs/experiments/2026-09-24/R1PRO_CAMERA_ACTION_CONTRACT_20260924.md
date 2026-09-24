# R1Pro Camera Action Contract

## Question

Can the default 2026 BEHAVIOR R1Pro legally reposition its head camera to
observe the low-body swept volume that remains missing from Phase 5 clearance?

## Protocol

- Source: audited BEHAVIOR-1K commit
  `b1979916ec1549b10a4e65e630bc6504a9af1b00`.
- Task/development instance: `turning_on_radio`, public-test instance `301`.
- Robot config: the bundled `omnigibson/eval/r1pro.yaml`, SHA-256
  `a98fa8a81472adfecfb642778d4d7a01e20131be7f70824e0ae095d665cdbb93`.
- Inspection occurred after ordinary evaluator reset/load/reset. It sent no
  actions, made no paid calls and required no motion authorization.
- The receipt records the native robot definition, registered controllers,
  action indices and configured proprioception while requiring simulator time
  to remain unchanged during the inspection itself.

Three preliminary attempts are retained privately. Each failed before sending
an action because the inspection script incorrectly assumed, in order, the
robot-config key name, a registered camera controller, and an active-camera
definition. The corrected `r4` protocol treats those absences as findings.

## Result

The corrected receipt completed and reports:

| Field | Native result |
| --- | --- |
| `robot.action_dim` | `23` |
| Controller order | base, trunk, left arm/gripper, right arm/gripper |
| `robot.is_active_camera` | `false` |
| Camera controller registered | `false` |
| Camera action indices | none |
| Camera joint names/control indices | none |
| Camera state in submitted proprioception | `false` |
| Actions sent | `0` |

The YAML contains `camera: NullJointController`, but the R1Pro robot definition
does not declare an active camera, so that group is not registered in the
runtime controller map or action space. The three challenge RGB-D sensors are
fixed onboard sensors; the head sensor is not an actuated pan/tilt unit.

Private artifact hashes:

- script:
  `3912d7e360ee33aaeba64d4f6485a56c009178b2913d43e1f3350b938d78d286`
- corrected receipt:
  `ffa16ff60ca953dc1072bda1127a85cf6e21167d7e7fae36e9dd1883321ca1b6`
- native log:
  `a502db41d91eb8a3f49580585c2fab0485d6c8f9935a1f04c777ac548302347b`

## Decision

Close the default-R1Pro head-actuation branch. Changing the YAML controller
cannot expose camera motion because the embodiment supplies no camera joints.
Adding an actuated or additional camera would be an embodiment change, not a
controller correction.

The 2026 challenge documentation permits disclosed custom OmniGibson robot
embodiments and restricts their policy input to onboard RGB, depth and
proprioception. This motivated a separate fixed-camera hypothesis while
preserving the 23-D motor interface. The subsequent
[custom-camera coverage screen](R1PRO_CUSTOM_CAMERA_COVERAGE_SCREEN_20260924.md)
found that even the union of all 228 screened fixed poses left 20 of 171 newly
occupied voxels occluded for a 5 mm segment. Under its declared stop rule, the
fixed-camera branch should not be built. The world-fixed `external_sensor0`
remains inadmissible, and strict Phases 5-9 remain blocked until a different
legal current-clearance authority is qualified.
