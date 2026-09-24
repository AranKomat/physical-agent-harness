# Coupled Base-Rate Diagnostic

## Predeclared Protocol

Run: `native-coupled-base-diagnostic-20260924-r1`.

This is a separately declared simulator-only diagnostic, not an automatic retry
for success. The preceding coupled round-trip aborted at its RGB-D/FK base-rate
gate. Retained RGB-feature/depth PnP also exceeded that rate bound, so selecting
the lower consecutive-depth estimate would not justify bypassing the abort.

The diagnostic preserves the fresh capture, coupled IK target, geometry
admission, joint/substep monitoring and base-rate gates. It adds a hard cap of
29 outward-profile actions, including the profile's 20 initial holds, followed
by the existing 60 reserved holds. An earlier gate failure takes precedence.
No return is authorized and round-trip success must remain false.

At each capture a separate write-only evaluator sink records native base-link
world pose, observation stamp, simulator time and capture time. These poses are
not added to legal observations, planner inputs or the controller's feedback.
Only retrospective analysis reads the sidecar. Full capture/sidecar association
and content hashes are checked before comparing rates.

The question is whether measured native base displacement corroborates the
sensor-derived rate, or whether sensor/FK error dominates it. The outcome will
guide the next correction, not authorize motion by itself.

External clearance remains explicitly unknown. This is not strict navigation,
stop qualification, manipulation or Phase 7 completion. Zero paid calls; the
existing GPU rental and unrelated CPU workload are left intact. Experiment
processes run at low priority on cores 19-22.

## Outcome

The diagnostic completed all 89 native actions: 29 outward-profile actions,
then 60 reserved holds. The unchanged base-rate gate triggered again at
observation sequence 63, before the diagnostic action cap could end the leg.
No return or endpoint success was claimed. The owner exited normally and GPU
memory returned to 0 MiB; the rental was not stopped or rebooted.

At that interval:

| Measurement | Sensor/FK monitor | Evaluator-only native pose |
|---|---:|---:|
| Translation rate | 29.337 mm/s | 0.03288 mm/s |
| Rotation rate | 0.018003 rad/s | 0.00002904 rad/s |
| Displacement from initial reference | 0.5575 mm | 0.000868 mm |

Maximum evaluator translation rate across all outward intervals was
0.05661 mm/s. The native pose evidence contradicts interpreting the monitor's
29.337 mm/s as actual base drift in this run. It does not identify whether
registration bias, moving robot pixels, depth/rendering error, camera FK, or a
combination caused the discrepancy. It also shows why agreement between two
sensor-derived methods was not sufficient: both can share error sources or
have insufficient precision for a 1/30-second finite difference.

The next correction is to the legal motion observer, not a relaxed threshold
or a different motor checkpoint. Retrospective evaluator poses remain excluded
from control. Any replacement estimator needs measurement-quality validation;
matching this one stationary-base trace is not general localization
qualification. Phase 7 remains incomplete.

## Evidence

- Native receipt SHA-256:
  `59809a8707f144a0a87c2602570dea777a44060038db12ef4fb93666cc24cf55`.
- Evaluator sidecar SHA-256:
  `d18716176ca2ae7a29ed038cab3524318cbdf3b612ddfa5071af699550e0a1c5`.
- Retrospective analysis: `runs/coupled-base-evaluator-analysis-20260924-r1`.
- Local backup verified: 93 captures, 549 unique RGB/depth artifacts, zero
  SHA-256 mismatches. Both joint and reserved-hold monitors reported no error.
- Local supporting tests: 42 execution/orchestration/analysis tests passed;
  46 existing public planning-adapter tests passed. These are not native phase
  completion evidence.
