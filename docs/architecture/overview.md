# Architecture And Ownership

This is the canonical architecture. Historical milestone handoffs describe why
parts were introduced, not additional runtime stacks that should be installed.
The end-to-end native integration remains experimental.

```text
                     Recurrent GPT executive
                   current state + source images
                              |
                     capability / task graph
                              |
               navigation / manipulation / inspect
                              |
                reviewed action catalog and program
                              |
                 ActionExecutor + JobManager
                              |
                native driver / optional frozen VLA
                              |
                     fresh legal observations
                              |
        RGB-D -> tracking -> identity -> state -> verification
          |                      |        |           |
          +-> read-only GLM ------+-> historical       +-> ledger
              hypotheses             memory                |
                              events -> executive boundary
```

Arrows indicate evidence/control boundaries, not a claim that every optional
port is connected in the native runner. Safety monitoring does not wait for GPT.

| Responsibility | Canonical implementation |
| --- | --- |
| Observation/action lineage | `core.actions.Basis`, `perception.contracts.FrameRef` |
| Evidence and lifecycle | `core.evidence`, `core.events`, `core.jobs` |
| Current beliefs and task state | `world.state.WorldState`, `world.ledger` |
| Physical association | `perception.identity.IdentityLedger` |
| Historical sightings and memory | `world.inventory`, `world.memory` |
| Task graphs/capabilities | `planning.tasks` |
| Geometry-filled programs/catalogs | `planning.actions`, `core.actions` |
| Native action ownership | `execution.actions.ActionExecutor` and existing JobManager |
| Recurrent executive/context | `reasoning.executive`, `reasoning.context` |
| Optional vendor/native ports | `integrations`, `experiments/behavior` |

Read next: [world state](world_state.md), [perception](perception.md),
[navigation](navigation.md), [execution](execution.md),
[executive](executive.md), [safety/evidence](safety_and_evidence.md).

## Code Categories

Core contracts live in the seven responsibility domains. `integrations/` houses
replaceable adapters, including provider transport and native IPC. Synthetic
fixtures and evaluation helpers live in `experiments/fixtures`; task-specific
drivers and diagnostic tests live alongside `experiments/behavior`.
GPU libraries must remain lazy imports. A passing mock is not port qualification.

## Enforced Dependency Boundaries

`tools/check_repository.py` enforces this default DAG (each row may import itself
and the listed domains):

| Domain | Allowed dependencies |
| --- | --- |
| core | No other runtime domain |
| perception | core |
| world | core, perception |
| planning | core, perception, world |
| execution | core, perception, world, planning |
| reasoning | core, perception, world, planning, execution |
| integrations | All runtime domains |

Experiments may compose all domains. Domain modules must use owning-module imports,
not the root convenience facade. Absolute and relative imports, nested and
TYPE_CHECKING imports, and literal importlib/__import__ calls are checked.
Computed plugin names cannot be established statically; this is not a sandbox.

The entire existing import graph is **not yet a strict DAG**. Twelve existing
bridges are explicitly grandfathered by exact source, target and imported symbols
in the checker, with reasons. Examples include the servo's planner contracts and
the legal observation envelope. No core exceptions are allowed. Added symbols or
new importing modules fail; stale exception symbols also fail and must be removed.
Do not expand the allowlist to conceal a new dependency cycle.

Discovery wiring lives in `perception.discovery_coordinator`; planner/driver
wrapping lives in `execution.planner_bridge`; the existing synchronous
`HarnessRuntime` composition lives in `reasoning.runtime`. No new session framework
was introduced. These remain separate optional paths, not a claim of an assembled,
qualified live V3 system.
