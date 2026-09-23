# Live Discovery And Scan Preflight

## Authorization And Scope

The user approved both bounded scopes: six GLM calls with a $1 local cap and
4,145 cumulative-call ceiling, and one exploratory simulator sensing scan with
the bounds in [the scan protocol](NEXT_SENSING_SCAN_PROTOCOL_20260923.md).
The $75 ceiling and all old holds remain unchanged. The shared GPU instance
remains running; no system changes or unrelated workload intervention occurred.

## Live Semantic Chain: Partial

Private evidence: `live-v3-discovery-20260923-r1`, `-r2` and `-r3`.

The native simulator supplied paired-render RGB-D/proprio captures, real
simulator time, source image hashes and GPU-host monotonic capture timestamps.
The actual AsyncDiscovery worker, strict response parser, coordinator and
SemanticInventory ran on that same host clock. A Mac-side file bridge retained
credentials and all paid-call accounting in the existing campaign ledger.
No actuator consumed the semantic output; native actions were zero.

- Run 1: SSH connection failure before any provider dispatch. Discovery expired
  without inventory publication. Zero paid calls. A cleanup timeout argument
  exceeded the worker API's 60-second maximum; fixed for run 2.
- Run 2: a dedicated persistent SSH connection enabled three provider calls.
  The first two responses reached historical inventory (four and five updates).
  The third response was rejected atomically: attention IDs `mantel_view` and
  `cabinet_top` did not match any returned update IDs. No retry or repair occurred.
- Provider latencies: 8.17, 9.06 and 18.99 seconds. Total new cost: $0.00284430.
  Cumulative calls: 4,142. Confirmed spending: $23.64785397140. Unresolved holds:
  $34.955225022900. Total exposure: $58.603078994300.

Schema-valid JSON is not sufficient semantic-contract compliance. The attention
cross-reference validator worked correctly. The discovery prompt and schema
descriptions now explicitly explain the linkage; the validator is unchanged.
Run 3 tested this revision on three new native paused captures, not resends of
the rejected request. All three calls passed and published four, four and two
updates respectively, with valid attention references. Provider latencies were
8.73, 9.40 and 6.64 seconds. The worker and native capture process exited cleanly.

An earlier accepted response also encoded "no radio sighted" as a full-image
object sighting. That is undesirable semantic content despite valid structure.
The revised prompt directs limited non-observation statements to scene_summary,
not object updates; it does not authorize absence/coverage conclusions. This
remains a semantic-quality issue to test, not a solved guarantee. The full-image
pseudo-object did not recur in run 3. Suggestions to inspect the cabinet or
mantel remain hypotheses, not evidence of a radio's location.

All six approved calls have now been consumed. Total new cost across runs 2/3:
$0.00511925. Final cumulative calls: 4,145; confirmed $23.65012892140;
unresolved holds $34.955225022900; total exposure $58.605353944300.
No more paid calls are authorized by this scope.

These repeated paused views are not a coverage benchmark or identity test.
The runner initially inherited Basis's `fixture` domain despite native pixels;
that metadata bug is corrected to `behavior_sim` in run 3. Raw receipts
are preserved unchanged. The run also did not exercise pending-job coalescing,
novelty-driven selection, executive context consumption or robot control.
Phase 3 therefore remains partial, not complete.

## Fresh Scan Geometry: Passed, Motion Not Run

Private receipts: `fresh-view-endpoints-20260923-r1`,
`fresh-view-path-20260923-r1`, `fresh-view-scene-points-20260923-r1`.

Candidate 67's relative joint intent was rebuilt from run 1's newly captured
robot posture, not replayed from historical sequence 416. It fits native URDF
joint limits and the approved 1.6-rad departure bound. The prepared profile
requires 562 actions including 20 initial and 60 final holds at the previously
declared 0.1-rad/s command limit.

Both endpoints have zero authored-hull self-collisions. Minimum endpoint
distances are 23.14 and 23.33 mm. Continuous support-gap checking passes in 35
adaptive nodes at the existing 11.07-mm diagnostic margin.

Three-camera depth rejection at 17 path fractions found up to 335 raw point
intrusions; all were within the explicitly ambiguous near-start robot region.
There were zero sampled intrusions outside it. This does not establish free
space, continuous external clearance, native cooking equivalence or stopping.
The historical 299-view-sample count is not validated for this fresh posture.

No scan was executed. A native monitored runner must still bind the geometric
checks to its own fresh episode, freeze tracking/abort thresholds, and retain
whole-arm substep measurements and the reserved hold budget. Approval does not
remove these prerequisites. No base transit or manipulation was attempted.

## Next Work

1. The clarified contract's three-call smoke test passes. A broader prospective
   discovery/context test still needs a separate future paid-call scope.
2. Complete native scan monitoring and fresh-episode admission before the one
   bounded exploratory movement. Keep unknown clearance explicit.
3. Only then resume the downstream sensing/association and motion experiments.

Private suite after runner/preflight changes: 1,149 passed, one skipped. The
public suite passes 1,490 tests and Ruff. Its prompt regression checks that
schema-valid dangling attention references remain rejected. All three raw runs
are copied locally with checksum comparisons. Owned GPU workers exited; the
instance is retained for the user's other workload.
