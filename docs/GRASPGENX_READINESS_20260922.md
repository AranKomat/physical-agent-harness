# GraspGenX / R1Pro Readiness Audit

Date: 2026-09-22. Scope: bounded, local, read-only sidecar inspection; this memo is the only output written. No downloads, upstream imports, model inference, native motion, simulator/API calls, code edits, commit or push. Online target acquisition and compiler replay are separate workstreams.

## Decision

**GraspGenX inference for the actual simulated R1Pro is not ready to run truthfully from the inspected configuration.** The adapter exists, but the worker template has placeholder paths/model names/gripper name, `gripper: null`, `expected_gripper_fingerprint: null`, and empty checkpoint/gripper manifests. Retained documentation explicitly records mock-only adapter validation, no loaded weights, and no qualified actual R1Pro profile. This audit did not attempt startup or survey every possible external installation.

Robot-only evidence supports named joints, authored travel limits and an EEF convention. It does not supply a complete GraspGenX gripper representation or prove a real Galaxea gripper is interchangeable with the simulated R1Pro.

## Evidence Paths

Paths below are repository-relative, without host identifiers. `H` means `physical_agent_harness_scaffold`; `L` means `internal/physical-ai-lab`; `K` means `L/runs/released_policy_audit/kinematics`. Private assets remain private: no mesh arrays, asset files or source/config excerpts are reproduced here. Numerical statements below are audit findings.

| ID | Retained evidence |
| --- | --- |
| E1 | `H/physical_harness/action_compiler/graspgenx.py`; `types.py` (`Gripper`); `geometry.py` (`compose_tcp`); `worker.py` |
| E2 | `H/configs/action_compiler/graspgenx-worker.template.json` |
| E3 | `H/docs/ACTION_COMPILER_V1.md`, section 5; `H/docs/ACTION_COMPILER_V1_VALIDATION.md`, GraspGenX checks |
| E4 | `K/behavior_r1pro.urdf`; `native_r1pro_meta.urdf`; `native_r1pro_processed.urdf`; `galaxea_r1pro.urdf` |
| E5 | `K/native_r1pro_source_cfg.yaml`, EEF and cuRobo sections |
| E6 | `K/r1pro.usda`, stage units and four finger prismatic joints |
| E7 | `K/live-controller-audit-002.json`, gripper controller records |
| E8 | `L/docs/G05_INTERFACE_AUDIT.md`, practical selection follow-up; `L/docs/RADIO_RECOVERY_AND_SKILL_AUDIT.md`, geometry diagnostic |
| E9 | `L/runs/r1pro-kinematics-20260920/processed-urdf.json`; `camera-calibration.json` |
| E10 | `H/docs/HYBRID_CALIBRATED_GEOMETRY_20260921.md`, planning-sphere enclosure diagnostic |

## Field-Level Readiness

| Field | Supported finding | Remaining prerequisite |
| --- | --- | --- |
| `joint_names` | Left: `left_gripper_finger_joint1`, `left_gripper_finger_joint2`. Right: `right_gripper_finger_joint1`, `right_gripper_finger_joint2`. E4/E5/E7 agree. | Select and identify one hand per profile; do not pass four joints as one two-finger gripper. |
| `lower_limits`, `upper_limits` | Each simulated finger is prismatic, lower 0 m, upper 0.05 m. Thus each hand has lower `(0, 0)`, upper `(0.05, 0.05)`. E4 and E6 agree; USD uses metres. | Bind these facts to the exact selected asset revision and verify the loaded representation preserves units/order. These are authored limits, not measured achieved endpoints. |
| `open_positions`, `closed_positions` | Simulated joint1 travels along +Y and joint2 along -Y in their gripper parent frame. Authored maximum separation is `(0.05, 0.05)`; minimum separation is `(0, 0)` (E4). | These are evidence-supported nominal open/closed joint configurations, not a demonstrated contact calibration. Verify pad separation, closure/contact geometry and controller mapping before declaring a qualified profile. |
| Native command mapping | Retained zero-action inspection records smooth gripper control with scalar input limits [-1, 1]. Left action index 14 maps to joints 24/25; right action index 22 maps to joints 26/27 (E7/E8). | This is not a metres-valued opening command, nor evidence of physical Galaxea scalar polarity/calibration. Do not confuse action indices with joint indices or infer achieved travel from a no-op command. |
| `max_opening_m` | Equal full travel increases separation by 0.10 m. | Exact inner contact-surface aperture is missing. The increase in separation is not itself the maximum aperture; finger origins, pad shape and collision offsets matter. Do not populate this field with 0.10 merely by doubling travel. |
| `grasp_to_tcp` | E5 defines an EEF relative to each gripper link: translation `(0, 0, -0.06)` m and quaternion `(0, 1, 0, 0)` in xyzw convention. E9 supports robot EEF/FK consistency. | This is a gripper-link-to-EEF transform, not a GraspGenX-grasp-to-TCP calibration. Define the exported asset root, learned grasp frame, approach/closing axes and chosen TCP; derive and validate `T_grasp_tcp`. Identity is not justified. |
| `family` | Opposed prismatic fingers support a parallel-jaw classification. | A family label does not identify compatible learned gripper geometry. |
| `id`, `revision`, `gripper_name` | No actual profile is selected in E2. | Assign an explicitly simulated, hand-specific identity and provenance after provisioning; do not substitute a real Galaxea product name based on appearance. |
| Mesh/URDF package | E4 references gripper/finger OBJ meshes; E6 retains robot mesh geometry. The inspected `K` directory has no corresponding loose `meshes/` directory or `x_grippers/<name>/config.json` package. | Authorized private export/provisioning must retain correct geometry, transforms, units, visual/collision distinctions and dependencies. A whole-robot USD is not a ready GraspGenX package. |
| `gripper_manifest`, `asset_digest`, fingerprint | Template manifest is empty; no calibrated profile/fingerprint exists there. | Hash every selected gripper file, bind `asset_digest = digest(gripper_manifest)`, then derive the profile fingerprint and set `expected_gripper_fingerprint`. File integrity alone does not establish origin or calibration. |
| Swept metadata | E5 contains planning spheres and collision exclusions, not a demonstrated GraspGenX closure-sweep package. E3 records upstream need for swept-volume metadata. | Produce metadata using the reviewed upstream schema/tooling for the selected geometry and full closure range. Exact upstream keys/tool invocation are not established by this bounded retained-doc audit; do not invent them. |

