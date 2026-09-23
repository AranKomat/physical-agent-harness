# Phase 0/1: Retained Discovery To Compact Context

Date: 2026-09-23. Starting commit: `4aa1b47`. The public corrections and
regressions accompanying this report are part of the tested working tree.
The replay protocol records every runtime Python-file hash, the private runner
hash and source hashes before execution; it verifies they remain unchanged.

## Result

**The corrected retained-data Phase 1 experiment passes: 64 checks, six saved
GLM packets, all 67 object proposals preserved.** Sixteen deliberate rejection
cases were refused. This is causal software integration on real retained pixels
and model responses, not a new model-quality or live robot experiment.

No paid requests, GPU inference, simulator actions, new policy trials or motion
gate changes occurred. The fresh baseline software preflight passed. Remaining
GPU provisioning, model-version and timing gaps are listed below rather than
counted as completed live preflight.

## Phase 0 Evidence Audit

An independent private audit completed 641 checks with no failed comparisons:

- All 25 exported source images match the decoded native RGB pixels. Lossless
  reencoding changes PNG bytes; it does not change image pixels.
- The six actual submitted API image payloads match their retained PNG bytes.
  Saved request hashes, request IDs, image associations and report/response
  correspondence pass checks. All 67 original objects remain available.
- Retained SAM mask artifacts and their source associations were audited as
  available inputs, not rerun or promoted to physical identity evidence.
- Campaign accounting was read without alteration: 4,127 calls, 148 unresolved
  reservations, $23.61798139640 confirmed and $34.955225022900 held, for
  $58.573206419300 exposure. The count ceiling remains 4,127 and the dollar
  ceiling $75. This snapshot grants no new paid calls or retries.
- Private source manifests replace a nonexistent private Git revision. Provider
  model alias/configuration are recorded, but no immutable GLM weight revision
  was supplied by the endpoint. Newly computed response-file hashes are not
  retrospectively claimed to be historical hash commitments.

The current host was independently checked: idle RTX 4090, driver 580.95.05,
Python 3.11.16, approximately 407 GiB free. It has the CPU code environment but
not restored SAM/model/simulator environments. Official SAM 3.1 checkpoint
access without login returned HTTP 401; credentials were neither printed nor
copied. The instance was not stopped, restarted or destroyed.

## Frozen Inputs And Conversion

Private inputs under `internal/physical-ai-lab/runs`:

- `glm-blind-inventory-20260923-r1`: six accepted inventory outputs, requests
  and raw responses, for source sequences 0, 288, 352, 384, 512 and 768.
- `glm-view-inputs-20260923-r1`: API images and source-reference manifest.
- `sam31-live-fusion-20260922-r1/stack/A`: original native capture receipt,
  calibration/proprioception records and content-addressed RGB images.

The adapter checks native PNG hashes/pixels, API payload bytes, request-body
hashes, response text and raw response content, observation stamps and source IDs.
Integer xyxy coordinates are divided separately by recorded width and height.
No box is clipped, rescaled by guessed units or repaired from a known target.

Descriptions and category strings are retained. V3-only fields use explicit
adapter defaults: `sighting` retention, zero utility hints, no baseline attention,
no known-ID association and an empty scene summary. A model's clear category is
still only a semantic interpretation, never physical identity or task truth.
Requests explicitly allow twelve updates so the original inventories are not
silently truncated to the default four-update delta limit.

The original calls did not generate V3 deltas. This experiment does **not** test
the new delta prompt or infer model-chosen relevance from these adapter defaults.

## Clock Scope

The captures record native monotonic `observed_at` and source sequence, but not
native simulation time or the GLM result's local availability timestamp. Provider
`created` and fusion-ready times cannot fill those missing fields.

Replay therefore uses a distinct `fixture` episode namespace. Its `sim_time`
field holds the source sequence as an **ordering clock only**, not simulator
seconds. Capture-wall references retain recorded observation times; controlled
delivery times are declared replay inputs. This establishes causal contract
behavior under an explicit schedule, not reconstructed live latency or native
timestamp qualification. No catalog contains an executable action.

## Exercised Paths

