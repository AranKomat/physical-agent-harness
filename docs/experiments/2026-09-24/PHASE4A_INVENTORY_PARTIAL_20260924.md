# Phase 4A Frozen Inventory Partial Cohort

The preregistered Phase 4A task-blind inventory comparator started on the four
held-out source indices `0`, `8`, `10`, and `15`. The run used GLM 5.3 Flash
through Together with low reasoning effort, strict structured output, no
provider fallback, no retry, and no robot actions.

## Outcome

| Item | Result |
| --- | --- |
| Approved cumulative ceiling | `4153` calls |
| Starting cumulative count | `4149` |
| Calls dispatched | 2 |
| Valid inventory packets | 1 |
| Unresolved transport outcomes | 1 |
| Calls intentionally not dispatched | 2 |
| Robot actions | 0 |
| Automatic retries | 0 |

The first response completed in `9.6441 s`, cost `$0.00049125`, and passed the
frozen inventory schema despite the provider adapter reporting
`terminated_semantic_ungraded`. It returned a 12-item room inventory on source
index 0.

The second request, for source index 8, reached the predeclared 110-second
timeout. Its status and format status are `unknown`, usage is unavailable, and
the full `$0.0102288` reservation remains unresolved. The runner then stopped as
specified. It did not retry the request and did not dispatch indices 10 or 15.

After the attempt, the shared ledger recorded:

- cumulative calls: `4151`;
- confirmed spend: `$23.65381692140`;
- unresolved exposure: `$34.965453822900`;
- total exposure: `$58.619270744300`;
- remaining exposure under the `$75` ceiling: `$16.380729255700`.

## Interpretation

This is a transport-qualified partial result, not the matched Phase 4A prompt
comparison. It adds one valid task-blind inventory packet but cannot support
aggregate coverage, unsupported-claim, latency, or cost comparisons against the
completed V3 half. The unresolved request must remain acknowledged in future
ledger resumes.

Completing Phase 4A requires a newly declared continuation or replacement
protocol for the two unsent views and the unresolved view. It must not silently
retry this request or merge a later cohort without preserving the timeout.

Private artifacts are retained at
`runs/phase4a-frozen-inventory-20260924-r1`. The frozen source/action hashes were
unchanged before and after the run.
