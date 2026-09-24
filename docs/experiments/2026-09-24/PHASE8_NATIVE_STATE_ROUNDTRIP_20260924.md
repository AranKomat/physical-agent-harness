# Phase 8 Native State Roundtrip Diagnostic

Date: 2026-09-24

## Scope

This evaluator-only diagnostic tested whether OmniGibson's native serialized
state APIs could provide a sufficiently faithful branch point for the matched
Phase 8 A/B/C study. It did not expose snapshots to control, authorize motion,
claim benchmark evidence or make paid model calls.

The frozen procedure captured legal radio RGB-D and robot state, serialized the
simulator, advanced five bounded hold actions, restored the serialized state and
captured fresh observations. No automatic retry was allowed. Attempts r1-r3 are
retained as failed setup/diagnostic attempts; r4 is the terminal result.

## Frozen Gate

The roundtrip passed only if all of the following held:

- serialized simulator-state maximum absolute error at most `1e-6`;
- proprioception maximum absolute error at most `1e-6`;
- every robot-state field maximum absolute error at most `1e-6`;
- each camera RGB mean absolute error at most `5` intensity levels;
- each camera depth mean absolute error at most `1e-4 m`.

## Result

**Failed.** The serialized-state error exceeded its frozen threshold.

| Measure | Result | Gate |
| --- | ---: | ---: |
| Serialized state max absolute error | `2.622604e-6` | `<= 1e-6` |
| Proprioception max absolute error | `4.768372e-7` | `<= 1e-6` |
| Robot position max absolute error | `1.192093e-7` | `<= 1e-6` |
| Robot orientation max absolute error | `1.192093e-7` | `<= 1e-6` |
| Joint position/velocity max absolute error | `0` | `<= 1e-6` |

All three cameras passed the frozen *mean* image-error bounds:

| Camera | RGB MAE | RGB max | Depth MAE | Depth max |
| --- | ---: | ---: | ---: | ---: |
| Head | `1.9745` | `204` | `3.327e-6 m` | `0.05764 m` |
| Left wrist | `1.8102` | `58` | `5.643e-6 m` | `0.56972 m` |
| Right wrist | `4.7836` | `79` | `3.013e-6 m` | `0.57968 m` |

The large sparse maxima show that fresh renders are not bit-identical even when
mean image differences pass. Native `load_state` also did not rewind simulator
time or the step index: the restored capture remained at step 61 rather than the
snapshot's step 41.

## Decision

Do not use native state restore as a transparent matched-branch mechanism under
the current protocol. It is numerically close enough to be useful for future
evaluator diagnostics, but it failed the preregistered state-fidelity bound and
does not restore causal time. Do not launch another nearby snapshot variant.

Phase 8 still requires either a separately declared snapshot protocol that
explicitly handles clock and render nondeterminism, or a preregistered
counterbalanced multi-start design. Strict clearance and the C condition also
remain unqualified.

The checksum-verified private receipt is retained at
`runs/backups/native-state-roundtrip-20260924-r4/receipt.json` with SHA-256
`c07735cf0f609de1530c908276a6bc36abbf2941b3a49fce2aad60e7a28abf65`.
