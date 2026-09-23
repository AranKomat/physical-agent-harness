# Full-Body Hold Calibration

## Scope And Isolation

One explicitly approved simulator-only attempt: at most 30 fixed hold actions,
no commanded transit or manipulation, unchanged raw stop/abort gates, unknown
external clearance logged, zero paid calls. The attempt completed 30 actions,
31 RGB-D/proprio captures and 120 physics callbacks without callback errors.
The original stop acknowledgement remains **false**. No automatic retry occurred.

The action vector was fixed from initial legal proprioception using the existing
hold codec. Legal telemetry retained torso, both arms and four finger joint
positions/raw velocities (22 joints); virtual base positions were excluded.

A separate write-only evaluator sink recorded `base_link` world poses to
`evaluator-base-poses.jsonl`. It returned no pose values to command generation,
abort checking, stopping or the legal observation stream. Post-run analysis alone
read that file. No object poses or task truth were queried. There are 121 matched
joint/evaluator records including the initial sample. Source snapshots and
before/after hashes are preserved. This evaluator data is not eligible for
runtime memory, planning or control.

## Measurements

| Measurement | Result |
| --- | ---: |
| Maximum sampled base-link planar displacement from start | 1.192 micrometres |
| Maximum evaluator substep planar interval rate | 0.128 mm/s |
| Maximum evaluator control-interval planar rate | 0.0435 mm/s |
| Maximum raw base speed at control endpoints | 2.439 mm/s |
| Raw base endpoints over the unchanged 2 mm/s limit | 2 / 30 |
| Evaluator base-link substep intervals over that limit | 0 / 120 |
| Maximum evaluator substep rotation rate | 0.000522 rad/s |

The largest position-derived joint rate was torso_joint2 at 0.030985 rad/s in
the first physics interval. Its position span was 0.000263 rad. Thus a hold command
does not imply perfect stationarity from its first instant. Wrist raw velocity
again reached 0.014426 rad/s while its position-derived maximum was 0.00010044
rad/s. These signals must not be treated as interchangeable.

## Independent Legal Estimator Evaluation

After native execution ended, all 31 head RGB-D captures were processed using
the existing fixed-first-reference point-to-plane path. Robot-only URDF/FK and
measured joint positions converted camera motion to base-link motion:

`T_base0_basei = E0 * T_camera0_camerai * inverse(Ei)`.

The estimator received no evaluator pose, warm-start truth or target coordinates.
Comparison against relative evaluator base-link poses found:

- Maximum observed translation error: **8.323 micrometres**.
- Maximum observed rotation error: **9.977e-6 rad**.
- All 31 captures processed; no fit retries or alternative initializations.

This is empirical agreement in one near-stationary simulator trace, not a
calibrated error bound. Evaluator poses have simulator numeric precision limits;
reported micrometre-scale differences do not imply real-world sensor accuracy.
Finite differences cannot rule out movement within a physics interval. Raw
virtual-joint base velocity and base-link point displacement are not identical
quantities under arbitrary rotating motion.

## Conclusion And Next Gate

The extra measurements support a mismatch between raw velocity readback and
sampled base displacement during holding. They do not establish why the simulator
produces it or justify silently replacing raw stop gates.

The legal camera/FK path now has a first retrospective base-pose comparison, not
only ICP fit scores. The missing test is sensitivity and error during deliberate
motion and braking, with complete joint monitoring and the same evaluator/control
separation. That requires a separately bounded and approved exploratory protocol.
No repeat hold-only trial is justified by this result alone.

Strict stopping, clearance, base transit and arm return remain unqualified.
Phases 5-7 are incomplete; no task or GPT-benefit claim follows.

## Evidence And Verification

Private run: `runs/full-body-stop-calibration-20260923-r1`.
Analyses: `runs/full-body-stop-analysis-20260923-r1` and
`runs/full-body-stop-rgbd-evaluation-20260923-r1`.

Receipt SHA-256:
`64f7054af1d8a71e79ea045cffc0d4623789af453bfe5df0207093c6794ce69a`.
Evaluator JSONL SHA-256:
`9e6a91dcfd514b7b2125c0b5e53062983e4a66cb4bab5eb2978744dd51245601`.
Legal joint JSONL SHA-256:
`c048c28ce3cfebfeb9936b061e11b4dd7fe06790acba07bbe173236cfebf2735`.

Complete run (about 149 MB) and log copied locally; run checksum comparison
reported no differences. GPU compute process list was empty after completion.
Private suite: **1009 passed, one existing skip**. New scripts pass Ruff.
Raw and licensed artifacts remain private. No rental lifecycle action was taken.
