# Instrumented Wrist Motion Diagnostic

## Scope And Outcome

One explicitly approved simulator-only attempt, with a 0.008 rad excursion cap
and 60-action cap. The command target was +0.006 rad to leave headroom. Existing
raw stop/abort thresholds were unchanged. External clearance remained unknown;
this was not a strict benchmark trial. No paid model calls were made.

The diagnostic completed, but **motion qualification failed**. It used 35 actions,
36 captures and 140 physics-step samples over 1.167 seconds of controlled
simulation. Initial five-sample stopping passed. Ten ramp actions reached the
target; ten outbound holds failed to establish five consecutive stopped samples.
Ten emergency holds also failed final stop acknowledgement. Return was not
attempted, and the consumed approval was not reused.

Maximum measured excursion was 0.005999874 rad; maximum held-joint drift was
0.000009060 rad. No callback or source-integrity error was reported.

## Measurements

Speeds below are maximum absolute values across physics samples, not just
control-step endpoints. Independent speed is calculated from substep positions.

| Phase | Actions | Raw wrist speed (rad/s) | Position-derived speed (rad/s) | Stopped endpoints |
| --- | ---: | ---: | ---: | ---: |
| Initial hold | 5 | 0.014426 | 0.00010044 | 5 |
| Outbound ramp | 10 | 0.030060 | 0.041920 | 8 |
| Outbound hold | 10 | 0.016055 | 0.0015120 | 8 |
| Emergency hold | 10 | 0.014072 | 0.000060964 | 7 |

The upstream position-derived velocity and independently calculated finite
difference agreed within 1.55e-9 rad/s where both were available. Cached and
direct wrist positions matched exactly; history was available for all 140 samples.
The first upstream estimate uses history preceding the recorded substeps, so its
initial-hold maximum need not equal the independent recorded-window maximum.
Outbound tracking error peaked at 0.000023485 rad.

Base planar speed also exceeded its unchanged 0.002 m/s threshold at actions
9, 17 and 22: approximately 0.002061, 0.002027 and 0.002347 m/s respectively.
Independent base stopping remains unresolved.

## Interpretation And Next Step

Unlike the preceding stationary diagnostic, this trace shows the position-derived
estimator responding to commanded motion. It does not qualify reverse motion,
braking, external clearance or task competence.

Eight ramp endpoints were labeled stopped despite movement within those control
steps. This is not by itself a false-stop bug: an instantaneous endpoint can be
stationary after earlier movement. It does mean endpoint checks must not be
interpreted as evidence of stationarity throughout an entire control interval.

Next: replay stationary and moving traces against candidate whole-window stop
semantics offline, with explicit uncertainty and independent base-observation
requirements. Do not promote an estimator to stop authority, relax thresholds,
or repeat the same probe without a separately justified, approved protocol.
Phases 5-7 remain open; matched hybrid/task comparisons are still downstream.

## Evidence

Private run: `runs/wrist-motion-substep-20260923-r1`.
Analysis: `runs/wrist-motion-substep-analysis-20260923-r1/receipt.json`.
Raw receipt SHA-256:
`6854d2b81d6878fe1d6e577f027e7391c66cbd6c95a2c772f0d561e3a9d6630e`.
Executed runner and recorder source snapshots are retained with source hashes.
The complete run was copied locally and checksum-compared against the host with
no differences. Raw data and licensed assets remain private.

Focused analysis/driver tests: 14 passed. Full private suite: 988 passed, one
existing skip. Analysis script and its tests pass Ruff. The run log also matches
the host by checksum; no GPU compute processes remained after completion.
