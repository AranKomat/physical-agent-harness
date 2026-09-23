# Scan Hold Base Evidence

## Retained Result

The completed exploratory sweep had full joint monitoring during its 60 reserved
holds but stopped running its legal RGB-D/FK base observer at the outbound
endpoint. The raw captures already existed, so no new motion was needed to
inspect that interval.

`scan-reserved-hold-base-20260924-r1` replays the last outbound capture plus all
60 hold captures with the existing `ScanBaseObserver`, pinned robot FK assets,
paired-render RGB-D, and unchanged drift/rate limits. It reads no evaluator truth.
All 61 observations pass. Maximum estimated displacement relative to the hold
anchor is 1.987 micrometres; maximum estimated translation rate is
0.000077315 m/s. These are estimator outputs, not calibrated accuracy bounds.

The replay clock is explicitly source observation time plus 0.1 seconds, not
measured live processing latency. Its receipt therefore keeps stop qualification
false. The report is copied locally. Full hold RGB-D remains on the host; the
earlier local fixed-stride subset does not contain every hold image.

## Runner Correction

Future scan holds now obtain legal base feedback as well as raw settling and
physics-substep joint feedback. The reserved-hold observer receives a fresh
paired-render anchor before the first hold. It is separate from the outbound
observer, whose failure remains latched: an aborted outbound step can omit an
observation, so blindly reusing it would reject the first hold as a timing gap.

The change preserves raw base abort limits, action caps and stop-unknown status.
It adds no robot commands, but adds one render-only capture and base estimation
work. Observer failures remain explicit and cannot become zero-motion evidence.
The receipt records `hold_base_samples` and `hold_base_error` separately.

Twenty-four focused observer/launcher tests pass, including source binding,
stale/future input, raw base abort, and isolation from an outbound observer
failure. Full private suite: 1,265 passed, one existing skip. Changed files pass
Ruff. The modified native hold path has not yet been executed in a new simulator
trial; unit checks and old-frame replay are not live qualification.

## Phase Decision

This closes a specific measurement/integration gap in Phase 5D preparation.
It does not complete Phase 5 or authorize strict transit/arm return. Calibrated
measurement uncertainty, live failure-path timing and external clearance remain
open. Do not repeat the entire sensing sweep solely to reconfirm the same
coverage result; exercise the corrected hold path in the next justified native
protocol. No paid calls, new robot actions or system lifecycle changes occurred.

## Native Abort Trial: Failed Before Reserved Holds

The subsequent declared `native-abort-hold-base-20260924-r1` used fresh admission
and a fault at action40/substep2, followed by a planned 60 reserved holds (100
total). The callback cancellation and immediate hold write succeeded. The native
counter records 40 dispatched actions and 39 normal returns; the executor records
41 attempted callbacks because the first reserved-hold callback failed before
dispatch. No reserved hold completed. This is a failed trial, not a stop pass.

The new hold-anchor capture failed `Render-only recapture changed simulator
state`. Inspection found that `capture()` used `evaluator.obs` as its pre-render
baseline, which can remain stale after a thrown evaluator step. The exact failed
equality was not separately logged, so stale evaluator state is the identified
implementation defect, not a fully isolated measurement of all render behavior.

The local correction reads a fresh `env.get_obs()` envelope for the pre-render
baseline without replacing policy input. Exact simulator-time, position,
velocity and proprioception equality checks remain unchanged. Regression tests
cover stale evaluator input and forbidden policy-observation replacement.
Full private suite after correction: 1,267 passed, one existing skip; Ruff passes.
The corrected capture path is not yet native-verified. Do not report its tests
as recovered physical stopping or automatically retry the failed run.

The complete failed-run archive SHA-256 is
`1e5452dc2e738c5998c23b05d36cf33a2bc83e41486da10bc3d5afd9a0824510`.
Public baseline verification also completed: 1,490 tests, Ruff, ownership/local
links, and whitespace checks pass. No paid calls or unrelated workload changes.

## Corrected Native Repeat

The separately declared `native-abort-hold-base-20260924-r2` deploys the fresh
sensor baseline correction and repeats the same 100-action diagnostic, without
changing gates, geometry, command limits or fault location. Fresh admission
passes. The intentional fault remains recorded at action40/substep2.

All 60 reserved holds complete and are raw-settled. Native dispatch count is
100 with 99 normal returns because the intentional fault interrupts one return.
The joint hold monitor retains 240 physics samples without error. The separately
anchored legal base observer records 61 observations (anchor plus 60 holds) with
no error. Maximum estimated displacement from that anchor is 2.412 micrometres;
maximum estimated translation rate is 0.000078402 m/s. Maximum observed base
result age is 0.893 seconds, within the unchanged five-second observer bound.

A new receipt validator checks all 61 base observations against actual capture
stamps, simulation/capture times and RGB/depth evidence hashes, plus every hold
action's embedded base result and 30 Hz interval completeness. Unsupported
authority flags and missing evidence are rejected. The actual r2 receipt passes
both the declared-abort validator and this source-bound hold audit. Future owners
apply the additional check whenever hold-base fields exist; historical receipts
without those fields retain their narrower original scope.

This establishes the corrected capture/hold feedback path under this declared
native exception. It does not establish calibrated stop uncertainty, general
braking competence or external clearance. `scan_completed=false`,
`stop_qualified=false` and `motion_qualified=false` remain appropriate. Do not
repeat this diagnostic absent a changed implementation or failure hypothesis.

Full archive SHA-256:
`af398a19abdeb56c92225462d776988cce47b8e946860547a279171050f386f7`.
All failed r1 artifacts remain retained. No paid calls or unrelated process,
package or instance-lifecycle changes occurred.
