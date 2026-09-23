# Executive And Context Profiles

`reasoning.executive` is the recurrent embodied decision boundary. The executive
receives current evidence and offered options, then selects, retrieves or holds.
Slow replies require fresh semantic rebinding; they cannot reuse expired catalogs.
`reasoning.selection` retains the smaller skill-selection implementation used by
existing fixtures. It is not a second concurrently running executive.

All context implementations live in `reasoning.context`:

| Profile | Existing contract |
| --- | --- |
| Conservative | `conservative.ContextProjector`: small WorldState projection |
| Rich | `rich.RichContextBuilder`: broad current roster, ledger and history |
| Compact | `compact.build_context`: Basis-bound images, facts and eligible catalog options |

Select explicitly through `project_context`; there is no automatic fallback or
silent conversion between schemas. Required critical facts cannot be pruned to
make a packet fit. Rich metadata overflow remains visible; compact omission only
applies to explicitly optional items and is reported. Saved trial profiles remain
part of the trial identity.

`core.events` owns runtime event types and semantic boundary records. EventBus
history, monitor signals and discovery attention feed scheduling; none is task
truth. RuntimeEvent uses recorded epoch wall time; BoundaryEvent uses the run's
monotonic availability clock and Basis. They must not be implicitly interconverted.
`reasoning.monitor_events` is the explicit advisory-to-boundary projection.

Verifier and executive remain separate causal roles. Actual provider transports
and budgets live in `integrations.experiment`; subscription-backed experimental
transport is not a behavior-equivalent API replacement. No consolidation change
permits additional paid calls or clears unresolved reservations.
