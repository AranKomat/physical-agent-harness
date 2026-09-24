# Phase 5D Retained Base Stop Audit

Two independent completed native BEHAVIOR transits were re-audited against the
existing control-facing stop predicate. This audit made no new robot actions or
model calls and did not tune thresholds from the results.

## Frozen Predicate

A stop window requires five consecutive current, source-bound pose intervals
plus a complete 21-sample physics joint window:

- base translation rate at most `0.002 m/s`;
- absolute yaw rate at most `0.005 rad/s`;
- arm/torso joint rate at most `0.03 rad/s`;
- finger rate at most `0.005 m/s`.

The audit also requires every retained action sequence to be consecutive, all
feedback to be complete, no hard abort or brake error, and more than half of the
declared move intervals to exceed the base stop threshold. Clearance remains
outside this test.

## Results

| Measure | 45 cm staging | 6 cm matched B |
| --- | ---: | ---: |
| Commanded speed profile | up to `0.049 m/s` | `0.03 m/s` |
| Move actions | 312 | 80 |
| Measured path | `0.451119 m` | `0.063865 m` |
| Moving intervals above stop threshold | 312/312 | 80/80 |
| Maximum measured move rate | `0.043958 m/s` | `0.024208 m/s` |
| Prehold max base rate | `0.0000591 m/s` | `0.0000762 m/s` |
| Final-hold max base rate | `0.0003915 m/s` | `0.0000785 m/s` |
| Final-hold max yaw rate | `0.0000706 rad/s` | `0.0000142 rad/s` |
| Final joint-window max | `0.001116 rad/s` | `0.000815 rad/s` |
| Final finger-window max | `0.0000384 m/s` | `0.0000384 m/s` |
| Prehold and final windows | Pass | Pass |

All four independent prehold/final stop windows pass, while every motion
interval in both traces is rejected as moving. Both traces retain complete
physics feedback and counted braking holds.

## Interpretation

This closes the **simulator control-facing base stop-discrimination subgate** for
the retained BEHAVIOR controller at commanded speeds through `0.049 m/s`. It is
appropriate evidence for stopping and re-observing before another bounded
simulator segment.

It is not a physical-hardware stopping-distance certificate, does not cover
higher speeds or different controllers, and does not qualify external clearance,
localization accuracy, navigation, or task success. Phase 5 remains blocked on
clearance and broader moving-localization evidence, not on another identical
base hold/move repeat.

The 45 cm input hashes match the published staging receipt. The 6 cm input is
read from the checksum-verified matched-handoff archive. The private audit output
is `runs/phase5d-base-stop-audit-20260924-r1.json`.
