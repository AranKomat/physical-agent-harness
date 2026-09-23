# Offline Wrist Stop-Window Replay

## Protocol

Replay the complete stationary and instrumented-motion traces without new native
actions or model calls. Compare the existing 0.006 rad/s wrist limit against:
control-endpoint raw velocity, maximum absolute raw velocity over four physics
samples, and maximum absolute position-derived interval velocity over the same
control action. No threshold search or runtime gate changes.

For each action, reconstruct four interval velocities from the pre-action wrist
position and the four post-physics positions. Validate finite data, 120 Hz physics
intervals, agreement with capture timing, sequential callback/action membership,
complete action accounting, and the final position's capture correspondence.
Keep recorded whole-robot endpoint decisions separate from wrist-only diagnostics.

## Results

Counts below are windows below the wrist limit, not qualified whole-robot stops.

| Trace / phase | Windows | Raw endpoint | Raw full window | Position-derived full window |
| --- | ---: | ---: | ---: | ---: |
| Stationary hold | 30 | 23 | 0 | 30 |
| Motion: initial hold | 5 | 5 | 0 | 5 |
| Motion: outbound ramp | 10 | 8 | 0 | 0 |
| Motion: outbound hold | 10 | 8 | 1 | 10 |
| Motion: emergency hold | 10 | 7 | 0 | 10 |

The position-derived window criterion separates this trace's ramp from its holds
at the existing threshold. Raw full-window velocity would reject every stationary
control interval. Merely sampling raw velocity more frequently therefore does not
resolve the stop qualification problem.

Endpoint stillness and whole-window stillness are distinct claims: a ramp can
settle before an endpoint is sampled. The eight ramp endpoints below the raw
limit do not by themselves prove a false instantaneous measurement.

## Limits And Decision

- Finite differences measure interval-average velocity. They cannot rule out
  within-physics-step motion that returns to the same sampled position.
- This is a wrist-only diagnostic using two traces, not a calibrated velocity
  error bound or a reverse/braking qualification.
- Derived and upstream estimates share position measurements. Their agreement
  validates calculation consistency, not independent sensor accuracy.
- Full-window base and other-joint stationarity were not measured here.
- No existing gate has been relaxed, replaced or declared qualified.

Next native work should first establish an explicit stop-observation contract:
the required quiet interval, measurement uncertainty, and independent base-motion
evidence. Validate that contract against movement and braking before granting it
execution authority. Another identical wrist probe will not address the missing
base evidence or external clearance. Phases 5-7 remain incomplete.

## Reproducibility

Private script: `scripts/replay_wrist_stop_windows.py`.
Output: `runs/wrist-stop-window-replay-20260923-r1/receipt.json`.
The output records per-window measurements and input receipt hashes.

Inputs, both previously checksum-backed-up locally:

- `wrist-hold-substep-20260923-r1`, receipt SHA-256
  `d60f1c4a164941db1d42b1c4770d749dd822176f46a5343987587d01f5e85935`.
- `wrist-motion-substep-20260923-r1`, receipt SHA-256
  `6854d2b81d6878fe1d6e577f027e7391c66cbd6c95a2c772f0d561e3a9d6630e`.

Nine focused tests pass, including net-zero endpoint displacement with intervening
movement, corrupt callback/timing data, both trace schemas and JSON serialization.
Ruff passes. No simulator was started; native actions and paid calls were zero.
