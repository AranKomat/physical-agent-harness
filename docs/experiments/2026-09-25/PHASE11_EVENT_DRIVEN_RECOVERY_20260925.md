# Phase 11 Event-Driven Recovery

Date: 2026-09-25

## Result

The bounded exploratory recovery experiment passed end to end.

The predeclared failure was a transport/evaluation dropout after the proven
soda-can lift: the first verification input omitted current left-wrist depth while
the complete raw capture remained retained. The runtime independently detected
`depth.left_wrist` as missing and froze a causal packet with two options:
`recapture_current_state` or `hold_without_reverification`.

GPT-6 Sol Flex selected `recapture_current_state`. The same live simulator then
executed six stationary hold actions, acquired fresh paired RGB-D and
proprioception, and completed at 36/36 actions. An offline verifier bound the
decision to the frozen packet and checked only legal RGB-D plus robot-only forward
kinematics from legal proprioception.

| Condition | Verified recovery |
| --- | ---: |
| Fixed no-recovery | 0/1 |
| GPT recovery | 1/1 |

The robot-only grasp center rose 50.010 mm during the lift. During the recovery
recapture it moved 0.021 mm. All 230,400 left-wrist depth pixels were paired, with
0.0033 mm median absolute depth change. Post-lift versus recapture RGB had 0.518
mean absolute error and 1.261 RMSE.

The model call completed in 2.77 seconds with 769 prompt tokens, 59 completion
tokens, and `$0.001064` cost. There were no automatic retries. Two local launches
failed before output creation, reservation, or network access because the package
root was absent from `PYTHONPATH`; those setup failures consumed no model calls.

This satisfies the Phase 11 five-part gate for one deliberately injected failure
class: independent detection, causal current evidence, bounded GPT alternative,
physical execution, and fresh verification. It does not establish natural sensor
failure robustness or BEHAVIOR benchmark success. Initialization remained
scripted, external clearance remained unknown, and `motion_qualified=false`.

## Evidence

- verification report SHA-256:
  `bfedaa8fef1036313eb3dce42018a731ef87d23f166df15dfc8612764b43a324`;
- execution receipt SHA-256:
  `1f21e8069b269a05f92ac9e65494100481450d76bc844b9fa15388adc3b6ac29`;
- injected-failure record SHA-256:
  `e685f78601e8ab1a4af79236bf65733346966e7bd8c0e28b90132814a5717e81`;
- causal recovery packet SHA-256:
  `739fb4b2de92a04335fcc6b73a063bd86f5ca4b371eb9256d8fb601df246f96a`;
- GPT decision SHA-256:
  `2647630dbe3979d2ce76ae7064b295087b140e2f356caa2a1c8b4fd519e0aabf`;
- robot URDF SHA-256:
  `b0d76760cbedfbcbe1ddc280380dd5f497bbca380313bc096d7239a2c50dae61`.

## Next Gate

Phase 12 should execute a memory-sensitive decision with the same fixed motor
backend. Compare M0 current evidence, M1 causal event/text history, and M2 selected
historical visual evidence. The endpoint must be physically verified progress or
recovery, not answer accuracy.
