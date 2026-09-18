# Closed Semantic Boundary

`HarnessRuntime` supports the minimum ordered loop needed for a meaningful
physical-agent boundary:

```text
motor skill
  -> after_observer(request, receipt)
  -> fresh legal evidence and world/entity update
  -> VerificationRouter
  -> on_verified(request, receipt, verification)
  -> task ledger update
  -> SKILL_VERIFIED event
  -> next executive decision
```

Configure `after_observer` only with a callback that captures a fresh legal
post-action observation, runs the perception/world update and returns its
nonempty evidence-ID tuple. A command, policy completion flag or native score is
not an after-observation. The verifier's evidence validator remains responsible
for episode, origin and freshness checks.

`on_verified` runs only after a `VERIFIED` result. It may call
`TaskLedger.set_status(..., "observed_complete", evidence_id, now=...)`, whose
existing checks require fresh observational beliefs matching explicit task
bindings. The runtime publishes `SKILL_VERIFIED` only after that callback
succeeds. `REJECTED` and `UNCERTAIN` results cannot invoke it.

The optional `before_evidence_ids` argument binds a comparison packet to the
pre-action boundary. GPT-6 remains sparse: invoke it at this semantic boundary,
not per frame, motor chunk or control step.

The deterministic unit test exercises this order with the radio predicate. A
live autonomous cycle still requires native BEHAVIOR artifact loading, the live
world/relation service and GPT-6 transport; no offline test claims those external
components ran.
