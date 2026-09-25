# Phase 13 One-Can Ashcan Visual Verification

## Result

A frozen post-action verifier evaluated the retained legal left-wrist images from
the successful one-can ashcan deposit. GPT-6 Sol Flex returned `verified` with
confidence `0.97`, cited all three supplied post-action evidence IDs, and stated:

> The orange soda can is visible inside the wastebasket after release and remains
> visible there in the retreat and settled views.

The preregistered rule required the post-settle evidence ID plus at least one
earlier post-release or post-retreat ID. Sol cited post-release, post-retreat, and
post-settle. Every citation was supplied legal evidence, so the response passed
both citation and temporal-support checks. Astra review was not triggered.

| Measurement | Result |
| --- | ---: |
| Sol calls | 1 |
| Astra calls | 0 |
| New robot actions | 0 |
| Prompt / completion tokens | 1,318 / 172 |
| Actual cost | `$0.00250675` |
| Wall latency | 4.785 s |
| Verdict | `verified` |
| Confidence | 0.97 |
| Supported citations | yes |
| Native evaluator agreement | yes |

The model saw no simulator object pose, native `Inside` predicate, task-progress
state, or evaluator result. Those quarantined values were loaded only after model
dispatch for scoring. They independently agreed that release passed, the can was
inside after settling, the relation remained stable, and exactly one of the three
required cans was inside the ashcan.

## Frozen Protocol

The verifier received only three chronological, content-addressed images from the
same legal left-wrist camera:

```text
post_release  0455ea75789f78f3e938ec4a5f4b2d1664590725adae1e6e91736832aeece248
post_retreat  85f7f55719b38f34631b73327925b9883af667546e53ea1808a682633c9cc36b
post_settle   8d10464a21db644c563b6316581da49f7071a63dc0ce863b4670a9d2c6abfb05
```

The frozen claim was:

> A soda can is visibly resting inside the wastebasket after release and remains
> there after the robot retreats and the scene settles.

Sol medium Flex ran first. Astra medium Flex could run once only when Sol failed to
produce a supported `verified` verdict. Neither model had motion authority, no
provider fallback or retry was allowed, and the maximum two-call reservation was
`$0.17`. Sol's passing result ended the protocol after one call.

## Evidence

```text
preregistration
e262287c07952f67fcf10aff2784b327718dbb4f4211e57f38346dcd66f0bf05

runner
c81a8ba633c7de6b49c72d075e28b7f6719b60e7a50736f4703fd0b282b30571

focused tests
3b320bdb6b79bd41ef36aeb90866bff679591329ae691fb7b190d9617b3d5e1a

preflight
3fafb2015965ea8ca588796d73d577397e658308e168da917d1ab3af8e9ab417

Sol plan / Sol report / final report
44d3c92635de2e18685e6fca85a7026e5f780a528fed1b478b67cb3c9a1de5c0
ab831eb8f82d32963dcceacbb15734f428dde4394f0122a9206ad81d0be4dec5
4651281c4cb80c080df832c474a9748850d23c1ed7c2e491a0fd35024c5e2f4f
```

The five focused verifier tests passed and Ruff passed. The shared campaign ledger
settled call 4,208 with 150 prior unresolved holds retained. Total exposure after
the call was `$58.950586494300` under the unchanged `$75` ceiling.

## Interpretation

This closes the previously pending model-based visual check for the retained
one-can deposit. It provides one integrated example of a semantically useful
physical effect followed by a legal-evidence, structured, citation-checked model
verdict that agrees with independent evaluator truth.

It does not qualify general verification, autonomous destination selection,
Action Compiler execution, strict clearance, complete `picking_up_trash` success,
or a BEHAVIOR benchmark result. The source fixture scripted robot, can, and ashcan
initialization before the first legal observation; motion remained exploratory and
external clearance remained unknown.
