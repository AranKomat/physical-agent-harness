# Post-Policy Stop Analysis

## Decision

The retained evidence supports a large discrepancy between sampled joint velocities and observation-to-observation joint-position changes. It does **not** support interpreting those velocity samples as sustained joint drift. Head-depth registration also shows little continuing base change after sequence 414, but an approximately 0.495-degree reference-relative yaw offset is already present by then. This is offline diagnostic evidence, not proof of zero motion or a qualified live stop. Stage 4's failed stop remains failed; no thresholds or admission gates changed.

## Scope And Method

Analyzed only retained legal observations in `internal/physical-ai-lab/runs/hybrid-assisted-yaw-20260921-r1/A/hybrid_short.json` and its content-addressed head-depth evidence. The trace records 384 policy actions followed by 60 initial-settling and 60 emergency-hold actions, all with zero base commands. No assisted yaw was reached. All 120 samples report `stopped: false`.

The new private script is `internal/physical-ai-lab/scripts/diagnose_post_policy_stop.py`; its output is `internal/physical-ai-lab/runs/post-policy-stop-analysis-20260922/analysis.json`. It completed in **7.97 seconds**, with a 170-second process alarm and two-thread numerical-library limits. No native motion, API/model calls, dependency installation, or quarantined-truth data/helper imports occurred. The prior registration script was inspected only for its frame convention, not imported or executed.

The script calls the existing `experiments.behavior.head_depth_shadow.point_to_plane` unchanged: stride-two depth, 10 m truncation, 1 cm voxelization, 4 cm normal radius, 5 cm correspondence distance and at most 50 ICP iterations. Its existing fit gate is fitness >= 0.75 and inlier RMSE <= 0.015 m. The function returns the gate result and information matrix, not individual fitness/RMSE values; this report does not invent those values.

Each selected capture is registered directly to sequence 384, not chained through intermediates. Calibration stamps, timestamps, evidence IDs, image dimensions and constant intrinsics are checked; depth content hashes are verified. FK uses the pinned processed robot-only URDF and source configuration without loading meshes. The head optical transform is:

```text
E_i = T_base_zed(q_i) * T_zed_camera_offset * diag(1, -1, -1, 1)
D_i = ICP transform mapping reference-camera points to current-camera points
T_reference_base_current_base = E_384 * inverse(D_i) * inverse(E_i)
```

This compensates articulated head-camera motion using each observation's joint positions. It is episode-reference-relative, not simulator-global pose. The 30 Hz control convention gives 4 simulated seconds across 120 holds; capture wall time is 93.654 seconds and is not used to integrate physical velocities. Reference-relative registration across these gaps is an offline diagnostic, not a pass through the live freshness gate.

## Depth-Derived Base Change

All five registrations passed the existing fit gate. Translations are expressed in the sequence-384 base frame; rotation is the full SO(3) angle, with yaw reported separately.

| Sequence | Elapsed simulated seconds | Translation x/y/z, mm | Translation norm, mm | Rotation, degrees | Yaw, degrees |
| --- | ---: | --- | ---: | ---: | ---: |
| 384 | 0 | 0 / 0 / 0 | 0 | 0 | 0 |
| 414 | 1 | -0.358 / 0.060 / 0.131 | 0.386 | 0.499104 | 0.495181 |
| 444 | 2 | -0.379 / 0.062 / 0.165 | 0.418 | 0.499004 | 0.494926 |
| 474 | 3 | -0.366 / 0.070 / 0.147 | 0.400 | 0.499022 | 0.495021 |
| 504 | 4 | -0.363 / 0.060 / 0.137 | 0.393 | 0.499126 | 0.495190 |

Composing the estimates for 414 and 504 gives only **0.00779 mm translation and 0.000132 degrees rotation** between them. These tiny numerical differences are not a demonstrated sensor accuracy. The estimated early offset could reflect actual settling motion, capture timing, or systematic registration effects; these samples do not locate its onset or establish its cause. They provide no evidence of appreciable continuing reference-relative drift after the first sampled second.

## Why The Stop Failed

