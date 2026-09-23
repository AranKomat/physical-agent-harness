# Action Compiler V1 Integration

Integrated 2026-09-22 into the real repository after `24f7dd2`, with the stopped
assisted-probe work preserved separately in `14eaeef`. Native experiments remain
paused at the user's request. The compiler is opt-in, not enabled in the radio
runner or live executive. No model calls, weights, licenses or native motion were
introduced by this integration.

## Provenance

- Bundle: `physical_agent_harness_action_compiler_v1_20260921.zip`.
- SHA-256: `78e6796ff13a6af945e0a70f6f33c26f99f15fe66f95338654ac1a3e2db64d64`.
- Author's reviewed base: `ffdd3bb8da9bfffb533cb5b77cd6ea88752c5a14`.
- All bundle checksums and exact guarded interface blobs passed verification.
- The installer added 31 files and overwrote no existing source files.
- The [author handoff](ACTION_COMPILER_V1.md) and
  [author validation](ACTION_COMPILER_V1_VALIDATION.md) retain their original
  scope and historical experiment status; this note records actual-checkout
  validation and corrections.

## Merge Corrections

The bundled MemoryJournal returned `{id, payload}`, but the repository's real
SQLite Journal returns `{id, ...record_fields}`. The compiler's history loader
and metrics therefore raised `KeyError: payload` with actual persisted records.

Corrected both consumers and the fixture to use the existing flat Journal
contract, without modifying Journal or adding another storage system. Added
real-SQLite regression tests proving:

- execution receipts and auxiliary-model accounting can be summarized;
- consumed action IDs remain one-shot after closing/reopening the database;
- unresolved stop faults survive closing/reopening the database.

Also corrected two test import-format issues and linked the package from the
root README. Core contracts, policy preprocessing, existing control gates and
current memory defaults remain unchanged. The original bundle is preserved
privately; its installer should now refuse reapplication over corrected files,
rather than overwrite the integration fixes.

## Validation

| Check | Result |
| --- | --- |
| Author's compiler tests, before corrections | 149 passed |
| Added real-journal tests before correction | Both failed, reproducing the mismatch |
| Compiler tests after correction | 151 passed |
| Complete repository suite | 793 passed |
| Synthetic end-to-end CLI fixture | Completed, no model inference or native motion |
| Ruff | Passed |
| Consolidated offline validator | Passed with full suite and lint |

Validation artifacts are retained privately. This establishes offline software
integration, not GraspGenX proposal quality, native feasibility, autonomous target
grounding, R1Pro control, or task success. Native port qualification and the
handoff's E1-E7 experiments have not been started by this merge.
