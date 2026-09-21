# Tiny-Perturbation Handoff Diagnostic

Run: `hybrid-tiny-handoff-20260921-r1`. No GPT calls, training, target-coordinate
preloading, or task-specific checkpoint switching. This is not target-directed
staging and is not a completed radio benchmark comparison.

## Protocol and Results

Independent ordinary radio resets (instance 301, seed 0), frozen Behavior-Skill,
native preprocessing, full 23D actions, and 32-action policy prefixes. Both used
`Move to the radio receiver on the table.` B first executed the authorized
tiny forward pulse, settling and braking with clearance labeled **unknown**.
Strict collision gates were not changed or claimed satisfied.

| Measurement | A | B |
| --- | --- | --- |
| Policy actions | 384 | 384 |
| Total native actions | 384 | 409 |
| Policy chunks | 12 | 12 |
| Policy phase wall time | 71.03 s | 68.97 s |
| Protocol completed | Yes | Yes |
| Native task success, evaluation only | No | No |

B passed the bounded pulse/stop and last-five-capture head-motion checks before
the actual policy reset. Both runs used reset-relative sampling indices
`0, 32, ..., 352`. The policy server was reused, so A incurred initial compilation;
these wall times are not a controlled latency comparison.

Contact-sheet inspection shows broadly similar arm positioning and turning to
bring the radio into view. There is no obvious immediate handoff-induced retreat
or jitter in those sampled frames. B frames the radio more centrally at the end;
this does **not** establish better distance, contact, task progress or success.
One pair cannot establish robustness, and sampled frames can miss brief motion.

The narrow positive finding is that this tiny perturbation did not prevent a
normal-looking 384-action policy rollout. It does not validate a larger transit,
an arm intervention, a useful staging envelope, or improved task performance.

## Retention and Next Gate

All 313 source files were SHA-256 checked against the local backup with zero
mismatches. Recordings, sensor evidence, policy receipts and native logs remain
private. Both GPU workers were reaped after the pair.

Ordinary policy captures did not retain same-boundary intrinsics in this run.
Do not retrofit calibration and claim live target localization. The next runner
revision records calibration on every capture, including policy-only captures.
Next: a fresh calibrated approach, legal RGB/depth target measurement and a
no-motion staging diagnostic. Autonomous target selection, moving localization
and swept clearance remain separate qualification gates.