The adapter computes `T_frame_tcp = T_frame_grasp * T_grasp_tcp` exactly once. Upstream coordinate restoration must not be followed by adding the object centroid again. The adapter emits the profile's fixed `max_opening_m`, not a separately inferred per-grasp aperture (E1/E3).

## Provenance And Limits

The pinned adapter revision is `b9429097728cb1c430dd78b92edf17ba318aad03`. E3 retains upstream source references and the audited callable contract; this audit did not fetch or independently re-audit upstream code. A bounded search under `internal` to depth five found no path named GraspGenX or gripper_descriptions; this is not a machine-wide absence claim.

E8 identifies the retained Galaxea comparison with GalaxeaManipSim revision `abe7f5161eeaa150e6eaffdf443af5df7f23f356`. Direct XML inspection confirms its finger axes have small off-axis components, whereas the simulated assets use pure opposed Y axes. Matching names and limits do not establish identical grippers, physical feedback order, pads, TCPs or control semantics.

Local SHA-256 recomputation matched E9 for all three inputs:

| Private input | SHA-256 |
| --- | --- |
| `K/native_r1pro_processed.urdf` | `b0d76760cbedfbcbe1ddc280380dd5f497bbca380313bc096d7239a2c50dae61` |
| `K/native_r1pro_source_cfg.yaml` | `d3eb97811138d00edd83bc2be23f8d1d2e2b17c1bbea237a7cf2f9f89752524e` |
| `K/r1pro.usda` | `6029617cdd3aefce981428058a1c82cffe6af20ae61dc5be1da7334342c3bc52` |

The retained FK diagnostic reports 102 comparisons, maximum position error 2.426e-6 m and rotation error 1.041e-6 rad. Camera calibration reports maximum matrix-element error 1.342e-9. These establish the scope of earlier geometry checks, not a learned grasp-frame calibration, grasp success or motion qualification.

Gripper closure-sweep metadata and full-robot trajectory clearance are different requirements. E10 reports 4,053 of 9,639 authored collision vertices outside the union of 79 planning spheres, by up to 53.206 mm at the checked posture. Existing spheres cannot be treated as a certified conservative swept-body bound; payload and unknown scene space remain separate gates.

## Next Provisioning Prerequisites

1. Select the exact simulated hand and immutable asset version. Review code, checkpoint and robot-asset licenses separately; retain origin, authorization and conversion receipts privately.
2. Provision/export a complete gripper-only package from authorized simulator geometry. Verify mesh dependency closure, scale, joint axes/order, open/closed geometry and the upstream gripper configuration schema. Validate actual pad aperture instead of assuming a 100 mm opening.
3. Define the learned grasp frame and TCP; derive `T_grasp_tcp` with explicit direction/conventions and static landmark/FK checks for the chosen hand. Keep real Galaxea and simulated R1Pro identities separate.
4. Generate and validate the upstream-required gripper representation and closure-sweep metadata. Retain tool versions, parameters and validation receipts. Do not use full-body planning spheres as a substitute.
5. In a separately authorized provisioning phase, supply a clean checkout at the pinned GraspGenX revision, compatible runtime/GPU dependencies, and materialized generator/discriminator weights plus both YAML configs. No model provisioning is authorized by this audit.
6. Populate a private worker config. Checkpoint manifest must cover `gen/config.yaml`, `dis/config.yaml`, and the exact selected weight files. Gripper manifest is relative to `assets_dir` and must cover `x_grippers/<name>/config.json` plus every selected gripper file. Reject LFS pointers; set the profile digest and expected fingerprint from the final artifacts.
7. Only after explicit inference/license approval, validate proposal-only startup in a supervised OS-level no-egress worker with both upstream directory overrides configured before import. Offline environment variables alone are not isolation. Use frozen legal point clouds and bounded calls; record timing, empty outputs and uncalibrated scores without claiming physical success.
8. Keep native execution disabled until separate IK, collision/unknown-space, payload, controller and verification gates qualify it. Neither this memo nor successful future inference authorizes motion.

## Audit Verification

Inspected local text/config files, parsed all four retained URDFs, checked USD joint declarations and recomputed the three provenance hashes. The default Python XML parser had a local library-link failure; the system Python parser completed the read-only extraction. No dependencies were installed. No model/runtime tests were run. Only this document was created; assets and templates were left unchanged.
