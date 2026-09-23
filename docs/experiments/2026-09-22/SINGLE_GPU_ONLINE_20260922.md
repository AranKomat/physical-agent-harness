# Single-GPU Online Integration

## Separate-Service Preflight

The normal private hybrid launcher now accepts explicit native/policy device,
deployment, data and tokenizer-cache paths, retaining its old two-GPU defaults.
A mutually exclusive no-motion preflight uses the same policy and grounding RPC
servers as moving trials. It rejects movement options and non-frozen grounding
prompts, captures fresh native RGB-D/calibration, validates response bindings,
and never applies a returned policy chunk.

Pinned RPent RPC source and hashed robot-only self-filter assets were restored.
The restored FK implementation passes its proprioception convention check on a
retained native observation. The online grounding service includes that filter
and passes the existing complete configuration-identity validation; this is no
longer the reduced shared-worker capacity test.

`single4090-rpc-preflight-20260922-r1` passed three fresh paused cycles with both
models and simulator on GPU0, driver 580.178.04. Maximum sampled global VRAM was
20,718 MiB. Cold policy inference took 19.441 s; warm calls took 98.66/97.28 ms.
Full grounding calls took 978/820/754 ms, and capture took 414-462 ms. These are
different workers/configuration from the earlier capacity probe; do not attribute
the grounding difference solely to GPU contention. No actions or GPT calls were
made. All workers exited and the GPU process query was empty.

## Concurrent CPU Audit

While the GPU ran, a retained-evidence metric-chain audit processed all 25
captures of `grounding-radio-extended-20260922-r1/A`, including 12 accepted
targets. It verifies RGB-D identity hashes, same-boundary calibration, complete
grounding configuration, mask hashes/source bindings, support counts, robot FK
against proprioception, and recomputes the detector's camera/base-frame medians.

All 25 FK/proprioception checks passed. Camera medians reproduced exactly; the
largest base-coordinate numerical discrepancy was 4.45e-16 m. This checks
implementation/lineage, **not semantic truth or physical localization accuracy**.

Across the 12 accepted masks, the central 90% depth span ranged from 0.068 to
0.540 m (median 0.110 m). The masks describe visible object surfaces, not a
qualified button/contact target. No mask was modified, selected for a better
fit, or substituted into runtime. Cross-view position invariance cannot be
inferred from instantaneous robot-frame coordinates during motion.

The older three-reset audit was refused at the first capture because its
historical identity lacks the now-required `files_sha256` field. Those receipts
were not rewritten and the check was not relaxed; no additional audited pass is
claimed. The omission does not itself prove the old files differed.

Twenty-five focused private regression tests pass for launcher mode isolation,
device arguments, paused-world checks, policy reply validation and masked-depth
math. This does not replace live motion/clearance qualification.

## Fresh Short Acquisition

`single4090-grounding-motion-20260922-r1` completed an ordinary seed-1 radio
reset, exactly 384 Behavior-Skill actions and 13 synchronous grounding captures.
No classical actions, GPT calls, memory intervention or threshold changes.
Maximum sampled global memory was 20,638 MiB; workers were reaped successfully.
This is a data-collection pass, **not task success** (native success was false).

All 13 head views were inspected. The radio was absent from the first 12 views
and partially clipped at the lower-left edge in the final view. No radio target
was accepted; the clipped view was missed. Eight near-hand ambiguous candidates
were rejected. This is limited policy acquisition plus an edge-view detector
miss, not evidence that a well-framed radio was consistently ignored. No accepted
false target was observed in this small trace.

All 13 fresh calibration/evidence and FK/proprioception checks passed, as did
derived-mask hashes and causal delivery checks. The full source run, including
video and RGB-D, is local; checksum comparison found no source-file differences.

| Timing | Single 4090 | Earlier dual-4090 seed-1 short run |
| --- | ---: | ---: |
| First-to-last capture, 384 actions | 114.30 s | 65.88 s |
| Actions/s after first 32-action chunk | 4.23 | 5.79 |

The new cold inference was 18.56 s, warm policy median 98.26 ms and grounding
median 757.80 ms. The older seed-1 run reused a policy process warmed by seed 0;
the full elapsed ratio therefore exaggerates a steady-state comparison. Excluding
the first chunk, observed throughput was about 27% lower (37% more time per
action). Neither comparison controls driver/runtime or divergent trajectory;
do not attribute the entire difference to sharing a GPU. The full loop is more
noticeably slower than policy-only timing, but ran without OOM.

A separate fixed 768-action acquisition follow-up was selected before its run,
with the same ordinary seed-1 reset and frozen interfaces. This is not an A/B
intervention comparison or permission to keep extending until a favorable result.

## Extended Acquisition Result

`single4090-grounding-extended-20260922-r1` completed exactly 768 policy actions
and 25 captures, no classical actions/GPT calls, with all workers reaped. Peak
sampled global memory was 20,634 MiB. First-to-last capture elapsed 232.98 s;
warm policy median was 99.73 ms and grounding median 752.66 ms.

There were 12 accepted radio captures at sequences 384-768, with a gap at 704.
The final 13 head views were visually inspected: radio acquisition and approach
are visible; at 704 the radio remains visible despite no candidate. This is not
continuous tracking or a calibrated accuracy estimate. Seven earlier near-hand
ambiguous candidates were rejected. The measured horizontal robot-to-partial-
surface distance decreased from 1.744 to 1.034 m; viewpoint-dependent partial
surfaces are not a measured 0.710 m base displacement or a world-map guarantee.

All 25 evidence/calibration/FK and causal delivery checks pass. Recomputed camera
medians exactly match and base-coordinate discrepancies are at most 3.34e-16 m.
The complete video/RGB-D source run is local and source-file checksums match.
Native receipt SHA-256:
`2f140765ecba48ff9664b8fcd64d54a3c4ea71df07880bf7466a11ae56b03c49`.

Native task success remained false. Both new runs used an approach instruction,
not a full power-on protocol; do not score them as full-policy task-completion
attempts. Because these are independent natural resets, the longer run's already
different view at 384 prevents attributing its better acquisition solely to
extra exposure. Both results are retained; no checkpoint or detector was tuned.

## Next Gate

The normal single-GPU online stack is operational. Stop repeating migration
preflights or extending acquisition indefinitely. Use these fresh calibrated
positive/negative views for stage 3 target/part consistency, while stage 4
moving localization, stop interpretation and low-space clearance remain separate
unqualified requirements. A new classical B intervention, arm staging, contact
primitive or GPT selector is not admitted by these policy-only traces.

Independent CPU audit and test work ran during GPU initialization/rollouts.
Native jobs were serialized to avoid two simulators competing for 24 GiB.
