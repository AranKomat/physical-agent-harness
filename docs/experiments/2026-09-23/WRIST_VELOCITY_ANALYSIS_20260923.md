# Wrist Velocity Follow-Up

## Scope

Offline analysis of the completed, failed [wrist probe](WRIST_PROBE_20260923.md).
No new robot actions, paid calls, threshold changes or motion authorization.
The original result remains failed: no sustained stop acknowledgement and no
return leg. This analysis does not qualify motion or external clearance.

The private analyzer verifies all 35 actions against 36 captures, matching
proprioception and contiguous same-session timestamps. Every control interval
is 0.03333333507180214 seconds. Input/source hashes match before and after.

## Evidence

| Phase | Samples | Post-action position span (rad) | Max raw speed (rad/s) | Max interval-mean speed (rad/s) |
| --- | ---: | ---: | ---: | ---: |
| Initial hold | 5 | 3.3523e-7 | 0.00478188 | 0.0000128669 |
| Outbound ramp | 10 | 0.00719883 | 0.00644801 | 0.02400909 |
| Outbound hold | 10 | 1.4640e-6 | 0.01076804 | 0.000876747 |
| Emergency hold | 10 | 4.3865e-7 | 0.01551091 | 0.0000117347 |

The first outbound-hold interval includes arrival at the target. Position spans
use post-action samples; interval means also use the preceding sample.
Three raw wrist-speed samples exceed the unchanged 0.006 rad/s stop threshold
in each of the outbound and emergency holds. Each also has one base-speed
threshold exceedance. Wrist telemetry alone therefore does not resolve all stops.

During the ramp, measured displacement is +0.00796950 rad, while coarse
endpoint-velocity integration gives -0.000038334 rad. During emergency hold,
the corresponding values are -5.24335e-7 and -0.00180338 rad.
These discrepancies motivate higher-rate inspection, **not a conclusion that
native velocity is wrong**. Endpoint samples can miss fast substep movement;
substituting 30 Hz finite differences could conceal oscillation.

## Source Inspection

Pinned BEHAVIOR commit: `b1979916ec1549b10a4e65e630bc6504a9af1b00`.
The proprioception path reads raw joint velocities. In
`OmniGibson/omnigibson/utils/usd_utils.py`, `get_all_joint_velocities(estimate=True)`
instead differences physics-step positions when history exists, but silently
falls back to raw velocity when it does not. Any diagnostic must log history
availability, not assume that requesting an estimate guarantees one.

The joint controller uses that estimator in its impedance branch, but the
evaluated R1Pro configuration sets `use_impedances: false`. Its existence is
not evidence that this run already used estimated velocity for control.

## Next Discriminating Test

A separately authorized stationary-hold diagnostic should record wrist position,
raw velocity, upstream estimated velocity, history availability, actual physics
dt and independent consecutive-substep differences. It should command no wrist
excursion, retain unknown-clearance labeling and preserve every stop threshold.
The proposed scope is at most 30 total hold actions; it has not run as part of
this analysis. The consumed excursion approval does not authorize a new attempt.

## Reproducibility

Private analyzer: `scripts/analyze_wrist_velocity.py`.
Private output: `runs/wrist-velocity-analysis-20260923-r1/receipt.json`.
Seven analyzer tests cover retained-data validation; the separate probe driver
has six tests. Raw traces and private scripts remain outside the public repo.
Original probe receipt SHA-256:
`5595635524d5bd18f8f388f80cddefbcfb4fa2fc78cb6f06489d7fb471e20688`.
