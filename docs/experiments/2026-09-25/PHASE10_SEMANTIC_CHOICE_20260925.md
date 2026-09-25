# Phase 10 Recurrent GPT Semantic Choice

Date: 2026-09-25

## Result

The frozen four-case exploratory comparison passed end to end:

| Condition | Correct | Physically valid |
| --- | ---: | ---: |
| fixed routing | 2/4 | analytical counterfactual over the same qualified options |
| GPT-6 Sol executive | 4/4 | 4/4 |

The four packet-bound GPT choices were `lift`, `hold`, `lift`, `hold` for the
counterbalanced orange/blue rules and orange/blue cans. All four requested
effects were executed with exact current-image rebinding, 30/30 actions, and
independent legal RGB-D/proprio verification.

The two lifts raised the robot-only grasp center by 50.01 mm. The two holds kept
it within 0.011 mm. No simulator object pose, scoring label, or expected decision
entered the GPT request or controller.

This establishes a causal semantic-routing benefit in the scripted exploratory
fixture. It is not BEHAVIOR benchmark success: initialization was scripted,
external clearance remained unknown, and `motion_qualified=false`.

## Preserved transport failure

The original blue-rule/blue-can response was billed but truncated at a 128-token
cap. It was rejected rather than repaired. One explicitly approved 256-token
replacement completed cleanly. The merged report records one replacement call,
zero automatic retries, and the discarded request ID.

## Evidence

- protocol SHA-256:
  `73fdfb41eb5e98dbc7e1979367b686a200ab72fbf9747ac05763401753ca417d`;
- merged decision report SHA-256:
  `cf073d2657a8f0140534b73bde893f3320b48fc542d0ce4b457da2541df94acc`;
- final score SHA-256:
  `e242cbb680706018d47cb540e22b23c21ed8fc8a3acff4f296efe1c827291635`;
- blue-rule/blue-can receipt SHA-256:
  `1d5531b93cff55cf92531a6173ab25e6648953f0da3fb3bb41bfd53fceb4ed7e`;
- blue-rule/blue-can verification SHA-256:
  `36299de6e7ef77d54fadc198a5a41c7e201fbef236de05ef1022120fbec9386c`.

The other three receipt and verification hashes remain recorded in
`PHASE10_SEMANTIC_CHOICE_PARTIAL_20260925.md`.

## Next gate

Phase 11 may now begin. Predeclare one independently detectable failure, expose
only causal current evidence to GPT, offer bounded recovery options, execute the
selected option, and require fresh independent verification of recovery.
