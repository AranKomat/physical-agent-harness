# Phase 2: Retained Association Contracts

Date: 2026-09-23. Starting public commit: `597aa14`; the three accompanying
runtime fixes were frozen and hashed for this replay. This is **partial Phase 2
progress, not visual association or native manipulation qualification**.

## Result

The final private run `phase2-association-contracts-20260923-r2` exercises
10 of 14 frozen scenarios using retained source images, masks and metadata.
There are 36 mask-archive visits and 30 positive-mask visits, with overlap across
scenarios; these are not independent examples. No physical identity or action
bindings were granted. No new model inference, paid requests or robot actions ran.

All 987 checks pass: 794 source/runtime preflight checks, 186 public-contract
checks, five private-adapter checks and two validation checks. This count is
**not a model accuracy score**. All 124 runtime Python-file hashes remained
unchanged during the run.

| Scenario | Evidence and result |
| --- | --- |
| Continuous target tracking | Retained candidates source-bound; physical identity remains unknown |
| Wrong label on a region | Injected semantics cannot promote unknown association into canonical identity |
| Correct label on wrong region | Source-valid proposal alone does not establish association; contract rejection only |
| Similar objects | Not executed: scripted images lack retained association/mask evidence |
| Full disappearance | Not executed: natural full-loss evidence remains missing |
| Reappearance after full loss | Not executed: no independently qualified reidentification evidence |
| Tracker reset | Distinct generation scope preserved; old-generation packet rejected |
| Local ID reuse | Local number alone supplies no physical association |
| Camera/session mismatch | Bad seed/packet scope rejected; evidence-matched session control described below |
| Stale box | Refused on a different source capture; no retimestamping |
| Object movement relative to background | Not executed as association test; scripted displacement is not continuous native motion |
| Partial hand occlusion | Four retained native captures/masks accepted as candidates, not identity proof |
| Negative/no-target view | No positive target binding or guessed current location |
| Artificial scene switch | Reordered native timestamps rejected; not relabeled as a natural loss/reappearance |

The frozen protocol is `phase2-association-protocol-20260923-r2`: 14 scenarios,
670 files and 4,329 preparation checks. Its r1 source-selection draft is preserved.
The replay's r1 is also preserved; r2 corrects stale explanatory wording that
described an already-fixed camera check as an open finding.

## What Was Actually Exercised

The runner verifies source and mask hashes, shape/type constraints, original
capture associations and RGB/depth pairing where available. It uses public
`FrameRef`, `RegionRef`, `DiscoveryRequest`, `Tracklet`, `IdentityLedger`,
`BoxSeed`, seed validation and current-tracking contracts. Private packet guards
are labeled separately rather than counted as public guarantees.

Each identity candidate starts with ambiguous semantics and no metric center.
All subsequent association proof support flags remain unknown. Consequently,
binding denials **do not prove invalidation of previously valid geometry on
loss**. Separately, the existing synthetic identity-loss regression now explicitly
asserts a valid pre-loss binding, then rejects both old/current bindings after loss
and journal reload while retaining remembered semantics. This establishes the
software transition only; do not interpret an already-unbindable retained candidate
or this synthetic positive fixture as native loss qualification.

A separate same-frame, evidence-matched callback control accepts lineage metadata
for the recorded seed/mask/session and rejects changing only the session. Its
positive return is not converted into an `AssociationProof`, passed to the identity
ledger, or given motion authority. This tests the repaired callback contract,
not physical reidentification.

The source sequence includes actual partial hand occlusion near action 924 and
clearer visibility at 956. Main-thread visual inspection confirmed that limited
description. Duplicate sequence numbers 768/860 remain distinct captures. Paired
depth statistics do not establish camera-to-map extrinsics or cross-frame identity.

The clock domain is explicitly `fixture`: capture index supplies ordering only,
native monotonic observation times are retained, and availability uses a controlled
fixture schedule. The replay does not recover missing live model-publication times.
Scripted task/entity labels and evaluator files are excluded from model inputs.

