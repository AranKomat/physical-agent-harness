# Phase 14 Second Prospective Selective Review

Date: 2026-09-25

## Result

The preregistered Sol-first, Astra-on-hold rule passed a second prospective
shadow cohort derived from a new physical source run. GPT-6 Sol made all four
category decisions correctly. Astra reviewed three correct Sol holds and
preserved all three, producing zero false corrections.

The source was `strawberry.n.01_2` in the official `freeze_fruit` task at seed
31. A corrected source runner completed 30/30 native actions and required both
the intended semantic decision and an evaluator-confirmed physical effect.
Evaluator-only scoring measured a 50.007 mm lift. Independent legal RGB-D plus
robot-only forward kinematics measured a 50.008 mm lift; the retained red
surface had mask IoU 0.98375 and only 0.0091 mm median depth change.

Four M2 packets were frozen before inference. They used the same source evidence
and varied only the required category:

| Required category | Expected | Sol | Astra review | Selective result |
| --- | --- | --- | --- | --- |
| Strawberry | lift | lift | not triggered | correct lift |
| Apple | hold | hold | hold | correct hold |
| Peach | hold | hold | hold | correct hold |
| Tennis ball | hold | hold | hold | correct hold |

| Profile | Correct | Calls | Astra calls | Sequential latency | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| All Sol | 4/4 | 4 | 0 | 16.830 s | `$0.01369825` |
| Selective review | 4/4 | 7 | 3 | 26.857 s | `$0.06278075` |

All calls used medium reasoning, strict structured output, OpenAI Flex routing,
no provider fallback, and no retry. The model outputs remained shadow-only and
authorized no robot motion.

Combined with the first prospective strawberry pair, Sol and selective review
both score 6/6 across six controlled decisions. Astra has now reviewed four
correct Sol holds without changing any of them. The earlier frozen blue case
remains the only observed Astra correction of a Sol error.

## Guard And Runner Fixes

The first launch stopped before reservation or network access because the shared
ledger's explicit call-ceiling allowlist ended at 4,195. The failed preflight was
retained, the authorized 4,202 ceiling was added to the allowlist, and its 20
budget-ledger regression tests passed before the fresh launch. This accounting
guard was extended rather than bypassed.

The source campaign also exposed and fixed a correctness issue before this
cohort: the development grasp/lift runner had treated action completion as a
passing result even when the evaluator found no physical effect. The corrected
runner requires both `evaluator_effect_passed=true` and the expected semantic
decision. The protocol builder independently enforces the same evidence. The
failed tennis-ball run remains immutable negative evidence and was rejected as
a protocol source.

## Evidence

- source receipt: `0a62b314d0405c4827a15054a252ac93c80245003f0cd68e1a79a21cd6d5bcd4`;
- evaluator sidecar: `59fc246fb198a6550e875f751fc2981c711c794131bc95709217613188edc13c`;
- legal visual verification: `498e60863954ff9cd171233ba9790895278501ccd18789a37b26a9f5a73aef6d`;
- preregistration: `6adacd8a7ecb9737cddf8c4f4e24d4eee89b3f0743909da958e2f86deb45da13`;
- coordinator: `73548e95a3b4d5b9c24eac0bfa3e97fe62fca0783c6ae8431b878cc496942532`;
- final score: `1dd8783311a71e723c51b6f9532d745835f140991bcb5b449ad2110f094a0094`.

Protocol file hashes for strawberry, apple, peach, and tennis ball were,
respectively:

- `b60b5bf4c3dd7ed0defcbbeb5e880dc718c21a9a38aea35c2740665896b47377`;
- `2416101865c8a9d035c70166676b5304f4fc431c5f9f0e30f18747a025b6d911`;
- `9025a50dca9f6bf3a236269ecec816454ae929d0483ae2f160051acfee2aef4e`;
- `f0b3b7a22170e22f63b73d7befc7dc76088fabc92018e3debdbfa4c46cd3c761`.

The calls ended at 4,201 cumulative requests with `$23.93998367140`
confirmed, `$34.979327322900` unresolved, `$58.919310994300` exposure, and
`$16.080689005700` available under the unchanged `$75` ceiling.

## Interpretation And Next Gate

This strengthens the evidence that Astra can review a Sol abstention without
reflexively converting it into action. It does not demonstrate a new
prospective Astra correction, natural uncertainty, or automatic-review safety.
All six prospective cases remain controlled category questions from two scripted
development fixtures.

Keep Sol as the default and Astra available for consequential, visually
ambiguous M2 decisions. The next useful comparison should come from a natural
M2 hold or a fresh Sol error, not another counterfactual category prompt over
the same images. Automatic Astra motion authority remains unjustified.

This is not benchmark task success. Source initialization was scripted,
external clearance remained unknown, and `motion_qualified=false`.
