# Reverse-Direction Localization And Stop Diagnostic

## Predeclared Question

Does the refreshed legal RGB-D/FK estimator retain its moving/braking fidelity
when the base command direction is reversed? Prior forward results were used
to identify render freshness; repeating that identical trace is not validation.
This is a directional holdout at the same fixture/seed, not independent scene
or seed coverage and not general stop qualification.

Run name: `base-render-reverse-20260924-r1`. One native attempt, no automatic retry.
Operator authorization covers bounded simulator diagnostics without repeated
approval; unknown clearance remains explicitly exploratory.

## Frozen Recipe

- Original physics and frozen policy codec; no solver/gain/limit changes.
- Public radio instance 301, seed 0, ordinary reset/load settling.
- Five initial holds; require existing raw preflight checks before the pulse.
- Five forward-axis commands at -0.01 m/s; nominal signed travel -1.667 mm.
- Fifteen braking holds; total cap 25 native actions.
- Existing whole-body drift/velocity abort checks and stop thresholds unchanged.
- Retain normal and paired render-only captures with distinct IDs and exact
  unchanged-state checks; neither refreshed stream nor evaluator truth changes control.
- Retain complete joint substeps and isolated evaluator pose stream.
- No policy inference, paid calls, instance lifecycle changes or unrelated process changes.
- One owned low-priority process restricted to four CPU cores; bounded timeout.

## Analysis Before Any Promotion

Apply the unchanged legal refreshed RGB-D/FK estimator first. Only after it
finishes, compare its estimates to the isolated evaluator stream. Report every
interval, fit rejection, latency, source/state mismatch and failed attempt.
The diagnostic target is maximum translation error <= 0.000033 m, not a newly
calibrated guarantee; compare all pulse/braking intervals at the existing 2 mm/s
base threshold. Report rotation error and complete joint-window results too.
Passing cannot establish between-frame peak velocity or universal pose uncertainty.

Any failure leaves stop authority false. Do not tune thresholds or timestamp
offsets on this trace and call it validation. No new navigation or grasp action
follows automatically from a passing result. Phase 5 remains partial pending
broader calibration and external clearance.

## Completed Result

The one native attempt completed 25/25 actions and 26/26 paired captures, without
callback/integrity errors or a latched abort. Raw final stop acknowledgement is
false and remains authoritative for this runner. No native retry was performed.

The unchanged refreshed RGB-D/FK replay completed all 26 observations:

| Measurement | Result |
| --- | ---: |
| Maximum observed translation error | 6.590 micrometres |
| Predeclared diagnostic target | 33 micrometres |
| Maximum observed rotation error | 0.000005511 rad |
| Moving intervals detected above 2 mm/s | 5/5 |
| Braking intervals below 2 mm/s | 15/15 |
| Maximum interval-speed magnitude discrepancy | 0.07695 mm/s |
| Maximum estimated braking interval speed | 0.05902 mm/s |
| Evaluator-only signed pulse travel | -0.43389 mm |

The reverse trial passes the declared observed-error target. Actual travel is
about 26% of the nominal magnitude; no inverse-gain correction was applied.
This is not sufficient evidence for speed tracking or long-distance transit.

The combined legal joint/RGB-D replay has 21 full five-interval windows, including
11 shadow stop candidates. Final-window maxima are 0.03699 mm/s planar,
0.00004566 rad/s yaw and 0.03778 of the joint velocity limits. Its allowed
per-endpoint planar position-error margin is 32.72 micrometres, NOT a measured
uncertainty guarantee. Evaluator poses are excluded from this window computation.

The prior forward result was 16.80 micrometres maximum observed translation
error. The new reverse result supports directional transfer of refreshed capture
timing on this fixture. It does not establish independent-scene calibration,
between-observation peak speeds, or confidence bounds for stopping. Strict
stopping, clearance and Phases 5-7 remain unqualified.

## Artifacts And Verification

Full native trace and log are archived locally under the private lab runs:
`base-render-reverse-20260924-r1.tar.gz` (approximately 103 MiB).
Remote/local SHA-256 match:
`c48144546df7ff371a1c9f82a49fde22b2e084368fd798025a8b40c4543c029c`.
The archive has been extracted locally, including all RGB-D and substep evidence.

Local analyses:

- `base-render-reverse-rgbd-20260924-r2/receipt.json`:
  `44832ea90213e711247eec993913c156e42a056576cc3cdc40396e845a5a4832`.
- `base-render-reverse-stopwindows-20260924-r1/receipt.json`.

The first remote replay attempt stopped on missing Open3D after writing an
incomplete receipt. A separate native-environment import check lacked yourdfpy.
The complete unchanged replay ran locally, where both dependencies were already
available. These setup failures were not estimator failures; the native trace
was not repeated or changed. The initial local test invocation lacked the
script module path; the correctly configured focused suite passed 35 tests.

The native process exited and released GPU allocation. No unrelated process or
instance lifecycle was changed; no paid calls occurred. Next pursue a declared
multi-condition uncertainty/stop study and a sensing strategy that actually
covers staging, not another identical short pulse.
