# Phase 12 Memory In Execution

Date: 2026-09-25

## Result

The first controlled M0/M1/M2 physical execution comparison passed.

The frozen task was to lift a held soda can only if supplied evidence established
that its dominant surface at an earlier observation was orange. At the post-close
decision boundary, current left-wrist RGB was removed from the model input by a
predeclared transport dropout while the complete raw capture remained retained.
All conditions received the same current head image, depth-evidence identifiers,
proprioception digest, task, options, and motor backend.

- M0 received current evidence only.
- M1 added a causal text event stating that the can had been observed and the
  gripper-close sequence had completed, but explicitly did not record color.
- M2 added the earlier left-wrist image, labeled as historical visual memory with
  its original stamp and evidence hash.

GPT-6 Sol selected `hold`, `hold`, and `lift_current_candidate` for M0, M1, and M2.
Each packet-bound decision was executed in a fresh deterministic fixture start for
30 actions and independently verified from legal RGB-D plus robot-only forward
kinematics.

| Condition | Decision | Verified progress |
| --- | --- | ---: |
| M0 | hold | 0/1 |
| M1 | hold | 0/1 |
| M2 | lift | 1/1 |

Both holds moved the grasp center by about 0.075 mm. The M2 lift raised it 50.010
mm. Every verifier retained 230,400 paired depth pixels and passed wrist-relative
RGB-D stability checks. The three calls used 5,810 prompt tokens, 247 completion
tokens, and `$0.00849525` total.

The original three-call driver completed M0 and M1, then stopped before sending M2
because two images exceeded its conservative 12,000-token preflight bound. The
partial result was retained. M2 used one separately scoped continuation with a
16,000-token conservative bound. There were no automatic retries.

This establishes causal visual-memory benefit for one controlled, executable
boundary. It does not establish general episodic-memory benefit or BEHAVIOR task
success. The current-camera dropout was injected, initialization was scripted,
external clearance stayed unknown, and `motion_qualified=false`. M1 intentionally
did not preserve the color attribute, so this result isolates visual memory rather
than claiming that images generally outperform complete text summaries.

## Evidence

- protocol SHA-256:
  `fdbe977bc043dba62ecbe676ae59bac0dcd5e44c2ec237f8ddbfeeb8a6d912ce`;
- merged decision report SHA-256:
  `a59a13029c2a5fa081a7bca1975df094b317469a339a4dc467c87fe49fb41a9e`;
- final score SHA-256:
  `73c16a9b69d02a37b0ae2f62a496c8f0143b3397a5d4cfbf99d31f6e4c45e4db`;
- M0 receipt / verification:
  `a953725265471da601475dbaaaef31077efc17bf14752600141fbeedc98ff571` /
  `f2f59409ac293c5d36a7b95e8b868e7b9a292d14de479dd5b4bf4fa71f8978f4`;
- M1 receipt / verification:
  `560cd6ea405513cefff240ec5fe7194b0c3f8af314a117aa7394f3bbfbd63c05` /
  `36d09e2218db6002bb306b6af6cee17ba42279fffe4b4bc9efd7d0ba1f5bea48`;
- M2 receipt / verification:
  `a923ff1058400d78a71571f2a8d870f4f50482d785b7a4c82eae72e6630b206d` /
  `8244773345c9735afac3f47e73fc2b8b06a97ae8eca6e2c47ec5f060a5346aab`.

## Next Gate

Phase 13 should replicate only the useful branch first: vary one axis at a time,
starting with a second can color or visual distractor and then a second simulator
seed. Keep the same evidence contract and motor backend. Do not pool layout, task,
identity, and failure variation into one experiment.
