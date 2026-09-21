# Geometry and Action Compiler V1 — validation record

**Date:** 2026-09-21. **Reviewed repository base:** `ffdd3bb8da9bfffb533cb5b77cd6ea88752c5a14`.

## Results actually obtained

| Check | Result | Scope |
| --- | --- | --- |
| New package regression suite | **149 passed** | Geometry, frame conventions, constraints, programs, catalogs, native-interface test doubles, real existing root contract types and JobManager, receipts, faults, worker protocol, attention, metrics, overlays and scene projection. |
| Same suite after applying the packaged overlay to a fresh partial workspace | **149 passed** | Confirms installer output imports and runs against the mirrored reviewed interfaces. Not a complete upstream checkout. |
| Installer regression suite | **15 passed** | Read-only preflight, additive/idempotent application, interface drift, corruption, conflicts, traversal, symlink rejection, write-failure rollback and duplicate manifest keys. |
| Synthetic end-to-end fixture before/after application | Passed | Synthetic RGB-D → geometry → grasp/contact/inspection candidates → scene/catalog → ID selection → fake bounded execution → receipts/metrics. No robotics success claim. |
| Patch | `git apply --check` passed | Additive patch on an empty patch-check directory; normal target review is still required. |
| Syntax | Python 3.11 grammar accepted | All delivered Python payload files were parsed using `feature_version=(3,11)`; runtime tests used Python 3.13. |
| Ruff | **Not run** | Ruff was not installed in this execution environment. Run the repository's real lint command after merge. |
| Full pre-existing repository suite | **Not run** | Git/archive download was unavailable from the container; only selected source files were mirrored for runtime tests. |

The 149 and 15 counts are separate suites. Do not add 149 to a historical public test count and claim the resulting full suite passed. Re-running the same suite after application is a packaging check, not independent robotics replication.

## Upstream interfaces used in local tests

The local test workspace contained byte-verified copies of these reviewed files:

- `physical_harness/jobs.py`: Git blob `f0c4022d53bce13866a700ecafa26679eccba666`.
- `physical_harness/contracts.py`: Git blob `6bfcfc85b46ae9b7736676a3a242f5d854cfcdd5`.

The installer additionally checks the existing Hybrid contract at blob `7a80755313aabeda50ad7203b846c3f633ccbb18`. Its original bundled bytes were used as an installer guard input, not as evidence that every Hybrid/native integration was executed.

The test workspace uses namespace-package assembly; it does not execute the full repository's root import graph. `CatalogMotor.run_skill` was exercised with the actual root SkillRequest/SkillReceipt definitions. Journal behavior was tested through an in-memory implementation of the existing immutable `put/records` contract, not the production SQLite Journal. `CatalogMotor.actions`, full EpisodeRunner wiring, native binding replacement and the real FrozenPolicyPort reset/serve chain still require full-checkout and native-environment integration tests.

## GraspGenX checks and their limits

The adapter follows source inspected at `NVlabs/GraspGenX` commit `b9429097728cb1c430dd78b92edf17ba318aad03`. Tests exercise the exact intended callable arguments through a mock: single generation attempt, bounded top-k, finite SE(3) output, empty output, deadline handling, and one-time grasp-frame-to-TCP conversion.

Local preflight tests use temporary synthetic assets and mock source/import responses to verify that both upstream asset-directory overrides are set before any import, identity/manifest mismatches fail first, and no inference occurs merely while loading. Separate process tests cover stdout framing, response correlation, timeout/EOF/oversized output, and channel poisoning. These are not live tests of the upstream neural package or CUDA stack.

**No GraspGenX weights were downloaded or loaded. No GPU grasp inference was run. No actual R1Pro gripper profile was created or qualified.** The inference adapter must be exercised with the audited real assets in an explicitly approved, separately provisioned worker before it becomes a qualified proposal backend.

## No native or paid work performed

No BEHAVIOR or other physics simulator was launched; no physical or simulated robot action was sent; no real VLA inference, GPT/API call, training, cloud allocation, policy-server startup, credential handling, license acceptance, repository push or modification of ongoing experiments occurred.

The Cartesian executor was tested against a deterministic pose-following fixture. That does not establish actual IK accuracy, compliance, contact observability, grasp force closure, collision clearance, tracking, stopping, radio activation or task success. Whole-program/per-step reviews rely on genuinely qualified native callbacks; test reviewers are not usable robot safety logic.

## Operator merge check

```bash
python apply_bundle.py --repo /path/to/physical-agent-harness --check
python apply_bundle.py --repo /path/to/physical-agent-harness --apply
cd /path/to/physical-agent-harness
python -m pytest -q tests/action_compiler
python -m pytest -q
ruff check .
```

Use the existing qualified primitives only. Native experiments must continue to respect the latest unresolved reverse/yaw response and localization findings. Do not convert software test passes into motion permission.