The unchanged assisted check includes joint/finger limits from `experiments/behavior/base_hold.py` plus stricter base limits from `experiments/behavior/assisted_probe.py`. Recomputed failure counts match the 120 recorded failures:

| Condition | Failing holds / 120 |
| --- | ---: |
| Base linear speed > 0.002 m/s | 57 |
| Base absolute yaw rate > 0.005 rad/s | 0 |
| Any left-arm joint speed > 0.03 rad/s | 116 |
| Any right-arm joint speed > 0.03 rad/s | 120 |
| Any torso joint speed > 0.03 rad/s | 120 |
| Any finger speed > 0.005 m/s | 0 |

Across all 121 retained observations from 384 through 504, maximum arm/torso reference-position drift was **2.0541e-5 rad**; maximum finger drift was **7.1898e-7 m**. Maximum adjacent-observation joint finite-difference speed was **0.000616 rad/s**, much smaller than the failing instantaneous velocity channels.

| Joint | Endpoint position change, rad | Mean absolute sampled velocity, rad/s | Signed right-endpoint velocity sum over 4 s, rad |
| --- | ---: | ---: | ---: |
| Left arm joint 5 | +7.749e-6 | 0.034423 | -0.137693 |
| Right arm joint 5 | +1.766e-6 | 0.040235 | -0.160941 |
| Torso joint 1 | +3.576e-6 | 0.047066 | -0.188263 |

These velocity sums are diagnostic quadrature of instantaneous samples, not validated displacement integrals. Their magnitude and sign disagreement with observed displacement support a sampling/feedback inconsistency at the retained observation rate. They cannot distinguish substep oscillation or solver effects from stale/misaligned velocity feedback, indexing issues, or another controller/observation timing mechanism.

Reported base linear speed ranged from **0.001642 to 0.002415 m/s**, and absolute yaw rate from **0.001359 to 0.003978 rad/s**. Summing speed magnitudes at 1/30 s gives **8.007 mm** and **0.012531 rad (0.718 degrees)**. Path-length-like sums and net endpoint transforms are different quantities, so their mismatch alone is not a base-velocity bug diagnosis. The absence of ongoing drift in the selected depth estimates is supporting, not definitive, evidence.

## Provenance And Consequences

Verified input SHA-256 values:

- Retained `hybrid_short.json`: `87ed3dd5346e2704f6755872442940eb73049ca28c7ca3699dd9967ff8f7aedf`.
- `runs/released_policy_audit/kinematics/native_r1pro_processed.urdf`: `b0d76760cbedfbcbe1ddc280380dd5f497bbca380313bc096d7239a2c50dae61`.
- `runs/released_policy_audit/kinematics/native_r1pro_source_cfg.yaml`: `d3eb97811138d00edd83bc2be23f8d1d2e2b17c1bbea237a7cf2f9f89752524e`.

The private JSON retains per-joint comparisons, full transforms, depth hashes and information-matrix eigenvalues. No host details or licensed geometry are reproduced here.

ICP fit is not independent ground truth or proof of motion observability. This is one head camera, one retained run and five reference-relative depth fits. Motion between sampled frames, dynamic scene content, local ICP bias and substep oscillation remain unresolved. No live controller, freshness, collision, payload or stop qualification follows.

Next prerequisite is a separately authorized timing/feedback investigation that establishes what each velocity channel measures relative to controller/physics substeps and position capture. Retain unchanged stopping gates and fail closed until the discrepancy is explained and independently qualified; do not replace the velocity gate with these offline position/depth results.

## Source-Only Follow-Up: Capture And Control Semantics

Read-only inspection on 2026-09-22 confirmed the remote BEHAVIOR checkout HEAD as `b1979916ec1549b10a4e65e630bc6504a9af1b00`. The inspected controller, robot, entity, simulator, evaluator, environment, evaluation config and `usd_utils.py` tracked paths showed no diff from HEAD. Only SSH source reads and Git inspection were performed; no simulator imports, physics, remote edits, process interruption or threshold changes. This follow-up appends documentation only and does not change the diagnostic script/results above. Source references below are relative to the BEHAVIOR checkout, under `OmniGibson/omnigibson/`.

