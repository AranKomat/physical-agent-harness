# SAM Large Live Shadow Preflight

## Scope

Private run `sam-live-shadow-preflight-20260922-r2` passes the bounded
zero-action co-residency and warm-age test on one RTX 4090 (24,564 MiB).
BEHAVIOR, frozen Behavior-Skill, Grounding DINO and SAM 2.1 Large were resident
together. No GPT calls, training, simulator object poses or segmentation oracle
were used. No controller inputs, actions or strict admission gates changed.

Three native captures used the ordinary radio seed-0 start. Each checked
unchanged simulator time (0.3416666845 s) and exact 61-value proprioception.
Policy inference ran, but zero actions were applied. SAM ran in a separate
loopback worker after policy and grounding, using only original detector boxes,
legally captured RGB-D and bound calibration. Its outputs were logged only.

The worker encoded each image once, segmented each accepted box, then partitioned
all valid mask pixels using the prior fixed factor-4 depth-connectivity rule.
That factor is a diagnostic midpoint, not a qualified contact threshold. All
components are retained; no preferred object patch is chosen.

## Results

| Measure | Cold capture | Warm capture 1 | Warm capture 2 |
| --- | ---: | ---: | ---: |
| Native capture | 411 ms | 454 ms | 430 ms |
| Policy inference | 18,927 ms | 102 ms | 101 ms |
| Grounding worker | 925 ms | 155 ms | 164 ms |
| SAM + depth worker | 714 ms | 142 ms | 119 ms |
| SAM RPC | 953 ms | 313 ms | 278 ms |
| Observation age at SAM return | 21.589 s | 1.217 s | 1.177 s |

Age starts at the native observation timestamp, after rendering and before
evidence storage; it includes the sequential policy/grounding/SAM path. It ends
before writing derived SAM artifacts. It is not camera-exposure-to-control
latency, nor moving throughput. The predeclared warm limit was 2 s; cold was
reported separately, not treated as fresh. Any future moving consumer must
warm up first and obtain a new observation, not reset an old timestamp.

Peak GPU usage sampled at approximately one-second intervals was 21,869 MiB
(21.36 GiB), leaving 2,695 MiB against reported capacity. The stop threshold was
23,552 MiB. This is sampled capacity at one stationary start, not a guaranteed
peak or proof of no performance interference while moving.

Each capture produced two masks: a television and a detector-labeled robot
gripper. Visual inspection of the native head image confirms the latter box is
on the fireplace, not a gripper. No accepted radio box exists in this view.
Thus this exercises actual live segmentation/partitioning but does not qualify
live radio identity, radio-part association or contact geometry. All six
partitions passed exact valid-pixel preservation and evidence-binding checks.

## Failure, Verification and Backup

Attempt r1 stopped on its first SAM result: the predictor exposes thresholded
binary masks as float32, while the splitter correctly requires boolean masks.
The adapter now verifies every value is 0 or 1 before conversion; logits,
nonfinite values and malformed dimensions are rejected. No thresholds, prompts
or scene settings changed for r2. Both attempts applied zero actions.

Seventy-six focused private tests pass, covering the adapter, bindings, malformed
results, partition preservation, existing geometry and launcher contracts.
Ruff passes. This turn did not rerun the complete public suite; public changes
are documentation only, and experiment scripts remain in the private lab.

Both runs are fully backed up locally and checksum-rsync comparisons are clean.
All owned workers exited; post-run GPU allocation was zero. The instance remains
running. The successful `shadow-owner.json` SHA256 is
`bdcd7f28d9ba3845599b571ee6f08fcd859ddaf06f607bde7b63f5b1178f6efc`.

## Decision

Keep SAM Large plus measured depth patches as a shadow candidate; further model
search is not required before the next test. Next, connect this logging to a
bounded frozen-policy approach trace with real radio views, preserving policy
inputs/actions and measuring capture cadence and source age while moving.
This preflight hook currently exists only in the private no-motion runner.

Do not enable classical/contact control from these results. Moving localization,
low-space clearance, requested-part association and cross-view geometry remain
unqualified. A positive shadow result does not by itself advance those gates.
