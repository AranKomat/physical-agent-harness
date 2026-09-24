# Phase 8 Counterbalanced Exploratory Handoff

## Question

Across repeated starts and balanced execution order, does the exploratory
SAM-directed base intervention obviously damage the unchanged Behavior-Skill
policy after handoff?

This is a non-strict diagnostic. Clearance remained `unknown`, every receipt
records `motion_qualified=false`, and the result is neither strict Phase 8
admission nor a benchmark result.

## Frozen Protocol

- Conditions: A is a 92-action control hold; B is a 92-action SAM-directed
  exploratory base transit. Both are followed by a fresh policy reset and 384
  Behavior-Skill actions.
- Total policy exposure: 1,152 actions per condition, including the 768-action
  acquisition prefix.
- Starts: seeds 2-5.
- Order: `BA`, `AB`, `BA`, `AB`.
- Automatic retries: zero.
- GPT and paid calls: zero.
- Primary diagnostic: target-directed post-handoff action projection without
  immediate away-motion.
- Secondary diagnostics: current SAM candidates at 13 boundaries, acquisition
  divergence, measured intervention path, wall time and evaluation-only task
  success.

The retained seed-2 pair was frozen by receipt hash before the three new starts.
All six new members completed. The three new pair owners reaped every worker;
their sampled GPU peaks were 23,198, 23,240 and 23,170 MiB, below the frozen
23,552 MiB abort threshold.

## Results

Every one of the eight conditions completed exactly 1,244 native actions:
1,152 policy actions plus 92 intervention actions. B moved 59.89-63.86 mm; A's
mean measured hold path was 0.116 mm.

| Seed | Order | A first-32 projection | B first-32 projection | A full projection | B full projection | B path |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 2 | BA | 0.000226 m/s | 0.000611 m/s | 0.029760 m/s | 0.059550 m/s | 63.865 mm |
| 3 | AB | 0.000736 m/s | 0.000333 m/s | 0.032620 m/s | 0.018056 m/s | 60.987 mm |
| 4 | BA | 0.000241 m/s | 0.000473 m/s | 0.050681 m/s | 0.050278 m/s | 61.840 mm |
| 5 | AB | 0.000349 m/s | 0.000392 m/s | 0.034816 m/s | 0.023982 m/s | 59.889 mm |

Aggregate observations:

- First-32 away-action fraction below `-0.01 m/s`: `0/256` for A and `0/256`
  for B.
- Unique current SAM candidate: `52/52` sampled post-handoff boundaries for
  each condition. This is tracker continuity, not physical identity proof.
- Mean first-32 projection: A `0.000388 m/s`, B `0.000452 m/s`.
- Mean full-window projection: A `0.036969 m/s`, B `0.037967 m/s`.
- Within-start full-window B-minus-A values: `+0.029790`, `-0.014564`,
  `-0.000403`, `-0.010834 m/s`; three of four are nonpositive.
- Mean post-handoff wall time: A `199.93 s`, B `201.24 s`.
- Evaluation-only task successes: A `0/4`, B `0/4`.
- Acquisition action RMS differences were `0.05094-0.08908`, so these are not
  matched pre-intervention trajectories despite identical initial
  proprioception within each pair.

## Decision

The bounded handoff-preservation question passes: the exploratory intervention
did not trigger immediate policy retreat, loss of all current target candidates,
or failure to complete the frozen policy exposure on any sampled start.

No task or causal benefit is established. The mean full-window difference is
small, its sign is inconsistent across starts, neither condition succeeds, and
the acquisition trajectories diverge before treatment. Stop repeating nearby
A/B handoff diagnostics. A useful next Phase 8 comparison requires a qualified
execution path and independent task progress, not more seeds of this same
unknown-clearance intervention.

Strict Phase 8 remains blocked by the Phase 5-7 clearance and execution gates.
Condition C remains unqualified.

## Evidence

Private immutable artifacts:

| Artifact | SHA-256 |
| --- | --- |
| Frozen protocol | `5b16733fb1f5968da4328df503ec032e4cf34d7356416361257234f68dc572e0` |
| Aggregate analyzer | `b643b79e60b4136b4f0a697a7e08b97f402fb563a80d8ec929d72a7a74ccf24b` |
| Remote aggregate result | `d5bbefec299d1dcc652d4665002d102e0183fd5819be44f12a57615e3fca7d43` |

The compact receipts for all four starts are retained locally. Reanalysis on
Apple and x86 hosts had identical structure and a maximum numeric difference of
`1.39e-17`, attributable to floating-point reduction order.