| Path/case | Result |
| --- | --- |
| Saved inventory -> strict parser -> actual async worker -> coordinator -> inventory | Six packets accepted; 67 historical sightings; no baseline attention invented |
| Inventory -> delta projection -> compact context | Source-bound sighting IDs, historical authority and availability preserved |
| Historical contexts after later arrivals | Earlier packet fingerprint unchanged; future records excluded |
| Out-of-order delivery | Older observations published only at actual replay receipt time; earlier cutoffs remain empty |
| Old-task versus current-task attention | Both archive semantics; only current-task injected attention wakes the scheduler |
| Future source / future completion | Independently rejected; no inventory or pending event produced |
| Late completion | Both direct inventory rejection and async terminal-timeout receipt checked; no published semantic result |
| Duplicate / reserved request | Refused, including after durable journal reopen |
| Undelivered terminal result after restart | Recovered once from journal, without reinvoking the callback/provider |
| Cross-frame region, unknown known-ID, extra action field, wrong fingerprint | Rejected rather than repaired |
| Valid known-ID suggestion | Remains a hypothesis; an existing current identity cannot be linked without separate association proof |
| Retention/demotion | Baseline 4 hot, 8 warm, 55 cold records; no evidence deletion. Separate injected retain/focus/ignore/aggregate and pin/unpin cases pass |
| Crop lineage | All 67 generated crops exactly match their original integer-pixel ROIs; parent/content hashes retained |
| Compact budgets | Explicit optional omissions; held-state uncertainty, constraints, failures, mandatory evidence policy and current facts survive |
| Oversized critical metadata | Fails rather than truncating required information |
| Token budget | Injected counter success/overflow paths pass; no model-specific tokenizer/image-token estimate available |
| Identity time direction | Historical semantics do not refresh geometry; future/foreign latest identity state is refused |
| World/task authority | World database unchanged and task remains planned; no discovery-driven physical identity promotion |

The private report includes the six generated compact-context hashes and all
individual check outcomes. Retention, attention and identity perturbations are
explicit contract tests, not additional semantic-model outputs. The positive
current-identity fixture used to test failed association is kept in a separate
journal and does not qualify actual physical geometry.

## Three Confirmed Bugs Fixed

1. `focus_identity_view` returned the latest canonical/conflict semantics after
   a failed current binding, even for a cutoff before those observations. It now
   rejects future/foreign latest state before historical fallback. It deliberately
   does not invent a historical identity snapshot. The identity schema still lacks
   publication timestamps; delayed-claim availability needs qualification before
   using this projection for arbitrary historical asynchronous results.
2. `crop_source` could expand integer-origin ROIs by a pixel after normalized
   division/multiplication. Fourteen of the 67 saved boxes exposed this. Products
   within two floating-point ULPs of an integer now recover that integer before
   conservative floor/ceil; genuinely fractional edges remain conservative.
3. Compact context previously admitted optional items without reserving later
   omission-ID metadata. It could then reject a packet whose required state
   would fit. Selection now accounts for the entire omission list before optional
   admission, skips oversized optional items, preserves deterministic ordering and
   fails if required state plus explicit omissions cannot fit.

Twenty new public regressions cover these fixes. No collision, stopping, identity
association or stale-action threshold was weakened.

## Superseded Development Replays

`v3-retained-discovery-20260923-r1` and `r2` passed narrower checks that missed
the future-identity, exact original-ROI and byte-boundary issues. They are retained
but are not final Phase 1 pass evidence. The directory named
`r3-before-fixes` was run while the corrections were being developed; that name
does not prove it used the old code. It is also development-only evidence.

The authoritative frozen run is **`v3-retained-discovery-20260923-r4`**, which
checks source and runtime hashes before/after execution. The independent auditor's
initial path-error attempt is retained separately; no source data were changed.

## Verification And Next Work

- Full public software validator: **1,471 tests**, Ruff and five synthetic CLIs.
- Private suite: **581 passed, one existing skip** at this validation snapshot.
- Linux follow-up: **194 embodied tests passed** against the synchronized fixes.
- Private new coverage: twelve replay-adapter tests and six evidence-audit tests.
- Repository ownership/link and whitespace checks pass.

Private runner: `scripts/replay_v3_discovery.py`. From the parent workspace:

```sh
env PYTHONPATH=physical_agent_harness_scaffold \
  internal/physical-ai-lab/.venv/bin/python \
  internal/physical-ai-lab/scripts/replay_v3_discovery.py \
  --output internal/physical-ai-lab/runs/<fresh-replay-directory>
```

The runner refuses to overwrite an existing output directory. Public tests use
generated inputs and do not publish private frames, responses or credentials.

| Final artifact | SHA-256 |
| --- | --- |
| r4 report | `651667f5ef2c93bbe1b23b6d46d3b2e1581cbb38f8f01cf7418cbc08e6ee3e3f` |
| r4 protocol | `77d22b512c96eea1420953c0667d6613c459b0a91a91615a2dc3f6812e4d557a` |
| Phase 0 private audit report | `9d6a4fe030096c8edea626bdbe181f93e9501d15484a6e93dab3bcc40d219612` |

Next: Phase 2 hard association/loss replay, with source-camera/session and stale
seed checks, wrong semantics, similar candidates and reset-ID reuse. Retained
scripted pumpkin displacement/revisit images can test safe uncertainty, but are
not natural occlusion or autonomous motion evidence. The existing 131-frame
Situated replay does contain a bounded partial hand occlusion near action 924;
retain that evidence rather than requiring a new capture for the same case.
Natural full disappearance, identical-object crossing and broader occlusion
qualification remain gaps.
Do not turn those missing tests into presumed success or refresh current geometry
from a remembered label. New paid discovery/context studies still require their
own budget authorization; strict motion remains gated.
