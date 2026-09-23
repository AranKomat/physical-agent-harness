# Local visual verifier diagnostic

User update: **use GPT-6 Astra medium Flex as the verifier candidate**, not Qwen.
Qwen is retained only as a historical diagnostic. The GPT diagnostic uses the
same six saved-image claims with no Qwen answers or expected labels in its input.
Preflight reservation: $0.8656125 for six calls, within the shared $75 / 4,000-call
ledger, preserving every old unresolved hold. No retries or standard-tier fallback.
Verify sparsely at semantic boundaries, not on every frame or motor chunk.
Flex's latency/resource availability makes it unsuitable for emergency stopping.

## GPT-6 Flex result

Six calls completed with confirmed OpenAI Flex identity, no retries and no
standard-tier fallback. Total provider-reported cost: **$0.0721525**. Mean output
was 92.67 tokens and mean end-to-end time 5.30 seconds. Input cost includes reported
cache-write charges. All six raw judgments matched the development expectations;
GPT correctly rejected the floor claim that Qwen falsely accepted. It returned
uncertain for electrical on/off state and battery charge.

This selects GPT as the next verifier backend, not a universal qualification:
the same single scene underlies every case. Diagnostic gates remain conservative.
The calls evaluated saved observations; GPT did not control the concurrent
600-action rollout or feed live decisions back into it. The selected medium
reasoning setting was sent; the provider reported zero reasoning tokens on these
brief answers. Actual Flex latency can be much higher on other requests.

At the observed packet size, 10 similarly sized checks would be about $0.12 and
100 about $1.20, not guaranteed prices for larger images/prompts/reasoning. Use
one check at a semantic skill boundary or an uncertainty event, not every motor
chunk or frame. A model cannot determine an unobservable power state just by
being more capable; keep uncertain or request a better legal observation.

Private experiment artifacts include the immutable plan, results, and budget
ledger. The experiment-side entrypoint requires explicit execution, provider
identity checks, a shared ledger, and a local $2 ceiling. This run admitted
exactly six calls with $0.8656125 total reservations. All old holds were preserved.

Official references:
- https://developers.openai.com/api/docs/models/gpt-6-astra
- https://developers.openai.com/api/docs/guides/flex-processing

2026-09-18. Six claims on the same saved BEHAVIOR radio scene, using real
before/after head-camera RGB. This is a development diagnostic, not six
independent episodes or an accuracy estimate. Expected labels came from agent
visual review, not an independent human annotation exercise.

## Result

Qwen3-VL-4B-Instruct produced valid JSON in all six calls and matched five of the
six diagnostic expectations. Crucially, it falsely accepted "the radio is on the
floor, not the table" at 0.98 confidence while explaining that the radio was on
the glass table. Raising a confidence threshold would not fix this failure.

It recognized the red radio on the table and the blue sofa, and abstained on
electrical on/off state and battery charge. Head-camera pixels do not reliably
establish those hidden states. A visually absent indicator is not proof of off.

Decision: **not qualified to certify task completion**. This result establishes
a working local inference path and a real false-positive failure, not a ready
semantic verifier. No prompt was tuned after seeing this failure. We should test
an evidence-first relation extractor or stronger adjudicator on a broader set
before enabling completion; neither has been done here.

## Implementation and measurements

- `EvidenceVisualVerifier` binds images to the request's before/after evidence
  IDs. Positive/negative judgments require current after-image citations.
- `qualified=False` is the default. Raw judgments are logged, but effective
  verdicts stay uncertain and cannot complete tasks. Model confidence is not
  treated as calibrated accuracy.
- Caller must independently validate episode, timestamps and image hashes.
  The probe validates saved Observation schemas, episode ordering and content
  hashes through the existing EvidenceStore.
- Model: `Qwen/Qwen3-VL-4B-Instruct`, revision
  `ebb281ec70b05090aa6165b016eac8ec08e71b17`, Apache-2.0, public non-gated weights.
- Official Transformers processor defaults, original full-frame images, no
  custom crop. Transformers 4.57.6, PyTorch 2.7.0+cu128, BF16, SDPA, one RTX4090.
- Greedy output, 384-token cap; this diagnostic deliberately differs from the
  model card's recommended sampling defaults. No FlashAttention optimization.
- Load: 2.44 s; six-call median: 2.79 s; peak PyTorch allocated memory: 8.63 GiB.
  This is sparse-verification latency, not motor-control frequency.
- No paid API calls, physical actions, training or held-out task data used.

Source: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct/tree/ebb281ec70b05090aa6165b016eac8ec08e71b17

## Artifacts

The experiment script and detailed receipts remain in the private lab workspace.
Receipt `passed` refers only to runtime/schema completion, never calibration.
Attempt 001 failed before inference because the processor required structured
system-message content; it is preserved separately, not counted as model error.

The radio harness pilot continues to abstain. Native evaluator success remains
separate from policy-facing beliefs and is not used to make the verifier pass.
