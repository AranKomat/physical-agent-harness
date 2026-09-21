# Native Radio Exploratory Base Response

## Scope

The user explicitly authorized small simulator-only moves with unknown clearance
logged rather than certified free. This separate diagnostic does not override
strict hybrid gates, qualify collision geometry, or establish task success.
No GPT or learned-policy inference is used. All commands preserve the initial
arm, torso and gripper position targets through the audited native 23D codec.

The pinned ordinary radio start is public-test instance 301, seed 0. The runner
uses the evaluator's fresh legal observation path, capturing RGB, depth,
proprioception and boundary-bound intrinsics after each counted native action.
Setup reset/load/reset occurs before the counted trial, not between phases.

## Forward Pulse

Run `hybrid-native-base-exploration-20260921-r1` passed the predeclared response
and stopping diagnostic:

- Five initial settling ticks, 15 forward-command ticks, five braking ticks.
- 25 completed native actions, 26 fresh captures, 0.8333 simulated seconds.
- Command: 0.030 m/s forward; last-five mean: 0.027261 m/s forward,
  0.000664 m/s lateral, 0.003480 rad/s yaw.
- Stop acknowledged after five ticks (0.1667 s), including five consecutive
  samples satisfying the joint-speed checks and tighter base-speed limits.
- Maximum arm/torso target drift: `9.059906e-6` native units;
  maximum gripper drift: `3.390014e-7 m`.
- Integrated braking translation proxy: 0.000669 m. This is an integral of
  sampled proprioceptive speeds, not independently measured displacement.

154 receipt/evidence files were SHA-256 verified after local transfer. Receipt:
`a61a90a46747e8098a6c80fc8141ba275cadcae8a4ca165381a81470bcd09240`.

This establishes a useful native-radio response that the standalone empty
fixture failed to reproduce. It does not establish the cause of that fixture's
failure, a general controller guarantee, or a safe staging corridor. Forward
travel is only approximately centimetre scale.

## Direction Sequence

Run `hybrid-native-base-exploration-20260921-r2` selected all six directions from
a fresh ordinary reset, but correctly stopped after **backward failed**. Forward
reproduced the first run's measurements. Backward commanded -0.030 m/s; its
last-five mean was -0.019004 m/s forward-axis, -0.009793 m/s lateral and
0.046718 rad/s yaw. Both commanded-axis tracking and cross-axis checks failed.
The robot nevertheless satisfied measured stopping after five braking ticks.

Total exposure was 45 native actions and 46 captures, including 30 nonzero
base-command ticks. Left, right and both yaw directions were **not executed**
in this run. This is a failed response diagnostic, not six tested directions
or a failed policy episode. Thresholds remain unchanged. An independent small
positive-yaw pulse from ordinary reset followed as a separate diagnostic, not a
continuation past the failed sequence's stop.

All 274 receipt/evidence files from r2 were hash-verified locally. Receipt:
`5275aa82f55e1404e7bea87ea49dfdaf249f533193b0dd9ab6b6ed6fb744210d`.

## Independent Yaw Pulse

Run `hybrid-native-base-exploration-20260921-r3` commanded +0.050 rad/s yaw from
a fresh ordinary reset. The last-five mean was +0.094048 rad/s yaw, with
-0.001516 m/s forward-axis and +0.002012 m/s lateral response. Translation
cross-axis limits passed, but yaw tracking failed. Stopping again passed after
five braking ticks. Exposure: 25 native actions, 26 captures, 15 nonzero-command
ticks. This is not a license to rescale yaw retrospectively and call it qualified.

The native process finished before the rental stopped during backup. The local
r3 receipt records the failed trial and all 26 capture references, but 100 of
153 referenced evidence files are missing locally. The r3 transfer is therefore
**incomplete and not remotely checksum-verified**. Recover it after the existing
instance resumes; do not rerun or overwrite it merely to fill the archive.

## Visual Consistency Check

Offline RGB-D odometry replayed the first forward trace using contemporaneous
intrinsics and robot-only FK, independently for each camera. No new actions,
model calls, future frames or simulator poses were supplied. All trackers
completed, but completion did not establish agreement:

| Camera | Final estimated translation magnitude | Final estimated rotation |
| --- | ---: | ---: |
| Head | 35.88 mm | 0.596 degrees |
| Left wrist | 11.55 mm | 2.191 degrees |
| Right wrist | 3.83 mm | 0.666 degrees |

The proprioceptive speed integral was 13.97 mm of path length, not net
displacement or ground truth. The camera estimates disagree materially with one
another. Earlier stationary drift also matters at this scale. This replay
**does not independently corroborate precise forward displacement** and assigns
no stationary pass/fail criterion to a moving trace.

## Decision

Do not expand to long navigation or claim a qualified A-short/B-short handoff.
One directional response passes reproducibly at one start, but reverse/yaw
tracking and moving localization remain unresolved. The next useful debugging
target is consistency of sensor-derived motion and native controller response,
not GPT prompts, policy retraining, or relaxed thresholds. No A/B policy inference
was performed by these diagnostics. Strict gates remain unchanged.

Local verification after implementation: 619 tests passed, Ruff passed. The
instance becoming unavailable prevents further native checks this session.

## Accounting

The outer `native_steps_completed` is persisted immediately after each returned
evaluator step, before observation conversion. The generic pulse driver's
`actions_executed` counts successful step-and-capture callbacks. A capture error
can make those counts differ; do not hide that distinction. A simulator exception
inside `evaluator.step` may leave completion uncertain. Process exit status is
not sufficient: the receipt's explicit pass/error fields are authoritative.

Raw sensor imagery remains private. See also the
[empty-fixture comparison](HYBRID_EMPTY_BASE_DIAGNOSTIC_20260921.md) and
[strict qualification sequence](HYBRID_EXPERIMENT_SEQUENCE.md).
