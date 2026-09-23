# Execution Hierarchy

| Level | Meaning and owner |
| --- | --- |
| Primitive | One bounded operation such as MOVE_EEF or gripper command; `core.actions` |
| Program | Current geometry-filled sequence of primitives; `planning.actions` |
| Capability | Parameterized qualified behavior and role/precondition contract; `core.tasks`, `planning.tasks.capabilities` |
| Graph | Task-level composition with budgets and explicit handlers; `planning.tasks.graph`, `execution.graph` |
| Executive decision | Selects/repairs an offered capability or requests evidence; `reasoning.executive` |

The lower levels cannot establish higher-level success merely by finishing.
The graph ledger must verify its declared postconditions independently.

For new task-facing APIs, **capability** is the reusable-behavior term. Existing
`CapabilityMacro` names an artifact of a capability, not another level in this
hierarchy. Recorded `skill`, `macro`, `route` and `phase` fields retain their wire
meaning; routes/phases describe lower-level handoffs, not parallel task planners.

`execution.actions.ActionExecutor` owns admitted programs through the existing
JobManager. `execution.handoff` retains sequential classical/frozen-policy phases
for matched experiments; it is a lower-level backend protocol, not another task
planner. A graph calls a reviewed program handler, which calls the native driver.
Do not nest independent actuator owners or run a VLA concurrently on owned joints.

`execution.servo` supplies bounded setpoints and counted trajectory streaming;
`integrations.curobo` supplies optional planner adaptation. Both still require
current collision, codec, calibration and stopping checks. Policy handoffs retain
queue reset, exact checkpoint/normalization fingerprint and hold semantics.

Receipts remain intentionally layered: `StepReceipt` accounts for a native step,
`ExecutionResult` for a program, and skill/navigation receipts for task-facing
outcomes. They are not interchangeable success booleans. No receipt schema or
recorded fingerprint was renamed during consolidation.

Six capability templates are unpromoted. New graph entries, synthetic passes,
finite action vectors and valid planner outputs are not native qualifications.
