# Physical Agent Harness

An experimental, evidence-backed runtime for embodied reasoning and bounded robot
execution. BEHAVIOR with R1Pro is the current integration target. **No reliable
general motor or task-success improvement from supervision/memory is qualified.**

## Start Here

Read the [architecture overview](docs/architecture/overview.md), then the
[current experiment queue](docs/experiments/queue.md). The seven architecture
pages define the active contracts; dated reports are research evidence, not
deployment instructions. [Integration status](docs/integration/README.md)
separates tested software from unqualified native ports.

```text
physical_harness/
  core/          evidence, events, lineage, jobs, contracts
  perception/    discovery, identity, geometry, localization
  world/         state, memory, inventory, topology, caches
  planning/      action catalogs, graphs, capabilities, navigation
  execution/     actuator ownership, primitives, servo, policy handoffs
  reasoning/     executive, context profiles, verification, monitors
  integrations/  experimental model, sensor, planner and transport adapters

experiments/     BEHAVIOR drivers and synthetic fixtures
tests/           regression tests grouped by runtime responsibility
configs/         explicit model/planner/qualification templates
docs/            canonical guides, decisions, and preserved research reports
```

## Offline Checks

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check .
python -m physical_harness doctor
python -m physical_harness demo --output runs/basic-demo-new
python -m physical_harness.reasoning demo --output runs/embodied-demo-new
python -m physical_harness.integrations.experiment doctor \
  --config experiments/fixtures/configs/doctor.fixture.json
```

Use fresh output directories. Demos are synthetic and neither load models nor
command a robot. Live services, paid calls, and native motion require separate
configuration, budget authorization, and qualification. Unknown clearance,
identity, or stopping state does not grant motion authority.

## Development Rules

- Add code by responsibility, not a new milestone/version namespace.
- Use the existing evidence store, `Basis`, event contracts, and executor.
- Keep semantic labels separate from physical identity and current geometry.
- Preserve recorded evidence and billing holds; no silent retries or repair.
- Keep private observations, credentials, licensed assets and weights out of Git.

The [decision log](docs/decisions/README.md) records the design choices.
The [consolidation report](docs/architecture/consolidation.md) lists moved APIs,
intentional distinctions, validation, and compatibility limits. This research
repo does not promise the former milestone import paths as a stable SDK.
