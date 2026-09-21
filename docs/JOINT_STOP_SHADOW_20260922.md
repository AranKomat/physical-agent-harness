# Position-Derived Joint Stop Shadow

## Result

A fresh native run recorded joint positions and native velocities during both
384 frozen-policy actions and 60 zero-base hold actions. The proposed **offline,
joint-only** position-derived check separated these intervals in this trace:

| Trace / phase | Ready control boundaries | Position-window stationary candidates | Instantaneous native-joint stationary |
| --- | ---: | ---: | ---: |
| Previous r2 / holds | 55 | 55 | 24 |
| Fresh r3 / policy | 379 | 0 | 118 |
| Fresh r3 / holds | 55 | 55 | 24 |

These are correlated windows, not independent trials or calibrated accuracy
scores. Policy/hold labels describe the controller phase, not independent
motion ground truth. An instantaneous native-velocity check and a trailing
window check also have different temporal semantics: the 118 disagreements
must not be presented as a measured native false-positive rate.

## Fixed Method

`experiments/behavior/joint_stop_shadow.py` accepts only complete, cleaned-up
FeedbackDiagnostic packets: exact 22 arm/trunk/finger names and units, unique
DOF mappings, finite samples, 120 Hz physics, four substeps per control action,
consecutive counters/timestamps, one phase, and no errors/truncation/dropped rows.
Malformed or gapped packets are refused, not interpolated.

Each candidate uses the maximum absolute position-derived velocity over the
trailing **20 physics intervals**. Limits remain **0.03 rad/s** for arm/trunk
joints and **0.005 m/s** for fingers. This uses every interval, not net endpoint
displacement; back-and-forth movement cannot cancel itself into a stop. The
first 20 samples are not ready. Policy and hold packets are evaluated separately
without cross-phase history. No future row changes an earlier valid window.

The native comparison uses the ending row's instantaneous velocities at the
same numerical thresholds. Base velocity is excluded from both joint-only
columns. Every output says `motion_authorized=false` and
`base_stop_evaluated=false`. No native stop gate or motor behavior is changed.

## Native Evidence

Private run `post-policy-feedback-20260922-r3` used the ordinary radio reset,
seed 0, the unchanged Behavior-Skill checkpoint/interface/instruction, 32-action
prefixes and the same 384-action exposure as the earlier diagnostic.

- **1,536 policy-motion physics samples**, followed by a separately installed
  logger's **240 hold samples**; both callbacks removed cleanly, no dropped rows.
- Policy-window maximum joint rates ranged from **0.307 to 5.475 rad/s**,
  well above the unchanged 0.03 rad/s criterion. All 379 ready policy boundaries
  were rejected by the position-window check.
- Both r2 and r3 holds produced 55/55 joint-stationary candidates after warmup.
- The existing **whole-robot stop still failed** in r3. It had 25/60 passing
  individual control samples and only two consecutive passing samples at the end.
  The diagnostic's operational completion flag is not stop qualification.
- No new classical translation/yaw, task-specific training, GPT call or runtime
  velocity-source substitution. Robot/world base positions are not read by the logger.

Source observations, videos and feedback remain private. The private driver
`scripts/evaluate_joint_stop_run.py` writes source hashes, per-row causal windows
and control-boundary aggregates into separate analysis files. Original receipts
are preserved. The rental remains running; owned experiment workers exited.

## Qualification Boundary

This supports a position-derived joint feedback workstream rather than raising
native velocity tolerances. It does not establish atomic getter timing, rule out
within-physics-step movement, prove real-sensor accuracy, evaluate base stopping,
or establish clearance/payload safety. Base motion must be measured from legal
sensors independently; classical transit remains gated on that and swept clearance.