### Proprioception Layout Is Consistent

`eval/r1pro.yaml:13-28` explicitly orders `base_qvel`, left arm position/velocity, left EEF position/quaternion, left gripper position/velocity, the equivalent right-hand fields, then trunk position/velocity. `robots/robot.py:1536-1537` concatenates that configured list:

```python
proprio_dict = self._get_proprioception_dict()
dic = th.cat([proprio_dict[obs] for obs in self._proprio_obs]), {}
```

With the retained robot's 7-joint arms, 2-joint fingers and 4-joint trunk, the resulting zero-based half-open slices are:

| Field | Slice |
| --- | --- |
| Base velocity | `p[0:3]` |
| Left arm position / velocity | `p[3:10]` / `p[10:17]` |
| Left EEF position / quaternion | `p[17:20]` / `p[20:24]` |
| Left fingers position / velocity | `p[24:26]` / `p[26:28]` |
| Right arm position / velocity | `p[28:35]` / `p[35:42]` |
| Right EEF position / quaternion | `p[42:45]` / `p[45:49]` |
| Right fingers position / velocity | `p[49:51]` / `p[51:53]` |
| Trunk position / velocity | `p[53:57]` / `p[57:61]` |

`robots/robot.py:1577-1592` selects position and velocity using the same arm/gripper/trunk index arrays. `robots/robot.py:2815-2818`, `2831-2833` and `4027-4033` build those arrays from joint names, not assumed contiguous low-level arm slices. Thus our three questioned velocity slices match the configured semantic layout; interleaved articulation joint ordering does not invalidate these concatenated proprioception slices. For a holonomic base, `robots/robot.py:1628-1641` rotates planar joint velocity into the yaw-relative base frame and retains the yaw rate.

### Control Writes Targets, Not Routine Joint-State Resets

`eval/r1pro.yaml:35-51` and `73-80` configure both arms and trunk as absolute-position `JointController`s with `use_impedances: false` and `use_delta_commands: false`. The base is velocity controlled (`62-72`). The traced sequence is:

1. `envs/env_base.py:561-580` calls each robot's `apply_action`. `robots/robot.py:795-802` slices the action by controller command dimensions and calls `ControllerView.update_goal`; `controllers/controller_view.py:102-112` converts the command and forwards it. This does not immediately reset arm positions.
2. `controllers/joint_controller.py:281-291` sets the absolute goal to the command and clips to limits. With impedances disabled, `366-369` returns the target as the control signal.
3. Before each physics step, `simulator.py:1419-1435` calls `ControllerView.step_all()`, robot `post_step()`, then `ControllableObjectViewAPI.flush_control()`. `controllers/controller_view.py:94-99` invokes each controller's `step()`.
4. `controllers/controller_base.py:460-482` computes/clips controls and, for position control, writes **position targets plus zero velocity targets**:

```python
ControllableObjectViewAPI.set_all_joint_position_targets(
    routing_path, enabled_rows, enabled_controls, self.dof_idx
)
ControllableObjectViewAPI.set_all_joint_velocity_targets(
    routing_path, enabled_rows, enabled_controls * 0, self.dof_idx
)
```

`utils/usd_utils.py:1286-1306` buffers target arrays; `1183-1192` flushes them. The final position write is `_view._backend.set_dof_position_targets(...)` at `1158`, not `set_dof_positions`. A zero velocity **target** is not a reset of measured dynamic velocity.

An actual instantaneous setter exists separately: `prims/entity_prim.py:649-656` distinguishes `drive=True` target setting from `drive=False` state setting. `utils/deprecated_utils.py:434-450` implements the latter with `set_dof_positions`, explicitly decoupled from position targets. `robots/robot.py:767-775` also has a conditional holonomic yaw-wrap state setter outside +/-pi; this is not an every-step arm/trunk reset. `robots/robot.py:822-837` describes and invokes assisted-grasp constraint handling between control computation and flush, not a generic arm/trunk position reset.

