# Situated Execution V2 Integration

Date: 2026-09-22. Scope: opt-in software integration, no native campaign.

## Provenance

- Bundle: `physical_agent_harness_situated_v2_20260922.zip`.
- ZIP SHA-256: `271cf8f36cdd07e82796217af087eec1b9c586231ab2fc20314c8f7ba3e26d1f`.
- Author-reviewed base: `1531ac983ebf142b4aca0b790538fff89330e3ef`.
- Integration checkout: `a4a2246` on `main`, clean before application.
- Inspected the archive and installer before applying. The pinned reused
  interfaces matched; the installer added 31 files without replacing existing
  files. Private extraction, receipts and experimental assets are not published.

## Integrated Surface

`physical_harness.planning.tasks` adds journal-backed identity/semantic history,
inspection and anchor-relative keypose proposals, bounded sequential semantic
graphs, advisory progress monitoring, exact-dependency representation caching,
and optional causal SAM prefix replay. It reuses the existing executor, job
ownership, journal, WorldState and EventBus. Nothing is enabled in the live
controller merely by installing or importing the package.

Integration changes beyond the supplied overlay:

- Fixed 11 Ruff import-order findings.
- Added 10 regression cases covering single-frame SAM propagation bounds,
  real WorldState projection/episode isolation, advisory EventBus publication,
  and clean imports without inference/simulator/provider dependencies.
- Selected `sam3.1` in the placeholder prefix configuration; inference and
  license opt-ins remain mandatory, with no automatic download.
- Reconciled the handoff, README and experiment sequence with newer SAM evidence.

## SAM Reconciliation

The [corrected live SAM 3.1 report](../experiments/2026-09-22/SAM31_INCREMENTAL_SHADOW_20260922.md)
remains authoritative for the private live worker: 768 frozen-policy actions,
25 captures, zero drops, all 50 raw-image accesses on the current frame.
Warm tracking was 252 ms median / 284 ms p95; ingress-to-mask/depth latency
was 483 ms median / 540 ms p95. Sparse boundary sampling is not video-rate
qualification or evidence of safe contact, persistent identity or task success.

The live adapter's frame-index correction is preserved. The new adapter is
instead a fresh, point-seeded JPEG-prefix session with tail-only publication.
It uses the positive prefix length as its propagation bound, including 1 for
a single-frame prefix. The regression tests check request semantics with mocks;
they do not certify upstream GPU raw-image indexing. This loader still needs
independent weight-coverage, runtime and resource qualification before use.

The corrected private tracker, lossless PNG capture path, timing reports,
superseded failed-run evidence, frozen Behavior-Skill recipe, independent verifier,
and motion gates were not changed. No API/cloud tracker substitution was made.

## Validation

Run in the actual repository checkout, without the bundle author's test-only
namespace shims. The existing private lab Python/Ruff environment was used:

```text
python -m pytest -q tests/situated
130 passed

python -m pytest -q
1228 passed in 15.21s

ruff check .
All checks passed!

python -m physical_harness.planning.tasks demo --output <fresh-private-run-directory>
scope: synthetic_software_fixture
native_robot_actions: 0
model_calls: 0
synthetic_graph_finished: true
```

The suite previously contained 1,098 passing tests. The overlay supplied 120;
integration added 10. The original installer suite also passed 21 tests.
No GPU work, paid model calls, model downloads, policy training or native
robot/simulator motion was performed during this integration.

## Next Qualification

Start with causal retained identity/permanence replay, then longer-stream reset,
occlusion, reacquisition and distractor checks using the selected SAM 3.1 path.
Association proofs still require a truthful provider, not just matching tracker
IDs or class labels. Monitor events remain advisory; the independent verifier
and task ledger retain completion authority. Native inspection/keypose execution
still requires the existing geometry, localization, clearance, stopping and
per-step review gates. See the [two-lane handoff](SITUATED_EXECUTION_V2.md).
