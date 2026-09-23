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
| Observation/action lineage | `core.actions.Basis`, `core.discovery.FrameRef` |
| Evidence and lifecycle | `core.evidence`, `core.events`, `core.jobs` |
| Current beliefs and task state | `world.state.WorldState`, `core.ledger` |
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
