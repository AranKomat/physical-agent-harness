# Motion Measurement Diagnosis

## Evaluation Boundary

Run r4 repeats the ordinary-radio forward pulse with explicitly quarantined
robot-base and camera world poses, read only for offline evaluation. None of
these poses enters the controller or legal sensor evidence. The action driver
is unchanged. This is diagnostic evidence, not an oracle-free benchmark result.
All 155 source receipt/evidence/truth files were SHA-256 verified locally.

- Receipt: `f9b8ed15480dadb243104cd87555d8f872bf30e73e5a943fad04402761224d9d`
- Quarantined truth: `d71ba89f872e68293e0d2f89701b428c75321da5f526c580ceb7a3803bd07f4d`

## Findings

The actual endpoint moved 11.419 mm forward, 0.015 mm sideways, with total
rotation 0.00825 degrees. In the last five moving intervals, pose differences
indicated 0.02291 m/s forward versus 0.02726 m/s in instantaneous proprioception.
Those are different temporal measurements; the discrepancy does not alone prove
a simulator bug. Arm/torso positions also change much less than instantaneous
joint velocities suggest. Do not integrate sampled velocities as ground truth.

Robot-only FK camera extrinsics agree with the quarantined camera poses within
1.5 micrometres and 0.000052 degrees across this trace. Mount calibration is not
the observed centimetre-scale localization error at this posture.

Sequential per-tick hybrid RGB-D odometry produced endpoint errors of 40.9 mm
(head), 17.1 mm (left wrist) and 13.5 mm (right wrist). Direct initial-to-final
registration on the same trace gave:

| Method | Head translation error | Head rotation error |
| --- | ---: | ---: |
| Hybrid RGB-D | 1.951 mm | 0.0579 degrees |
| Color RGB-D | 4.263 mm | 0.0969 degrees |
| Point-to-plane ICP | 0.247 mm | 0.0169 degrees |
| Colored ICP | 4.273 mm | 0.1078 degrees |

This supports accumulated small-step estimation error as a contributor. It does
not establish that endpoint registration generalizes. Wrist point-to-plane ICP
reported near-perfect fitness while missing essentially the whole translation;
the visible robot dominates those images. Registration fitness alone cannot
establish world-motion observability. Do not fuse those wrist estimates blindly.

## Frozen Follow-Up Candidate

Before inspecting r5 yaw results, select **head-only fixed-reference
point-to-plane ICP** for the next offline check:

- Existing legal full-resolution depth, decimated by 2 with intrinsics scaled
  consistently; linear depth in metres, 10 m truncation.
- Voxel size 0.01 m; normal radius 0.04 m, maximum 30 neighbours.
- Maximum correspondence distance 0.05 m; 50 iterations; identity initialization.
- Initial capture as reference; no truth initialization or pose prior.
- Compare against quarantined truth only after estimates are frozen.
- Diagnostic endpoint bounds remain 5 mm and 0.5 degrees.

Direct endpoint replay is offline and does not apply the runtime's consecutive
frame-gap gate. It must not silently replace that gate. Any online implementation
must still receive fresh, monotonically ordered observations and distinguish an
old reference keyframe from stale current sensing. No production estimator or
hybrid admission gate is changed by this analysis.

## Yaw Follow-Up And Online Shadow

The frozen head-depth candidate passed the separate r5 yaw endpoint check:
0.085 mm translation error and 0.0120 degrees rotation error. Actual yaw motion
was 0.6256 degrees; last-five interval-average yaw rate was 0.02182 rad/s versus
0.09405 rad/s instantaneous proprioception and a 0.050 rad/s command. Therefore
the earlier reported yaw overshoot did not describe net angular displacement.
The original velocity-response diagnostic remains failed; no threshold is changed.

Causal fixed-reference replay across every frame, not just the endpoint, had
maximum head-derived base translation errors of 0.782 mm (r4 forward) and
0.550 mm (r5 yaw). References are always the first legal capture, never a truth
pose. Wrist estimates remain excluded from this candidate.

Run r6 then ran the estimator **live in shadow**, with all 26 captures accepted,
25 counted actions and no freshness failures. Offline evaluation of those saved
online estimates yielded maximum translation error 0.779 mm, endpoint translation
error 0.266 mm and endpoint rotation error 0.0187 degrees. Its forward response
and measured stop passed. Raw evidence and truth remain private; all 155 source
files were verified after transfer.

- r5 receipt: `faad032b14cc505da230ca339b64bb377bec68e8796a8e5397183feb6b2e185c`
- r6 receipt: `6ea8467488a69d239c4902a20d7cd2b790ddcf29fda090ab0b28a65882f58b5e`

The existing public estimator now has an opt-in fixed-reference mode; default
previous-frame behavior is unchanged. Current-frame freshness, episode identity,
rigid-transform validation and loss latching remain active. Calibration changes
invalidate either mode. A new head-depth shadow callback uses the existing
estimator interface, not a new mapping stack. This is evidence for one bounded
start/posture, not general navigation or full-body clearance.

## Next Diagnostic

Proceed to a **tiny-perturbation** A-short/B-short pair without GPT. Both receive
384 Behavior-Skill actions with the unchanged native 32-action prefix and same
instruction. B first receives the tested 15-tick forward pulse plus measured
settling/braking; it must also retain valid, stable live head-depth estimates.
Policy reset acknowledgements and noise indices are matched relative to each
handoff, while native action counts retain the classical exposure.

This is not target-directed staging: no target distance is invented, unknown
clearance is disclosed, and strict hybrid navigation gates remain unchanged.
It tests whether the frozen VLA behaves normally after a small intervention;
it cannot establish that transit helps task completion. The main target-localized
A/B comparison still requires its own staging prerequisites.
