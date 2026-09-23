# Provider Routing And Scan Monitor

## GLM Provider Preference

Operator preference is now recorded in
`configs/reasoning/glm-provider-routing.json`, referenced by the runtime template:

1. Together (`together`)
2. Baseten (`baseten/fp8`)
3. Fireworks (`fireworks`)
4. Parasail (`parasail/fp8`)
5. CoreWeave (`coreweave/nvfp4`)

The private live-discovery bridge consumes that policy. Before dispatch, it
selects the first listed healthy endpoint supporting images and the required
structured-output/reasoning parameters. Price validation and conservative
reservation still precede inference. The selected route is pinned for the
bounded run and logged with the endpoint metadata and provider-specific ledger.

Unlisted routes cannot be selected. A failed dispatched request does not cause
an automatic provider retry or release an unresolved billing hold. Historical
experiments retain their original fixed-provider scripts and receipts.

A public catalog check found all five routes and selected Together. This was
metadata access only, not paid inference or a quality/latency measurement.
`autoexact` was not an advertised endpoint tag. It remains an unconfigured
last-resort suggestion, not an enabled unrestricted fallback. Eight routing
tests cover preference order, unavailable/incompatible routes and fail-closed
behavior. The earlier 4,145-call ceiling remains exhausted; this preference
change does not authorize additional calls.

## Scan Joint Monitoring

The private `sensing_scan_monitor.py` adds a latched, non-actuating diagnostic
monitor for the approved exploratory scan. It requires all 22 named arm, torso
and finger joints and exactly four physics samples per control action. It
checks finite telemetry, callback/action order, approved 1.6-rad departure and
0.1-rad/s command limits, and reserves the final 60 of 600 actions for holds.

Explicit experimental feedback thresholds are 0.02 rad active-joint tracking
error, 0.15 rad/s position-derived active-joint speed, 0.003 rad held-joint drift
and 0.002 m finger drift. Raw velocities are retained, not quietly reinterpreted
as qualified stopping measurements. A threshold violation latches failure;
this component cannot issue either movement or braking commands.

Ten tests exercise valid intervals, bad telemetry, drift, speed, incomplete
intervals and the reserved hold budget. Retained replay through all 120 physics
samples of `full-body-stop-calibration-20260923-r1` passed, with zero new actions
or paid calls. Receipt: `scan-joint-monitor-replay-20260923-r1/receipt.json`.

This is NOT a native motion or stopping result. Base-motion observation,
fresh-episode geometric binding, and tracking-error allowance in the geometric
margin still need integration before the scan. The component explicitly reports
`motion_authorized=false`, `stop_qualified=false`, `base_monitored=false`.