**Finding:** the proposed routine position-command teleport/reset mechanism is not supported by the traced standard arm/trunk control path. Existence of a separate instantaneous setter does not establish that it ran in this trace.

### Capture Ordering And Velocity Estimation Boundary

`eval/evaluator.py:247-251` obtains an action, calls `env.step(..., n_render_iterations=1)`, optionally synchronizes lighting/observations, then preprocesses the result. `envs/env_base.py:635-647` applies action goals, calls `og.sim.step()`, then `_post_step`; `_post_step` reads observations at `582-585`. `simulator.py:1380-1394` performs the configured physics/render loops, then non-physics processing. This establishes post-step observation collection at the Python call level, not capture in the middle of an explicit environment step.

Within a proprioception read, `robots/robot.py:1546-1548` requests joint **positions first, velocities second, efforts third**, with no intervening explicit simulation step in that function. `prims/entity_prim.py:859` and `892` call `_articulation_view.get_joint_positions()` and `.get_joint_velocities()` respectively. The articulation view is instantiated from the project subclass in `prims/entity_prim.py:133-136`; `utils/deprecated_utils.py:79` inherits the underlying Isaac articulation view. This bounded source audit did not inspect the installed Isaac/native getter implementation or establish an atomic common physics timestamp for those two reads.

There is also a **different controller-side cached/estimated velocity path**:

- `simulator.py:1444-1452` calls `ControllableObjectViewAPI.post_physics_step()` after physics. `utils/usd_utils.py:1114-1133` preserves prior cached positions/transforms, then clears/refreshes the cache. `1135-1148` refreshes current DOF positions.
- `utils/usd_utils.py:1494-1505` returns `(current_positions - previous_positions) / physics_dt` only for `estimate=True` with history; otherwise it reads `get_dof_velocities()`. Its comment at `1111` explicitly says the prior poses are for estimating velocities because native values are inaccurate. That is an upstream rationale, not proof of this run's failure mechanism.
- `controllers/joint_controller.py:319-331` uses `estimate=True` in impedance control. The inspected R1Pro arm/trunk config disables that branch. Robot proprioception follows the separate articulation getter path above, not this explicit finite-difference estimator.

When lighting synchronization is enabled, `eval/evaluator.py:132-143` performs three renders and recollects observations. This is a conditional source path, not evidence that it executed during the retained stop interval. Likewise the generic render-propagation warning in `simulator.py:1396-1398` does not prove the early depth yaw offset was stale imagery.

### Follow-Up Conclusion

The source confirms the intended proprioceptive index mapping, target-based position control, and a distinction between native velocity feedback and an available physics-substep finite-difference estimate. It does **not** prove mismatched capture substeps, stale feedback, a physics-solver cause, or routine arm/trunk state resets in the retained experiment. The observed discrepancy remains real at the saved observation level, but its causal mechanism is **unresolved**. No speculative runtime fix, estimator substitution or threshold adjustment follows; live stop qualification remains failed.

## Fresh Physics-Substep Diagnostic

Two separately labeled ordinary-reset attempts used the same frozen policy,
384 policy actions, then a maximum of 60 zero-base hold commands. No yaw,
transit, GPT call or target-conditioned motion was added. Source observation
and feedback are robot-only; base/world poses and task truth are excluded.

`post-policy-feedback-20260922-r1` sent **zero holds**: an extra entry-speed
check rejected the policy's final 0.299110 rad/s yaw rate (planar speed
0.001293 m/s). The logger was never installed. This failed attempt is retained.
That entry-only condition was then removed so a zero-base command can begin
braking. All existing post-step speed/drift guards and measured-stop thresholds
remain unchanged, with regression coverage for a moving entry and a failed
post-step bound. No nonzero base command was permitted by the correction.

`post-policy-feedback-20260922-r2` completed **384 policy + 60 hold actions**.
The read-only logger wrapped the pinned simulator's existing post-physics
handler, invoked the original handler first, and sampled named arm/trunk/finger
positions and velocities. It captured **240 callbacks at 120 Hz**, four per
control action, with **239 consecutive time-consistent intervals**, zero dropped
rows, no logger error, and verified callback removal. Same-callback sampling
still does not prove atomic native getter timestamps.

