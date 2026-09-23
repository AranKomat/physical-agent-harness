# Four-Velocity-Iteration Diagnostic

## Declared Scope

Run `base-drive-solver4-20260923-r1` tests one opt-in simulator-only physics
variant: articulation velocity solver iterations 1 -> 4, after ordinary setup.
The default remains unchanged. No mass, gains, friction, limits, codec, source
pin, abort checks or action-budget changes. Shared-host process priority 15 and
four-core affinity remain in effect. No paid calls or automatic retry.

The intended schedule was the same five holds / ten 0.005 m/s commands /
fifteen braking holds, conditional on five initial raw stopped samples. USD
articulation property readback confirmed 4; the internal native solver iteration
count was not independently measured. This is not a published benchmark recipe.

## Outcome: Preflight Failed

Only **five hold actions** completed. **No forward command was issued.** All
five raw stopped checks failed, and the diagnostic raised
`PermissionError: Initial five raw stopped samples required`. This attempt is
retained as incomplete, not scored as a completed pulse or silently retried.

Initial captured proprioception exactly equals the original one-iteration r2
baseline. Following holds, raw wrist velocity was approximately -0.02523,
-0.02610, -0.02220, -0.02330 and -0.01795 rad/s. The same baseline hold endpoints
were -0.00200, +0.00062, -0.00030, -0.00358 and -0.00478 rad/s.
Maximum wrist displacement from its initial value was 0.71 microrad; maximum
sampled evaluator-only planar base displacement was 1.192 micrometres. No
callback errors or raw abort were reported, but stop preflight did not pass.

More velocity iterations did not improve the bounded stationary stop readback
in this run. Because the pulse was censored by preflight, the result says
**nothing about the variant's commanded base-motion response**. It is not
adopted. Do not relax the gate to make this comparison complete.

Return to the original physics recipe for subsequent diagnostics. The unresolved
questions remain small-command physical response and a qualified observational
stop estimate; the failed variant does not establish a friction cause or a
universal simulator defect.

## Evidence And Verification

Receipt SHA-256:
`cc899695a0b62650a8cfe031e2e4343430663a0afb1af2a90b985e71bf61c10b`.
Environment and script hashes match before/after; saved script snapshots were
independently checked locally. The exception was persisted inside the evaluator
context despite Isaac's zero process exit code. Exit status is not success.

Full private suite: **1045 passed, one existing skip**. New tests preserve the
no-write default, restrict the explicit variant to 4, and require the expected
baseline before mutation. These are software checks, not physical qualification.
