# Target-Directed Exploratory Transit

## Scope And Authorization

The user authorized **one simulator-only target-directed probe capped at 10 cm**,
with unknown clearance explicitly recorded and experimental stopping checks.
This does not qualify benchmark motion, authorize deployment on a real robot,
or change the strict default gates. There is no automatic retry or VLA handoff.

The low space around the robot remains outside current camera coverage. The
coverage audit is a limitation, not a collision-free certificate. This experiment
asks whether a small sensor-directed base intervention is operationally possible;
it cannot establish that the route is safe or that the task is solved.

## Predeclared Procedure

- Ordinary public-test radio instance 301, seed 0, frozen Behavior-Skill weights.
- Fixed instruction: `Move to the radio receiver on the table.`
- 768 native policy actions in 32-action prefixes, with synchronous pinned
  GroundingDINO RGB/depth grounding. No GPT calls or policy training.
- One subsequent exploratory transit, only if current radio grounding is
  unambiguous and the experimental stop monitor becomes ready.
- Use robot-only FK and adjacent measured head-depth registration for base
  motion, and physics-substep joint position differences for joint stopping.
  No simulator object, robot-base or world poses enter control.
- Translation at most 0.03 m/s, zero commanded yaw. Stop driving by 8 cm of
  commanded integral or measured path, reserving 2 cm before the 10 cm measured
  abort bound. Estimator error and within-step motion mean this is not a
  physically certified distance guarantee.
- Reobserve after every action. Target loss, invalid tracking, excessive drift,
  motion bounds or timeout terminate forward commands and trigger bounded
  zero-base braking. No blind forward continuation.
- Persist commands, evidence identities, monitoring outputs, abort reasons and
  cleanup status. Keep original native-velocity stop results separate from
  experimental position/depth-based candidates.

## Dense Offline Stop Evidence

Before enabling this mode, the retained r2 zero-base hold was checked at every
adjacent control boundary, rather than using only five-tick endpoint changes.
All 60 depth/FK pairs passed the unchanged registration fit checks. The first
pair exceeded the stationary limits; the remaining 59 were candidates.

The causal trailing-five-pair maximum produced four not-ready windows, one
nonstationary window and 55 stationary candidates. Limits were 0.002 m/s
translation norm and 0.005 rad/s absolute yaw. No rejected pair was replaced
with zero motion. Information eigenvalues were retained descriptively, not
used to invent an observability certificate.

This is a single correlated trace, not a calibrated stopping test. Joint-only
results and caveats are in `JOINT_STOP_SHADOW_20260922.md`; clearance limitations
are in `EXTENDED_VIEW_CLEARANCE_20260922.md`.

## Native Result

The single approved attempt completed. It did **not** solve the radio task and
does not pass strict Stage 4. No second attempt or VLA handoff was launched.

| Quantity | Result |
| --- | --- |
| Frozen-policy approach | 768 native actions |
| Exploratory actions | 6 pre-hold + 80 translation + 6 final-hold = 92 |
| Total native actions | 860 |
| Commanded translation integral | 8.00 cm |
| Estimated full path, including settling | 6.672 cm |
| Estimated translation-phase path | 6.465 cm |
| Estimated pre/final hold paths | 0.126 / 0.082 cm |
| Estimated net horizontal displacement | 6.551 cm |
| Net component along initial target direction | 6.457 cm |
| Net lateral component relative to that direction | 1.106 cm right |
| Estimated net yaw change | 0.416 degrees |
| Maximum translation-phase estimated speed | 0.02487 m/s |
| Maximum recorded capture-to-command latency | 2.233 s |
| Exploratory phase wall time | 224.7 s |
| Abort / blind-braking actions | None |
| Physics feedback | 368 samples; complete, no dropped rows; callback removed |
| GPT / paid API calls | Zero |

Fresh target grounding remained accepted throughout the exploratory phase. A
manual check of the final head image confirms that the selected box contains
the red radio on the table, not a robot hand. This is a final-frame check, not
new per-frame ground-truth annotation. The final visible-surface estimate was
approximately `(1.119, -0.486, 0.577)` meters in the current base frame; this is
not a power-button location or a full object pose.

Both pre-hold and final-hold experimental stopping conditions passed after six
actions. The final joint-window maxima were 0.00122 rad/s and 0.0000255 m/s for
fingers. The existing raw proprioceptive settled check also happened to pass at
the final capture; that does not resolve its earlier inconsistent traces.

The useful conclusion is that this sensing/command path can perform one small
target-directed intervention and stop in this scene. The roughly 1.1 cm lateral
deviation and below-command displacement mean tracking is not exact. All motion
values are depth/FK estimates, not independent ground truth. They do not prove
collision avoidance, accurate long-range localization, real-time control,
successful policy handoff, generality across starts, or radio completion.

## Verification And Artifacts

- Full offline suite: **1,000 passed**; Ruff and diff whitespace checks passed.
- Includes 36 focused exploratory tests covering bounds, stale commands,
  target/tracking loss, termination, uncertain steps, interrupted execution,
  logger failure/cleanup and receipt persistence.
- All native probe source hashes match the local implementation.
- The approximately 609 MB private run was downloaded locally. A checksum-mode
  rsync dry-run reported no differences. Raw images, video, robot assets and
  simulator data are not included in the public repository.
- Owned native, policy and grounding workers exited. The rental instance was
  left running as requested.

Private run ID: `target-transit-exploratory-20260922-r1`.
Native receipt SHA-256:
`9c8aad77b797c8e9a5db8af854a0ca24c11057202d9693a41f7b862e56f9d662`.

## Next Experiment

The next informative test is a matched short policy handoff, not a larger drive:
give both conditions the same 768-action acquisition prelude, then compare a
zero-base control against the bounded intervention, reset the same frozen policy
in both conditions, and expose each to the same 384 policy actions. Log the
handoff observation and first actions. This would be another separately labeled
unknown-clearance exploratory experiment, not strict benchmark admission, and
requires authorization for the additional motion. The current one-probe approval
has been consumed. Strict Stage 4 remains blocked on clearance and broader
moving-localization qualification.
