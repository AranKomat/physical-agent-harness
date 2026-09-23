# Full-description candidate verification

## Experiment

Six independent retained-image GPT-6 Astra medium/Flex requests through the
existing guarded transport. Each receives one current crop and the complete
requested description with explicit category/color/subtype constraints. No SAM
scores, expected outcomes, prior conversation, simulator truth or future frames
are supplied. Existing manually inspected development crops are reused; this
does not test autonomous candidate generation or live integration.

The returned statuses are `matches`, `contradicts`, `unknown`, or `not_requested`
for each constraint. Local code requires all requested constraints to match;
any contradiction rejects, otherwise an unresolved constraint yields unknown.
A requested attribute cannot be omitted by returning `not_requested`.

| Candidate crop | Requested description | Result |
| --- | --- | --- |
| Radio, action 384 | `radio` | Match |
| Radio, action 448 | `a portable radio` | Match |
| Radio, action 512 | `a red portable radio` | Match |
| Same radio, action 384 | `blue radio` | Reject: color contradicts |
| Same radio, action 512 | `yellow radio` | Reject: color contradicts |
| Television control | `red radio` | Reject: color contradicts, category unknown |

The control result is not a confident television identification; it is sufficient
to reject the full requested description. Do not claim six perfect category
classifications or compare this task directly with SAM mask generation.

## Cost and audit

- Six completed calls, no retries or fallbacks: **$0.039415 total**.
- Observed per-call transport latency: **4.93-6.12 seconds**.
- $1 local cap; existing shared $75/4100 ceilings preserved.
- Shared calls: 4074/4100. Existing unresolved holds unchanged.
- Six reconstructed request-body hashes match stored transport receipts;
  image hashes, response JSON and locally derived decisions also match.
- Six focused decision tests pass; verifier and audit scripts pass Ruff.
- Private artifact: `candidate-description-gpt-20260922-r1` with preflight,
  transport receipts, journal, report and independent audit. Report SHA-256:
  `29135b4c34e214b390931e592f8f68e6c3624beefa1f1f33e78ef7d9ea179a59`.

## Consequences

This provides a small positive test of preserving the full target specification
while using candidate masks/crops. It does not qualify hard distractor selection,
ambiguous or relational descriptions, verifier calibration, or identity retention.
No task state, production defaults or motion authority changed.

Seconds of latency are suitable for occasional acquisition/ambiguity checks, not
per-frame robot feedback. Reuse of a positive semantic claim still requires a
qualified association to the same object; loss, reset or contradiction cannot
be bypassed by remembering a past match. Existing Situated Execution V2 identity
contracts already separate track IDs from semantic identity, so no new identity
architecture is needed. Next bind this verifier output to those contracts in a
retained end-to-end replay before a fresh live shadow experiment.