## Three Demonstrated Boundary Fixes

1. Tracking validation previously returned a proposed session without passing it
   to the trusted association checker. An evidence-aware checker received identical
   arguments when only the proposed session changed. It now receives keyword-only
   `session_id` and must verify independent source/session provenance. There is no
   legacy callback fallback. This was a metadata attestation gap, not demonstrated
   physical identity leakage or motion execution.
2. Discovery delivery checked episode/time but not consumer robot/domain or a
   consumer capture after `now`. Injected mismatches could populate inventory and
   wake the executive. Every request frame now passes `available(current, now)`
   before either write. Historical, cross-camera and relocalized consumers remain
   supported when compatible.
3. A region could reference a head-camera image but declare a wrist-camera track.
   `DiscoveryRequest` now checks scoped-track camera against its referenced frame.
   Valid head and wrist scopes still pass; session provenance remains a separate
   trusted-adapter responsibility.

Ten public regressions cover these boundaries. Before fixes, six of the first
seven new cases failed and one passed; the separate camera suite had one failure
and two valid positives. After fixes all pass. No action or association threshold
was lowered; the identity schema was not expanded.

## Verification And Runtime Restoration

- Public full suite: **1,481 tests**, Ruff and five synthetic CLIs pass.
- Synced Linux host: **204 embodied tests** pass.
- Private suite: **604 passed, one existing skip**; includes 23 new replay tests.
- Phase 1 regression replay `v3-retained-discovery-20260923-r5`: 64 checks,
  six packets and 67 sightings pass after the new consumer checks.
- Repository ownership/local links and whitespace checks pass.
- An initial private-suite invocation omitted its scripts import path and failed
  collection with 28 import errors. The corrected command below passed; no source
  changes were made to suppress those errors.

From `internal/physical-ai-lab`, private software validation:

```sh
PYTHONPATH=scripts:../../physical_agent_harness_scaffold .venv/bin/python -m pytest -q tests
```

The single-4090 host now has clean SAM source revision
`2345a4ad109ac29c569da749c91d84f10dc08c40` and all 59 dependency versions from
the retained SAM environment. Builder import, CUDA tensor arithmetic and
`pip check` pass. This is **not a model-loading/inference test**. The checkpoint
is absent and no Hugging Face token is configured there; restore an authorized
copy/login before new inference. Simulator and policy environments remain missing.

Private restoration receipt: `sam31-runtime-restore-20260923-r1/report.json`.
No instance was stopped or destroyed. No campaign reservations were changed.

## Next Gates

1. Obtain the already-approved SAM checkpoint, then run bounded hard-case
   inference with the frozen protocol and explicit gaps; do not repeat prompt
   sweeps or only easy continuous tracking.
2. Qualify actual association and inherited geometry invalidation across native
   loss/reset/ambiguous objects before refreshing manipulable entities. The separate
   synthetic state-transition test is necessary but insufficient.
3. Obtain legal natural full-loss/reappearance and similar-object crossing
   evidence; scripted images cannot substitute for those native outcomes.
4. Delayed identity-claim publication remains a schema limitation. Historical
   discovery belongs in availability-aware inventory; `IdentityLedger` is not a
   historical publication-time database.
5. Live GLM shadow/delta-context comparisons still require separate call approval.
   Motion and later task-benefit phases remain gated by native qualification.

| Artifact | SHA-256 |
| --- | --- |
| Phase 2 final replay report | `5abc65f31db86a3eadc00015c7e3d5c64ffd6797a5663f0bf1819d7a3805a59d` |
| Frozen r2 protocol | `76ebe8b0a34dfe1b0fabe26882b11b1b9f0dbf4317f045870ed3109d07321907` |
| SAM runtime restoration report | `ff9cde21896c119c400e06c5547a2e13cb612bd6ecd039ef1e649e79e8cf4dcb` |
