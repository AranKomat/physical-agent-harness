# Phase 4B Frozen Executive-Context Protocol

## Status

The rich-versus-compact protocol is frozen before model output. Preparation made
zero model calls and sent zero robot actions. Phase 4B is ready for an explicitly
approved eight-call GPT-6 Sol Flex cohort; it is not yet complete.

```text
source supervisor trace:
768d4c27cefb2fb337116f1588e98e3658ac2dab111678834dd8679c571eadc8

source radio protocol:
544fe8be8d332872947862eebc843754ff39fb3c825d0d9425dd736180d2e58b

frozen Phase 4B protocol:
7aca6b0ecd577c31dd7e72cb2c8eeb05191f930441fd0e03a3cd4aed3a38ecfc
```

All 12 current source images were resolved from the retained evidence store and
verified against their content-addressed filenames and PNG dimensions.

## Boundaries

| Sequence | Frozen causal state | Preferred reference decision |
| ---: | --- | --- |
| 0 | No prior attempt; target not confirmed reachable | `approach_table_radio` |
| 384 | One approach verified; radio remains away from both grippers | `approach_table_radio` |
| 768 | Two approaches verified; target appears reachable | `press_radio` |
| 3072 | Six press attempts all returned `uncertain` | Reposition, stop, or request useful fresh evidence; never another blind press |

The final boundary is the critical failure-history test. Its compact packet
explicitly preserves two approach attempts, six press attempts, six uncertain
power outcomes, zero unsafe verifier outcomes and the latest verifier reason.

## Matched Conditions

Both conditions receive the same goal, seven-skill menu, physical and causal
constraints, three current legal camera images and underlying history through the
boundary.

- **Rich:** raw 61-value R1Pro proprioception plus every prior executive and
  verifier record in chronological order.
- **Compact:** named R1Pro state fields, velocity norms, grouped skill-attempt and
  verifier-outcome counts, and the latest verification.

The call order is counterbalanced:

```text
0 rich, 0 compact,
384 compact, 384 rich,
768 rich, 768 compact,
3072 compact, 3072 rich
```

The model is not told the condition label. Source images are byte-identical
within each boundary.

## Transport And Scoring

The frozen transport is GPT-6 Sol through OpenRouter's OpenAI Flex route, medium
reasoning, strict structured output, a 30,000-token input reservation bound and a
512-token output cap. Provider fallback and automatic retry are disabled.

Primary scoring covers accepted decisions, invalid options and use of the late
repeated-failure evidence. Secondary scoring covers retrieval/hold behavior,
input/cached/output/reasoning tokens, image pixels, latency and cost. Reasons
remain subject to source-grounded review; accepted decisions cannot be changed
after outputs.

The conservative reservation is `$0.048072` per call and `$0.384576` total when
the higher cache-write input rate is used. Dispatch remains gated on an explicit
`$0.40` local cap, cumulative call ceiling 4,159, the existing `$75` shared
ceiling and retention of every unresolved hold.

Focused preparation and transport-contract checks pass `6/6`. This comparison
measures frozen executive decision quality and context cost. It does not establish
task success, motor-policy quality, episode generalization or live causal benefit.
