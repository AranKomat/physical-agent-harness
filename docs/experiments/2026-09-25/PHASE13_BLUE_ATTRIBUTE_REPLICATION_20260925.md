# Phase 13 Blue-Attribute Replication

Date: 2026-09-25

## Result

The first Phase 13 robustness replication failed at the semantic decision layer.
Physical execution remained valid in all three conditions.

This cohort repeated the Phase 12 memory-sensitive boundary with one declared
change: the staged can and required historical color changed from orange to blue.
The task was to lift only when supplied evidence established that the can's
dominant visible surface at the earlier observation was blue. M0 received current
evidence, M1 added causal text without the color attribute, and M2 additionally
received the earlier left-wrist RGB image labeled with its original historical
stamp and digest.

GPT-6 Sol selected `hold` for M0, M1, and M2. M0 and M1 were correct. M2 should
have selected `lift_current_candidate`, because its historical image visibly
showed the blue surface. The failed M2 response was retained without a retry or
prompt adjustment.

| Condition | Decision | Expected | Physical execution valid | Verified progress |
| --- | --- | --- | --- | ---: |
| M0 | hold | hold | yes | 0/1 |
| M1 | hold | hold | yes | 0/1 |
| M2 | hold | lift | yes | 0/1 |

Every packet-bound decision executed for 30 actions in a fresh deterministic
fixture. Each hold moved the grasp center by about 0.012 mm. Every verifier
retained 230,400 paired depth pixels; median absolute depth change was 0.0026 mm.
The three model calls used 5,821 prompt tokens, 383 completion tokens, and
`$0.009189` total. Latencies were 2.686 s, 3.980 s, and 4.327 s for M0, M1, and
M2.

The request and structured-output schema were correctly bound to M2's packet.
The historical image was transmitted with the expected digest, role, camera, and
stamp. Therefore the current evidence supports a semantic-decision failure, not a
schema, transport, packet-binding, or motor failure.

The preserved image is an extreme close-up: blue is visually clear, but the can's
object shape is not. One plausible explanation is that the conservative executive
did not consider the image-to-can correspondence established strongly enough,
especially under the instruction not to invent object identity. This is a
hypothesis from the frozen evidence, not a post-hoc correction. The cohort must not
be rerun or prompt-tuned after observing the failure.

## Evidence

- protocol file SHA-256:
  `253d0cd2ea2669c039d53e561395c494ec2d26946259dc5d3b513ecb9dd86c88`;
- decision report SHA-256:
  `f5042bf004141759779573f234a76a795165c6cc44f14636067d49db3f1f7425`;
- final score SHA-256:
  `cac4e675e83f8013ea69f6e227d2a74352725ae3b4e1a3bc6f9f6efaa30565ce`;
- M0 receipt / verification:
  `fcc27ba146b5be6009d8b6a47bad937896f48b6819bd48cc6610bba8ce6ce9cb` /
  `c6acfcd30bb74668736f02eb128106bcc17641408218c0123cb7e00fdc474c0d`;
- M1 receipt / verification:
  `62dfc63c928aa1cd913845ed4c01b212d82973f9871981818b922fc6a16ae88c` /
  `7275ebb2d656bd5274298e708bab41b0bc9894b9be7b0ae7efd903b6c34f608b`;
- M2 receipt / verification:
  `265cdd3c73a03d2ebcdf077d1c547338237dd22bed7274502a2a1a6fb03caac6` /
  `d30057d94ac131dd7bb921e0150b834be4b3aad191260d4e00238c43c212f961`.

## Interpretation And Next Gate

Phase 12 established one positive orange visual-memory boundary. Phase 13 now
shows that the benefit did not replicate under the first attribute change. This
does not invalidate causal memory mechanics, but it blocks a robustness claim.

Do not rerun the blue case. The next independent axis should retain the successful
orange attribute and change only the simulator seed. If that seed passes, run one
predeclared visual-distractor cohort. Phase 14 efficiency optimization remains
premature until useful behavior survives at least one independent robustness axis.

This remains a scripted development fixture, not BEHAVIOR benchmark success.
Initialization was scripted, current left-wrist RGB dropout was injected,
external clearance stayed unknown, and `motion_qualified=false`.
