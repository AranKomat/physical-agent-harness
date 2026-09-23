# Phase 5A Target-Support Analysis

Date: 2026-09-24  
Run: `live-fusion-dense768-20260924-r5`  
Scope: read-only analysis of retained live-fusion artifacts; no model calls,
robot actions, or motion authority.

## Result

The corrected post-run validator reports 13/13 bound, fresh, target-bearing
fusion boundaries through policy sequence 768. Every row contains tracker
`(id=0, generation=0)` and `motion_authorized=false`.

For each boundary, the highest-support target patch was selected only for this
descriptive stability check. Its support counts were:

`2381, 1695, 1504, 1491, 1491, 1787, 1845, 2217, 2276, 3361, 2925, 3073, 2987`

The selected patch medians have axis ranges of approximately:

| Axis | Range |
| --- | ---: |
| X | 0.016189 m |
| Y | 0.022208 m |
| Z | 0.027090 m |

The maximum distance from the 13-point mean was 0.021220 m. This is useful
internal consistency evidence for the target-support stream across the dense
window.

## Why this is not a staging result

The corresponding pose report labels every estimate:

`shadow_camera_motion_not_base_or_clearance_authority`

Although the frame field is `local_map` and the reported confidence is `1.0`,
that scope is not a calibrated robot/world pose authority. The run also has no
qualified clearance, reachability, or visibility callbacks. The public staging
resolver correctly requires all three signals and rejects unknown values.

Therefore this analysis does **not** authorize or propose a base endpoint, and
does not qualify localization accuracy, external clearance, stopping, transit,
arm staging, contact, or task success. The target coordinates must remain
evidence for later review only.

## Provenance

The source artifacts remain on the GPU host at:

`/workspace/physical-ai-lab/runs/live-fusion-dense768-20260924-r5/`

| Artifact | SHA-256 |
| --- | --- |
| `fusion-report.json` | `e88bd1a2e0977883383cc438a54031b39ea5865c7cc959ebfb3f40f887a39097` |
| `pose-report.json` | `0f7d83c436b9de0ece8bf7575a522dd4229def26e189ab4c7bb5877dbab55939` |
| `posthoc-validation.json` | `a3cc8d02df40f6d9f0832db3b2593ab9230d77ec2cb95526a65be94f0140a54e` |

## Next gate

Do not repeat dense fusion. The next phase-level experiment requires a changed
source of authority: a legal calibrated pose plus real clearance,
reachability, and visibility callbacks, or a simulator/camera configuration
that supplies equivalent evidence. Until then, continue only CPU-side
contract/replay work and preserve this result as positive fusion evidence.
