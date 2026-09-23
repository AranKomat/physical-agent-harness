# Consolidation Record

2026-09-23; no new robot, model or planning capability. The baseline is `10b58fe`
plus the integrated, uncommitted Embodied V3 overlay. Pre-migration source and
private-consumer snapshots were saved locally before moving files.

## Before And After

| Surface | Before | After |
| --- | --- | --- |
| Runtime organization | Root modules plus 8 packages, including 4 milestone packages | 7 responsibility domains |
| Historical milestone packages | action_compiler, hybrid_v0, situated, embodied_v3 | Removed; concrete modules migrated |
| Library Python files | 123 | 123, including new domain package markers |
| Library source lines | 20,026 | 19,151 |
| Flat documentation files | 84 | Index only; guides, references and experiments separated |
| Dated research reports | 58 in the docs root | Same 58 under experiment dates |
| Duplicated validation drivers | 2 milestone scripts | One `tools/validate.py` |
| Package-wide eager re-export layers | 3 milestone aggregators | Removed |

Most library-line reduction is relocation of synthetic fixtures/evaluation to
`experiments/fixtures`, not deletion of functionality. The repository is not
claimed to have fewer total files: canonical documentation and import-regression
tests add files. Private recorded inputs, native images, weights and billing holds
were not rewritten. Report navigation paths changed; measured outcomes did not.

## Canonical Homes

| Former module/group | Current home |
| --- | --- |
| action_compiler.types, root contracts/events/jobs | core.actions, core.contracts, core.events, core.jobs |
| situated.identity and perception | perception.identity and perception.track_bindings |
| embodied_v3 discovery/keyframes/regions | perception.discovery/keyframes/regions |
| root state/navigation, memory, embodied inventory | world.state/topology, world.memory, world.inventory |
| action compilation and situated graphs | planning.actions and planning.tasks |
| action executor, hybrid phases, servo | execution.actions, execution.handoff, execution.servo |
| embodied executive and context builders | reasoning.executive and reasoning.context |
| model/native/SAM/GraspGenX/cuRobo adapters | integrations |

The [module migration inventory](module_migration.json) records moved modules.
There are no old-path shims. Active public consumers and private lab source/test
imports were migrated. Other external consumers must update imports before using
this tree. Package-wide re-exports are intentionally not preserved: import the
concrete module that owns a contract.

Symbol-level changes beyond that map:

- `EventType`, `RuntimeEvent`, and `BoundaryEvent` now live in `core.events`.
- Compact `ControlMode`, `ContextBudget`, `ExecutiveOption`, `ContextItem`,
  `ExecutivePacket`, and `build_context` live in `reasoning.context.compact`.
- `reasoning.context.project_context` selects conservative, rich or compact
  profiles explicitly, preserving their existing schemas and failure behavior.

## Consolidated Concepts, Not Collapsed Authority

The event definitions, bus, and boundary wake taxonomy now have one home. Runtime
and monotonic semantic availability clocks remain distinct; no lossy conversion
was added. Context profiles share an entry point without silently changing trial
inputs. The same Basis class is used by geometry, identity and action paths.

WorldState, IdentityLedger and inventory are complementary authorities/views,
not three databases allowed to declare current physical identity. The compact map
is a projection of existing occupancy/topology. Semantic caches wrap the existing
dependency cache. These distinctions are documented rather than erased.
Step/program/skill receipts also retain their original meaning and wire values.

Historical configs with live relevance have responsibility-based paths; synthetic
doctor/prefix configs moved beside fixtures. No apparently old qualification
contract was deleted merely for being old. Deployment templates stay disabled or
unqualified as before. Old overlay installers are pinned to their original tree
and must not be reapplied to the consolidated layout.

## Verification

All 1,408 pre-existing tests passed after module and contract migration. With the
new profile/import/layout guards, **1,418 repository tests pass**. The final
validation command is `python tools/validate.py --output <fresh-directory>`:
full suite, Ruff, and five synthetic CLI fixtures. The repository checker validates
local Markdown destinations and rejects retired imports. GPU inference, native
motion and paid model calls are outside this cleanup.

Final validation also passed on the new Linux host: **1,418 tests and Ruff**.
An isolated wheel installation outside the source checkout passed all-module
imports, packaged doctor configuration, and the embodied synthetic demo. No GPU
library was imported by the all-module smoke check. Source copies on the host
were backed up before synchronization; only obsolete bytecode directories were
removed after the source move.

The full private-lab suite passes: **563 passed, 1 existing skip**, including the
25 SAM streaming/GLM/LocateAnything checks. Updating import paths does not qualify
a live V3 pipeline or change any provider/robot permission.

## Follow-Up: Ownership Boundaries

Review of `35bc2b6` identified domain-specific contracts and coordination still in
core. A follow-up moves discovery contracts to `perception.contracts`, discovery
coordination to `perception.discovery_coordinator`, the read-only identity view
to `perception.identity`, and planner qualification wrappers to
`execution.planner_bridge`. Function behavior and receipt/wire values are unchanged.

The same audit moves the existing runtime to `reasoning.runtime`, the state-backed
ledger to `world.ledger`, compute accounting to `reasoning.compute`, grasp worker
serialization to `integrations.grasp_serde`, and handoff contracts to
`execution.handoff.contracts`. Core is now a source-level leaf domain. This is
ownership cleanup, not a new composition framework or capability implementation.
The migration inventory includes these follow-up paths; the earlier table/counts
above describe the initial consolidation.

The [dependency policy](overview.md#enforced-dependency-boundaries) is enforced by
AST tests. Its default DAG has no core exceptions. Twelve exact existing bridges
outside core remain documented debt, not general permission to import upwards.
Recorded formats, identity authority, actuator gates, provider budgets and the
experiment queue are unchanged. Root convenience exports remain for now; domain
code cannot use them to conceal dependencies.

Follow-up validation: **1,451 repository tests pass** locally and on the Linux
host, including 33 import-boundary tests. Ruff passes on both hosts; the local
unified validator also passes all five synthetic CLI fixtures. The private-lab
suite remains **563 passed, 1 existing skip**. The five relocated coordinator
definitions are AST-identical to their originals. These are software-only checks,
not evidence of live perception, planner, or robot qualification.
