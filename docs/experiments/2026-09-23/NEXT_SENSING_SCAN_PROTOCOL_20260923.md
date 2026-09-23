# Proposed Exploratory Sensing Scan

Status: **explicitly approved by the user on 2026-09-23 ("both approved")**.
Fresh captured-posture geometric checks now pass; see the
[preflight report](LIVE_DISCOVERY_SCAN_PREFLIGHT_20260923.md). Native monitored
execution remains pending, and those receipts are not live motion authority.
The [joint-monitor follow-up](GLM_ROUTING_SCAN_MONITOR_20260923.md) passes a
120-sample retained hold replay; native base monitoring and geometric allowance
for tracking error remain open. No stop qualification follows from that replay.
No native scan has run yet. Approval covers one exploratory scan within the
bounds below; earlier 0.01-rad wrist-probe results do not qualify this motion.

## Question

Can a bounded full-arm sensing movement obtain useful new low-body depth while
preserving measured robot control? This is not strict navigation qualification
or task execution. The robot-only checks identify candidate #67 as a useful
starting intent: 299 optimistic visible samples, smallest maximum joint change
among the four continuously self-separated retained paths (1.504 rad).

See [the retained survey](WRIST_VIEW_SURVEY_20260923.md). Those historical joint
targets and camera transforms are not live execution authority.

## Bounds

- Existing simulator and R1Pro sensors only; no physical robot.
- One attempt, no automatic repeat or replacement start.
- No base translation/yaw command, object manipulation or intended contact.
- At most 1.6 rad departure per active arm joint from the fresh measured start.
- Commanded joint speed at most 0.1 rad/s. Measured overshoot is an abort signal,
  not permission to enlarge the bound.
- At most 600 total control actions, including preflight and braking/hold actions.
- Reserve braking/hold budget before admitting the outbound trajectory. Reject
  profiles whose speed/acceleration limits cannot fit the remaining budget;
  never speed up to fit it. No automatic return motion.
- No paid calls, model downloads, system changes or instance lifecycle actions.
- Keep the unrelated CPU workload isolated; use the existing low-priority CPU
  affinity and one owned actuator process.

### Offline Command-Profile Check

Private `scripts/sensing_scan_profile.py` prepares only seven-joint target arrays;
it has no actuator transport. A piecewise-constant acceleration profile is
integrated twice with SciPy `PPoly`, giving a triangular/trapezoidal velocity
profile. Fixed limits are 0.1 rad/s and 0.1 rad/s squared. Every joint follows
the same scalar path fraction, preserving the straight joint-space path tested
by the geometric checker. Duration is rounded upward to 30 Hz intervals; time
is never compressed to satisfy the budget.

Reserve 20 initial and 60 final hold actions. A departure of 1.50404024 rad
needs 482 motion actions, 562 total. The maximum 1.6-rad departure fits in 590
total actions. Zero displacement produces hold targets only. Invalid limits,
nonfinite values, out-of-limit targets and oversized departures are rejected.

Six tests pass for continuous-profile-derived command-rate bounds, acceleration
differences, held endpoints, straight-path preservation, zero/tiny/full-range
departures and rejected inputs. Ruff passes. This does not establish measured
tracking, physical acceleration, stopping or clearance, and is not a native
experiment. Fresh-state admission remains open; the larger-scan authorization
has now been received.

## Required Preparation

1. Verify current host, robot assets, codec and relevant source hashes.
2. Obtain a fresh paired-render RGB-D/proprio capture, preserving actual capture
   times and unchanged simulation-time/proprio checks across render-only updates.
3. Rebuild the candidate from the current posture. Reject out-of-limit joints,
   departures above the cap, missing calibration or source mismatches. Do not
   simply replay the sequence-416 path or retimestamp its evidence.
4. Recheck continuous authored-hull self-separation at the declared diagnostic
   margin from the new start. This is necessary but not scene clearance.
5. Check observed scene obstacles; retain near-start robot ambiguity. Any concrete
   obstacle rejection blocks the scan. Missing coverage remains unknown.
6. Freeze the trajectory, action/time budget, monitoring thresholds and receipt
   schema before the first movement command. A partial scan is a recorded result,
   not a reason to extend the trajectory.

## Monitoring And Interpretation

Retain full named-joint substep telemetry, legal base-motion estimates, source
captures, commands, tracking errors and all abort causes. Keep evaluator-only
truth separate and unavailable to control. Missing/stale/nonfinite telemetry,
loss of a required measurement, budget exhaustion, unexpected base movement,
joint envelope violation or a declared tracking-error violation aborts outward
motion. Use only the predeclared hold/stop budget afterward; no improvised retreat.

Existing strict stop acknowledgements remain unchanged. Position-difference or
RGB-D estimates may be shadow diagnostics, not a silent replacement stop gate.
Unknown external clearance is explicitly exploratory throughout. Native contact
and stopping qualification are not established by completing the scan.

Measure new depth-supported low-body samples, observation timing, control
tracking, commanded/measured travel, stop outcome and encountered ambiguity.
Keep the original 1,031 diagnostic sample set only for a labeled retained-frame
comparison; a new posture/episode requires its own source-bound coverage set.
Do not compare different sample denominators as if they were the same coverage.

## Exit And Next Decision

Back up raw receipts and evidence, checksum the copy, reap only owned workers,
and leave the shared instance running. Report aborted and failed attempts.

If fresh preflight cannot admit this diagnostic, state the specific blocking
measurement rather than cycling through more retained camera poses. If it runs,
use its new observations to determine whether active sensing materially reduces
the gap; do not proceed automatically to base transit or grasping.
