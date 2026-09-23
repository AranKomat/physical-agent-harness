# GPT-6 Sol Default And Optional Luna Comparison

User requested GPT-6 Sol Flex for future experiments in place of Astra, plus
occasional Luna Flex comparisons. Sol is now the active matched-radio model and
GPT verifier metadata default. Luna is selectable explicitly, not an automatic
fallback. GLM remains the existing discovery candidate pending matched evidence.

## Verified Metadata, Not Inference

Official model pages were opened on 2026-09-23:

- https://developers.openai.com/api/docs/models/gpt-6-sol
- https://developers.openai.com/api/docs/models/gpt-6-luna

Both document image input, structured outputs, medium reasoning and Flex at
50% of standard token rates. Unauthenticated OpenRouter endpoint queries also
returned the corresponding `openai/flex` routes with status 0 and these prices:

| Model | Input / million | Output / million | Cache write / million |
| --- | ---: | ---: | ---: |
| GPT-6 Sol Flex | $1.00 | $5.00 | $1.25 |
| GPT-6 Luna Flex | $0.05 | $0.25 | $0.0625 |

These are ordinary-context rates; published overrides apply above 272,000 input
tokens. Existing experiment packet bounds remain below that threshold. Pricing
and availability must still pass fresh endpoint checks at dispatch. No paid
inference was performed to establish account access, latency or robotics quality.

## Changes And Controls

The public model configuration pairs each explicit model with its expected
prices. Historical Astra remains available explicitly with its existing cohort
prices; saved results and fixtures were not relabeled. The matched-radio example
uses Sol. The private executive, semantic verifier, memory-QA and discovery
entry points now use Sol, retaining Flex-only routing, structured schemas,
medium reasoning, request limits and no automatic fallback/retry.

Private memory-QA resume requires the same recorded model cohort, not merely
matching prices. Start a fresh run for Sol; do not append to an Astra run.
All existing approval flags, cumulative ceilings, local caps and unresolved
holds remain unchanged. A model preference is not an extension of the call
budget. The 12-call Sol/Luna inventory comparison budget has been requested,
not treated as approved by this change.

Validation: full public suite **1,489 passed**; full private suite **818 passed,
one existing skip**. Public Ruff and changed private modules/tests pass. Tests
use fake transports; they establish configuration/accounting behavior, not model
quality. Private import formatting left by consolidation was normalized in the
touched entry points; no prompt, action gate or simulator behavior changed.
Changed runtime files were also synchronized to the current GPU host with
backups of previous versions. A remote CPU import smoke confirms Sol transport
defaults and explicit Luna configuration; this does not invoke either model.

## Next Comparison

Use the six frozen blind-inventory views already used by GLM, identical pixels,
the same 12-object prompt, native pixel-coordinate schema and output cap. Run
Sol and Luna as separate cohorts, with the same reasoning effort as the retained
GLM baseline. Score visible-object coverage, duplicates/hallucinations, box
localization, uncertain objects, schema validity, latency and actual billed cost.
Compare semantic identification separately from precise localization. This is
retained-image discovery, not online identity tracking or task success, and the
historical GLM timing is not a contemporaneous provider-speed control. Do not
select a robotics model from general language benchmark rankings alone.

### Frozen Preparation

The 12 matched requests are now prepared locally in
`internal/physical-ai-lab/runs/sol-luna-inventory-inputs-20260923-r1`.
Sequences are 0,288,352,384,512,768; Sol-first/Luna-first ordering alternates
across views. Exact original image bytes, messages, schema and the low reasoning
effort used by GLM are retained; only model/provider/Flex routing differs.
The 50,000-input / 2,048-output bound includes cache-write rates and 20% price
headroom, giving a total estimate of **$0.5499144**, not a billing reservation.

The preparation tool has no execution, network, credential or ledger access.
All source hashes remained unchanged; 14 focused synthetic tests pass. Approval
is recorded as pending and no calls were sent. Frozen plan SHA-256:
`52b328a659dd097ac3c4acceca34dd44f95e2a6f35c61339adc9f4603a64d6dd`.