The instrumented capture completed, but **measured stopping failed**. Fourteen
of 60 control-boundary samples passed the conjunction, never five consecutively
(maximum streak four, final streak zero). The top-level runner's operational
`passed` flag means the diagnostic was collected; `feedback_hold.passed=false`
and `stop_acknowledged=false` are the actual stopping outcome.

| Unchanged failure condition | Failed control samples / 60 |
| --- | ---: |
| Base linear speed > 0.002 m/s | 46 |
| Base yaw speed > 0.005 rad/s | 0 |
| Left/right arm joint speed > 0.03 rad/s | 0 / 0 |
| Torso joint speed > 0.03 rad/s | 31 |
| Finger speed > 0.005 m/s | 0 |

Base speed ranged from 0.000398 to 0.003106 m/s; maximum absolute yaw rate
was 0.003230 rad/s. At control capture boundaries, maximum arm/trunk drift from
the pre-hold anchor was 1.3005e-5 rad and finger drift 3.9861e-7 m.

Within the latter half of the physics log, maximum native arm/trunk speed was
**0.036131 rad/s**, while the corresponding maximum finite-difference magnitude
across all arm/trunk positions was **0.000758 rad/s**. For torso joint 1, mean
absolute native velocity over the full log was **0.016047 rad/s**, versus
**0.000126 rad/s** from positions. Its maximum position excursion from the first
substep sample was **1.43e-6 rad**. Early braking transients exist: this is not a
claim that every physics interval had zero motion.

The mismatch therefore persists at the exposed physics-callback frequency;
ordinary 30 Hz observation downsampling alone does not explain it. Getter
timestamp semantics and internal solver behavior remain unresolved. The logger
does not capture base virtual positions, and these joint findings cannot
authorize a base stop. No gate, velocity-source substitution or navigation
admission is changed by the offline finite differences.

Private artifacts: `A/feedback.json`, `A/hybrid_short.json`, and
`substep-analysis.json` under the r2 run. Reproduction uses
`scripts/analyze_substep_feedback.py --input .../A/feedback.json --output .../analysis-new.json --input-kind retained_trace`.
The source trace is preserved and analysis is written separately. Runtime
helpers and regressions are public in `experiments/behavior/feedback_diagnostic.py`
and `experiments/behavior/tests/test_feedback_diagnostic.py`.

### Independent Depth Check Of The New Hold

The same unchanged fixed-reference head-depth ICP and robot-only FK method was
then run offline at sequences 384, 399, 414, 429 and 444. All five fits passed
the existing registration gate. It took 8.38 s and issued no model/native calls.
The source trace and earlier diagnostic reports were not modified.

| Sequence | Reference-relative translation norm, mm | Reference-relative yaw, degrees |
| --- | ---: | ---: |
| 384 | 0 | 0 |
| 399 | 1.70845 | 0.503404 |
| 414 | 1.69626 | 0.503122 |
| 429 | 1.69488 | 0.502999 |
| 444 | 1.71410 | 0.503223 |

The approximately half-degree offset is already present by the first sampled
half-second. From 399 to 444, the composed estimates differ by 0.00672 mm and
0.000246 degrees. These are numerical consistency figures, **not established
sensor accuracy or proof of zero motion**. Actual early braking, sensor timing
and registration bias remain possible explanations; this does not resolve the
origin of the initial offset or qualify live moving-base localization.

The depth evidence supports little continuing relative drift after the first
half-second, while the native velocity-based stop still rejects the interval.
The next targeted work is to qualify feedback/observation timing and a measured
stop estimator under actual motion and stop cases, retaining failure detection;
not to increase tolerances until this trace passes. Swept clearance remains a
separate prerequisite for target-directed transit.

Private result: `post-policy-feedback-20260922-r2/depth-analysis/analysis.json`.
The generalized diagnostic now accepts explicit `--run` and `--output` while
preserving the original 120-hold default and its existing results.
