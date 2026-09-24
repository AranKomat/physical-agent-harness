# Synchronous SAM Exploratory Transit

Run: `sam-live-transit-20260924-r1`. Started 2026-09-24 on the existing single
RTX 4090. No paid calls. User-approved exploratory scope, not strict qualification.

## Protocol

- Public radio instance 301, seed 1; frozen Behavior-Skill source/checkpoint/codec.
- 768 policy acquisition actions, followed by at most one exploratory base probe.
- Synchronous SAM 3.1 `radio` candidate acquisition and tracking using the pinned
  local source and checkpoint. No Grounding-DINO or GrabCut worker.
- Reacquisition is allowed only before a candidate is first found, never after
  probe selection. Selection requires one current candidate and pins its episode,
  generation and tracker ID. This remains a candidate, not verified identity.
- At each capture render and read fresh onboard sensors without advancing physics;
  reject any physics-step change while waiting for SAM. Original evidence clocks
  are retained. Two-second target-consumer age gate remains active.
- Deproject the dominant connected depth surface, requiring 80% of valid mask
  support. Do not merge disconnected background or load retained target positions.
- Existing exploratory controller unchanged: at most 8 cm commanded integral,
  10 cm measured-path hard abort, 260 total action ceiling including braking,
  joint drift, speed, continuity and stopping checks. Strict admission is false.
- SAM frame capacity is explicitly bounded at 320 to cover acquisition and probe
  captures; existing callers retain their smaller defaults and unavailable frames
  still raise. GPU reserve below 1 GiB aborts the owner.
- Low priority (nice 15), CPU affinity 19-22 inherited by owned workers. Only owned
  processes may be terminated; no instance or unrelated workload changes.

This is not a matched A/B comparison: fresh synchronous rendering changes capture
timing from older acquisition runs. No improvement or task-completion claim follows
from a completed controller trajectory alone.

## Preflight

The owner loads native Open3D, yourdfpy and pinned robot-only FK assets before
launching acquisition. Native trimesh remains at its original 4.5.1 version;
yourdfpy 0.0.56 was added without resolving/upgrading its dependencies. SAM build
checks source revision, clean source tree and checkpoint SHA. Policy loading keeps
its original manifest checks. Source hashes are stored in the owner receipt.

Public suite: 1,511 passed. Focused private streaming/owner guards: 13 passed.
Ruff passed on the new/changed live integration files.

## Outcome

Completed, with the declared exploratory probe passing and strict qualification
still false. All owned workers exited; GPU memory returned to zero. Full trace,
mask archives and rollout video (about 579 MiB total) were copied locally. The
receipt/hash audit passed independently on host and local backup.

| Measure | Result |
| --- | --- |
| Policy acquisition actions | 768 |
| Probe actions | 92: 6 prehold, 80 move, 6 final hold |
| Commanded integral | 8.0 cm |
| Measured RGB-D/FK path | 6.039 cm |
| Visible-surface planar range | 1.31527 m to 1.25320 m |
| Final experimental stop | Observed |
| Abort / braking retries | None |
| Capture/mask bindings verified | 119 |
| Pinned-track surface proposals | 94 |
| Physics feedback | 368 rows; callback removed, no truncation/error |
| SAM archive age, maximum | 0.678 s |
| Target consumption age, median / maximum | 1.157 / 1.266 s |
| Probe wall time | 148.36 s |
| Peak GPU memory | 23,121 MiB |
| Native task success (evaluation only) | False |

Range is a viewpoint-dependent visible-surface statistic, not object-center truth.
It is consistent with approach, but not an independent task verifier. Video endpoint
inspection shows the radio on the table with both hands still away; no grasp/lift
occurred. No evaluator object poses were supplied to control.

## Interpretation And Next Step

This closes the live SAM-to-exploratory-controller integration gap: acquisition,
fresh geometry, bounded target-directed travel, final observation and experimental
stop were all exercised together. It does not close strict Phase 5/6 clearance or
stopping qualification, nor demonstrate policy benefit or manipulation success.

Next move toward meaningful reachable staging, under a separately recorded bounded
exploratory protocol, with fresh geometry at each segment. Do not reuse these target
coordinates or generate another grasp batch from the old frame 704. Longer staging
needs an explicit memory/capture horizon and whole-body proximity review; the current
320-frame service is bounded and has only about 1.4 GiB peak GPU headroom. A fixed
6 cm movement should not become another repeatedly sampled microdiagnostic.

Public summary receipt: [SAM_LIVE_TRANSIT_RECEIPT.json](SAM_LIVE_TRANSIT_RECEIPT.json).
Private video: `runs/sam-live-transit-20260924-r1/stack/A/rollout.mp4`.
