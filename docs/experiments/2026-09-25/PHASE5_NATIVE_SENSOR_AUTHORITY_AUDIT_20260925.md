# Phase 5 Native Sensor-Authority Audit

## Decision

Close the search for an unused legal clearance sensor on the default 2026
BEHAVIOR R1Pro embodiment. The pinned challenge configuration and asset expose
three fixed onboard vision sensors and selected proprioception. They expose no
LiDAR/range sensor, contact/touch/force sensor, active camera joint, or external
sensor to the challenge policy.

This is a source and runtime-contract result, not a claim that collision-free
motion is impossible. It establishes that strict whole-body clearance cannot be
recovered by enabling a dormant default-R1Pro sensor. Strict Phases 5--9 remain
blocked until either:

1. a different challenge-legal current-clearance method is qualified from the
   existing RGB-D and proprioception; or
2. a disclosed custom embodiment supplies useful onboard RGB-D coverage while
   retaining the challenge observation restrictions.

The prior 228-pose fixed-camera screen did not establish such an embodiment.
Do not resume nearby wrist-pose, head-actuation, fixed-mount or hidden-contact
searches without a materially different hypothesis.

## Audited Sources

The audit used the clean BEHAVIOR-1K checkout at
`b1979916ec1549b10a4e65e630bc6504a9af1b00`.

| Source | SHA-256 | Relevant finding |
| --- | --- | --- |
| `OmniGibson/omnigibson/eval/r1pro.yaml` | `a98fa8a81472adfecfb642778d4d7a01e20131be7f70824e0ae095d665cdbb93` | Requests only `proprio` and `rgb`; names head, left-wrist and right-wrist cameras; declares the 61-D proprioception fields. |
| `models/r1pro/r1pro.yaml` | `63f841cffd5c499102416a797a22fa5b4cbaf146539df7dde8a4a1053e2326f1` | Declares no active-camera group and no range/contact sensor definition. |
| `source/r1pro/r1pro_source_cfg.yaml` | `8b0a672e335b6ad6881d0886a46a6c36745845012e284e8bf9dd65c0f772ddd9` | Declares exactly three camera links and `lidar_links: []`. |
| `eval/wrappers/rgbd_full_res_wrapper.py` | `85ed8b529c0e6acc7839d0d9a7ac3d3bee0a58a3e13b84d237675c8b4ed9e6ff` | Changes each existing vision sensor to `rgb` and `depth_linear`; it does not create another sensor. |
| `eval/evaluator.py` | `8279b296d619509424219a172fb6361a6abea7c1469e1c4b42448bf457f0f9b0` | Flattens robot observations and appends relative poses for configured cameras; task observations are disabled by the environment configuration. |
| `robots/robot.py` | `998826feedcf8c28208681a809cbf4500d3da0cbf1f6d07a7384627e09726271` | Imports only sensors whose asset prim and requested modality intersect; proprioception contains only the configured selected fields. |
| `docs/challenge/evaluation.md` | `d8eeab47f02b668e5e8a3bf43705f8c513d9b348d86e0e0acda3352ef49feab1` | Restricts submitted policy observations to onboard RGB, depth and proprioception. |

The robot-asset files are supplied by the pinned local
`omnigibson-robot-assets` package. Their hashes are recorded because they are
not part of the BEHAVIOR Git commit itself.

## Default Observation Surface

The default evaluator config names:

- `robot_r1:zed_link:Camera:0` as head;
- `robot_r1:left_realsense_link:Camera:0` as left wrist;
- `robot_r1:right_realsense_link:Camera:0` as right wrist.

`RGBDFullResWrapper` enables only `rgb` and `depth_linear` on those existing
vision sensors. The evaluator also publishes their relative poses and the exact
selected proprioceptive vector. The config does not request `scan` or
`occupancy_grid`, and the R1Pro source asset provides no LiDAR link from which a
`ScanSensor` could be instantiated.

The selected proprioception consists of base velocity; bilateral arm positions
and velocities; bilateral EEF positions and quaternions; bilateral gripper
positions and velocities; and trunk positions and velocities. It contains no
contact, force, touch, collision, camera-joint or range field. The earlier native
runtime receipt measured this as 61 dimensions with a 23-D action interface.

The prior zero-action camera contract inspection independently found:

- `robot.is_active_camera=false`;
- no registered camera controller;
- no camera action indices or camera joint/control indices;
- no camera state in submitted proprioception.

This closes the possibility that the `camera: NullJointController` text in the
evaluation YAML corresponds to a dormant movable camera. The robot definition
has no active camera group, so the controller is not registered.

## Why Simulator Internals Do Not Change The Decision

OmniGibson includes a generic `ScanSensor` class and gathers rigid-contact data
inside the simulator physics step. Those facilities are not controller
observations in this challenge configuration:

- the default R1Pro has no LiDAR link and requests no scan modality;
- contact gathering feeds simulator physics/object-state machinery, not the
  selected robot observation dictionary;
- collision queries, object contact state and task state are privileged simulator
  data and cannot be converted into a control authority under the current rules.

Likewise, `omnigibson/configs/r1pro_behavior.yaml` is a general demonstration
configuration containing a world-fixed `external_sensor0`, but it sets
`use_external_obs: false` and is not the challenge evaluator config. Even if
enabled, a world-fixed external camera would violate the onboard-observation rule.

## Custom Embodiment Scope

The 2026 rules allow a disclosed custom OmniGibson robot configuration, but the
policy must still receive only onboard RGB, depth and proprioception. Therefore:

- adding an onboard RGB-D camera is potentially rule-compatible but is a custom
  embodiment experiment, not a default-R1Pro fix;
- exposing LiDAR scan, contact state, collision state or an external/world-fixed
  camera would not fit the documented challenge observation contract;
- a custom camera must demonstrate actual useful occlusion-aware coverage before
  implementation and must be disclosed in the submission.

The existing fixed custom-camera screen tested 228 candidate poses. Even the
union of all poses missed 20 of 171 newly occupied voxels for a 5 mm segment.
That finite result does not prove all possible custom embodiments impossible,
but it triggers its declared stop rule and does not justify building that design.

## Consequence For The Experiment Sequence

Phase 5 is now complete on the narrow question of whether an unused default
sensor can resolve clearance: **no such channel exists in the audited contract**.
Phase 5 as a whole remains partial because strict clearance is still unqualified.

The sequence must now fork explicitly:

- **Strict track:** stop at the clearance gate until a materially different,
  challenge-legal current RGB-D/proprioceptive method or custom embodiment is
  proposed and screened.
- **Exploratory benchmark track:** permit bounded actions using only legal inputs,
  record `clearance=unknown` and `motion_qualified=false`, and quarantine hidden
  collision/task truth for retrospective scoring only.

No actions, policy calls, model calls or paid requests were made for this audit.
The GPU remained unused, and the remote source checkout was not modified.

