# Phase 4A Discovery Prompt Comparison

## Result

Phase 4A is complete for its frozen four-view scope. The task-aware V3 delta
profile found the radio in both positive views and made no radio false positive.
The task-blind inventory profile found one of the two radios, made no radio false
positive, and covered substantially more of the frozen major room inventory.

| Metric | V3 delta | Task-blind inventory |
| --- | ---: | ---: |
| Strict packets | 3/4 | 4/4 semantic outputs |
| Radio recall | 2/2 | 1/2 |
| Radio false positives | 0/2 | 0/2 |
| Frozen primary categories covered | 4/24 | 20/24 |
| Reported semantic items | 6 | 48 |
| Manually supported inventory claims | Not rescored | 40/48 |
| Manually unsupported inventory claims | Not rescored | 8/48 |

The inventory's clear-view miss is concrete: at source index `15`, it localized
the red radio closely but labeled it `projector`. At clipped source index `10`, it
correctly returned `radio`. This supports task-aware V3 deltas for target-directed
historical discovery and task-blind inventory for slower, broader scene cataloging.
Neither profile should supply current geometry, physical identity, or motion
authority.

## Continuation Integrity

The first inventory attempt produced one valid response, then timed out on source
index `8`; source indices `10` and `15` were never dispatched. The continuation
was declared before its outputs and requested exactly `8`, `10`, and `15`.

- The original timeout and its full `$0.0102288` reservation remain unresolved.
- The replacement for index `8` is recorded as an independent declared request,
  not a silent retry.
- All three continuation calls used GLM 5.3 Flash through Together, low reasoning,
  strict structured output, no fallback, and no automatic retry.
- No robot action occurred.

All three continuation calls completed. Their combined latency was `25.9991 s`
and cost was `$0.00150325`. Across the four valid semantic outputs, completed-call
latency was `35.6432 s` and cost was `$0.00199450`. Transport accounting remains
five attempts, four valid packets, and one unresolved timeout.

The manual support review was not blinded and used one research-agent reviewer.
It separately records visible, unannotated claims such as floor and wall instead
of incorrectly treating every object absent from the limited major-object list as
a hallucination. Eight unsupported claims include the clear radio mislabeled as
a projector and robot grippers mislabeled as controllers.

## Decision

Use the bounded task-aware V3 delta profile for target-relevant asynchronous
discovery. Use task-blind inventory only as a lower-priority historical cataloging
job when broad room coverage is useful. GLM remains asynchronous: the valid calls
took `4.42--12.35 s` for V3 and `7.97--9.64 s` for the completed inventory calls,
well outside the two-second synchronous control gate.

Together with the completed Phase 4B context study, this closes Phase 4's frozen
scope. Compact V3 executive context remains the default. The result is not a
general perception benchmark and establishes no task success, persistent identity,
metric geometry, or motion qualification.

## Evidence

```text
frozen Phase 4A protocol
8bb49fb34d3e47352b54ab661b74fc398af32b34324a4478accdb6b66148e735

original partial inventory report
0045595278494c1d257c197c9b8566006cecdebeca5178bad872591da3140b40

continuation preregistration
8ed8507bfc58843d857baab2a830eeb3b35bd8619cde105d546da5f7e72da83b

continuation preflight
31665e0c326a5880186bf7bdcddb5fd2d48d2b7412e1f1492084073ccd8358c9

continuation report
cc8948fb2acee7dd62d7ed9cd46da6d619a1a6926ee35b3947bf981bba616516

manual review
152ac7cd12f35f30aec57e12fe628241e901e40e0e3f3d98e4ca1f5216dee10c

combined score
8e9776cd075020e934f2558972ff4ac393c2f0bd43b7d43e171b324d59f28948
```

After the continuation, campaign accounting is `4,206` cumulative calls,
`$23.96038742140` confirmed, `$34.979327322900` unresolved,
`$58.939714744300` total exposure, and `$16.060285255700` available under the
shared `$75` ceiling.
