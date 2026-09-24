# Balanced SAM Matched Handoff

Date: 2026-09-24

## Scope

This exploratory reverse-order `B -> A` pair tests whether a frozen Behavior-Skill policy remains usable after a source-bound SAM target transit. It is not strict benchmark admission: external clearance remains unknown and `motion_qualified=false`.

- Seed: 2
- Initial proprioception maximum difference: 0
- Policy actions per condition: 1,152
- Acquisition policy actions per condition: 768
- Intervention actions per condition: 92
- Fresh-reset post-handoff policy actions per condition: 384
- GPT or paid model calls: 0
- Automatic retries: 0
- GPU peak: 23,180 MiB, below the 23,552 MiB abort threshold
- Workers reaped: yes

An initial attempt completed B but could not start A because local policy port `8011` was still unavailable. That failed attempt remains retained. The corrected owner assigns distinct ports to each member; focused launcher tests pass.

## Matched intervention

| Condition | Intervention | Command integral | Measured path | Feedback/stop checks |
|---|---|---:|---:|---|
| A | Control hold | 0 m | 0.124 mm | passed |
| B | SAM-directed base transit | 80 mm | 63.865 mm | passed |

Both conditions retained one unique current SAM candidate at all 13 sampled post-handoff boundaries. This is tracker continuity, not independently proven physical identity.

## Policy behavior after handoff

| Measure | A | B |
|---|---:|---:|
| First 32-action mean target projection | 0.00023 m/s | 0.00061 m/s |
| First 32-action fraction below -0.01 m/s | 0 | 0 |
| Full 384-action mean target projection | 0.02976 m/s | 0.05955 m/s |
| Evaluation-only task success | no | no |

The policy did not immediately back away, jitter out of the target, or lose the SAM candidate after B's handoff. The full-window target projection is larger in B, which is directionally promising.

## Validity limit

This pair does not estimate a causal treatment effect. The acquisition action streams differed before intervention (`0.3126` maximum absolute difference and `0.05739` RMS difference), despite identical initial proprioception and the same declared seed. Same-seed simulator reset therefore did not produce a matched policy trajectory. Order, rendering, model runtime or another uncontrolled source may contribute.

Do not claim that classical transit improved policy competence from this pair. The justified conclusion is narrower: this SAM-directed intervention did not obviously destroy immediate policy behavior, and the equal-exposure protocol now runs end to end. A causal Phase 8 comparison needs either replayed/frozen pre-intervention state or multiple counterbalanced starts with a declared analysis.
