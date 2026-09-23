# cuRobo V2 R1Pro Forward Kinematics

## Result

The actual pinned cuRobo V2 GPU backend passes a robot-only forward-kinematics
comparison on 37 numerical configurations and both tools (74 comparisons).
This is Phase 7 preparation, not a planner, collision or execution pass.

| Comparison | Maximum position error | Maximum orientation error |
| --- | ---: | ---: |
| GPU versus independent yourdfpy, 37 configurations | 1.63e-7 m | 1.71e-8 rad |
| GPU versus native legal EEF feedback, measured posture | 8.24e-7 m | 4.92e-7 rad |

The configurations are one measured posture plus +/-0.01 rad for each of the
18 torso/arm joints, clipped to URDF limits. They are **not** 37 independently
observed physical postures or executed actions. Bounds were declared before
execution: 1e-4 m and 1e-3 rad. Both tool comparisons passed at every sample.
The native feedback comparison checks consistency with the simulator, not
external physical calibration.

Build/load: 2.77 s. First FK: 300 ms; subsequent median 0.343 ms, p95 0.369 ms
(36 samples). Timings synchronize CUDA but exclude result transfers, CPU
comparison and reporting. These are component FK timings, not planning latency.

## Model And Frame Findings

- Root is `base_link`; named model joints exactly match torso4 + left7 + right7.
- The supplied URDF, including the file named `with_meta_links`, lacks the named
  EEF links referenced by the legacy planner YAML. GPU outputs therefore use
  `left_gripper_link` and `right_gripper_link`; tools are explicitly composed
  using the generated configuration: xyz `[0,0,-0.06]`, xyzw `[0,1,0,0]`.
- Original import configuration and generated simulator configuration differ in
  collision decomposition and gripper joint-limit flips. The generated config
  matches the prior audited hash and is the one used here. No source asset edited.
- The bundled planner YAML is legacy cuRobo, with null held-joint values and a
  different root. It was not loaded as if it were a qualified V2 planning config.
- GPU model uses `KinematicsCfg.from_basic_urdf`; upstream explicitly excludes
  collision queries for this API. No empty world or invented collision model was
  used to obtain a planning pass.

The earlier robot-mesh audit found 4,053/9,639 vertices outside the supplied sphere
union, up to 53 mm. The restored USD and URDF hashes match those audited assets.
This negative coverage evidence remains relevant; FK does not resolve it. Even
inside vertices alone would not prove enclosure of mesh surfaces by sphere unions.

## Reproduction And Verification

User explicitly approved isolated preparation on the current 4090. Separate
`/workspace/curobo-v2-venv`; simulator and SAM environments unchanged. Source:
`NVlabs/curobo` at clean `78fd485fa82d9b9a063fb4985e371814587e666a`, matching
the public adapter pin. Python 3.11, Torch 2.7.0+cu128, cuRobo version metadata
0.8.0.post1.dev43, yourdfpy 0.0.60, NumPy 2.4.6, SciPy 1.17.1. Pip check clean.
Source `[cu12]` runtime compilation worked without a system CUDA toolkit install.

Private protocol: `docs/CUROBO_R1PRO_FK_PROTOCOL_20260923.md`.
Private checker: `scripts/check_curobo_r1pro_fk.py`, SHA-256
`7e446c63862e3a1d8c992f9ece0d0ecb7571806c2e58c75cd3030082473ecbcc`.
Inputs:

- URDF: `b0d76760cbedfbcbe1ddc280380dd5f497bbca380313bc096d7239a2c50dae61`.
- Generated config: `d3eb97811138d00edd83bc2be23f8d1d2e2b17c1bbea237a7cf2f9f89752524e`.
- Native observation: `f8795d1487dbd284731298d71b4e6139115b93423f30b7a6bf75849abf54bfd5`.

Attempt r1 failed before GPU work: public observation parsing rejected three
additional native fields. The corrected checker uses the producing native schema,
without discarding unknown fields. Its new regression and explicit r2 declaration
preceded the repeat. Same data, configurations, limits and 600-second timeout.
The failed receipt and old checker are retained, not replaced by the passing run.

R2 verified input/script hashes and clean pinned source both before and after.
Checks reject invalid/nonrigid matrices and non-unit quaternions before SciPy
could normalize/project them. Focused tests: 39 passed; Ruff passed. Full private
suite: **687 passed, one existing skip**. Public runtime unchanged; its suite was
not rerun for documentation-only changes.

Private artifacts copied to Mac: `runs/curobo-v2-restore-20260923-r1`,
`runs/curobo-r1pro-fk-20260923-r1`, `runs/curobo-r1pro-fk-20260923-r2`, and local
`runs/r1pro-planner-preflight-20260923-r1`. R2 receipt SHA-256:
`8f3f83883682e34aab248ff96a2032bd043a1ce943f3e973e1de60bb00ced412`.
GPU process exited zero and released the device. Zero actions and paid API calls.

## Remaining Gate

Next: conservative robot collision geometry and independent enclosure review,
then exact held-joint/tool configuration and a sensor-derived collision world.
Planning, swept-path review, stopping, endpoint execution and return remain
unperformed. Full-loss identity and base localization/clearance gates are also
still incomplete. This result does not promote any motion capability.
