# Phase 4B Rich Versus Compact Executive Context

## Result

Phase 4B passes its frozen four-boundary scope. All eight GPT-6 Sol Flex calls
completed without retry or provider fallback, produced schema-valid decisions,
and matched the preregistered accepted actions.

```text
frozen protocol:
7aca6b0ecd577c31dd7e72cb2c8eeb05191f930441fd0e03a3cd4aed3a38ecfc

completed transport report:
09c6fcb135fb83e8c96a586962b7a74db6e2ce5074fdecfd0685e8f42e2661d9

score:
5c833a4f7f239bb8231854f34d03b6326d3c242c58fdacce2cf16573a63101d3
```

The run sent zero robot actions. Total model cost was `$0.03403650` under the
approved `$0.40` local cap. The cumulative ledger reached the approved 4,159-call
ceiling with the shared `$75` ceiling and all prior unresolved holds retained.

## Decisions

| Sequence | Rich | Compact | Accepted |
| ---: | --- | --- | --- |
| 0 | `approach_table_radio` | `approach_table_radio` | Yes / yes |
| 384 | `approach_table_radio` | `approach_table_radio` | Yes / yes |
| 768 | `press_radio` | `press_radio` | Yes / yes |
| 3072 | Retrieve unobstructed power/control evidence | Retrieve unobstructed power/control evidence | Yes / yes |

At sequence 3072, both profiles rejected a seventh blind press. Compact explicitly
cited six verified presses with uncertain outcomes; rich cited repeated presses
that had not established power state. Both requested a fresh, unobstructed view of
the power control/display/indicator. This passes the preregistered critical-history
test rather than merely matching an option ID.

## Efficiency

| Metric | Rich | Compact | Compact change |
| --- | ---: | ---: | ---: |
| Prompt tokens | 12,503 | 10,087 | -2,416 (-19.3%) |
| Completion tokens | 518 | 643 | +125 |
| Reasoning tokens | 207 | 316 | +109 |
| Mean latency | 6.324 s | 5.151 s | -1.173 s |
| Median latency | 5.461 s | 5.198 s | -0.262 s |
| Cost | $0.01821575 | $0.01582075 | -$0.002395 (-13.1%) |
| Accepted decisions | 4/4 | 4/4 | No delta |

Each profile received the same 3,916,800 source-image pixels. No prompt tokens
were served from cache. Compact used more output/reasoning tokens on this tiny
cohort, mostly because its late retrieval response was more explicit, but still
reduced total cost and latency.

## Decision

Use **compact V3 context** by default for the next live GPT executive trial.
Retain rich context as the controlled comparator and preserve the frozen prompt;
do not interpret this result as evidence that compact context is universally
equivalent.

This completes Phase 4B, not all of Phase 4. Phase 4A remains partial because its
task-blind inventory cohort had one valid completion, one unresolved timeout and
two unsent calls. This trace also does not establish task success, motor-policy
quality, episode generalization or live causal benefit.
