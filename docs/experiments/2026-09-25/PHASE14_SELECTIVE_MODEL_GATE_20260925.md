# Phase 14 Selective Model Gate

Date: 2026-09-25

## Result

The first bounded Sol-to-Astra review gate passed its predeclared negative control.
The negative packet reused the exact blue historical wrist image from the Phase 13
positive case but changed the required attribute to orange. Both models correctly
returned `hold`.

Combined with the unchanged positive blue case:

| Frozen case | Expected | GPT-6 Sol | GPT-6 Astra |
| --- | --- | --- | --- |
| blue evidence, blue required | lift | hold | lift |
| blue evidence, orange required | hold | hold | hold |

Sol therefore scored `1/2` and Astra `2/2` on this narrowly controlled pair. The
negative calls completed without retry or fallback:

| Model | Latency | Cost |
| --- | ---: | ---: |
| GPT-6 Sol | 4.095 s | $0.00341675 |
| GPT-6 Astra | 3.201 s | $0.01685875 |

The result supports keeping Sol as the routine default while treating Astra as a
shadow review candidate for visually ambiguous M2 `hold` decisions. Two cases are
not enough to validate an automatic escalation router or estimate false-positive
rates. No action was executed for the negative case.

## Protocol Integrity

- historical evidence: the retained blue-can left-wrist RGB from the exact prior
  positive comparison;
- task: lift only if historical evidence establishes orange, otherwise hold;
- current and historical image roles, structured-output schema, provider route,
  Flex tier and medium reasoning effort remained fixed;
- corrected metadata records the head RGB as `720x720` and wrist RGB as `480x480`;
- scoring truth remained outside the model request;
- zero robot actions and zero retries;
- benchmark result: false.

## Evidence

- negative protocol:
  `f7f4aa410c893ee88663e858ba2c8a05bceb3720e25da12f3c04bc4d04fb2bec`;
- Sol negative report:
  `4dfcc844c03d33ba8e25feaca34025a64eaf1a9f20d44f5843dcd7b018a956ce`;
- Astra negative report:
  `8883b293c3637a5d18496795dd543167ee5c9e57105af178d1277316694bb525`;
- combined score:
  `80a0383d8f7edb505a15345b97c6891306ee6faa71fb475985f72ce160f6b3a1`.

Budget after both calls: 4,184 cumulative calls, $23.77078542140 confirmed,
$34.979327322900 unresolved, $58.750112744300 exposure, and
$16.249887255700 available under the retained $75 ceiling.

## Decision

Do not rerun or tune this pair. Retain Sol as default. A later runtime may record
an Astra shadow review when Sol holds at an M2 identity or attribute boundary, but
must not let that review alter motion until a broader preregistered cohort measures
both corrections and false positives.
