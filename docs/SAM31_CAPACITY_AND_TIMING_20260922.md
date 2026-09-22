# SAM 3.1 Full-Stack Capacity and Timing

## Completed No-Motion Experiment

One RTX 4090, frozen Behavior-Skill, native radio simulator and SAM 3.1 resident.
SAM 3.1 replaced the detector/SAM 2 sidecars for this test; they were not also
loaded. Three fresh calibrated RGB-D captures, three policy inferences with
actions discarded, and three independent text prompts per capture. Simulator
time and proprioception were checked unchanged before and after each cycle.

| Measure | Result |
| --- | --- |
| Capacity / paused-world checks | Pass, 3 cycles |
| Actions applied / GPT calls | 0 / 0 |
| Peak sampled GPU memory | 23,194 MiB (22.65 GiB) |
| Headroom at sample peak | 1,370 MiB (1.34 GiB) |
| Predeclared abort threshold | 23,552 MiB |
| Warm SAM three-prompt worker time | 0.552 / 0.488 s |
| Warm observation age at SAM return | 1.050 / 1.001 s |
| Native capture time | 0.404-0.448 s |
| Policy inference | 0.101-0.171 s |
| Native scene startup | 199.94 s |

One television prediction and zero radio/gripper predictions occurred in every
cycle. This start does not qualify positive radio tracking. Sessions are reset
between captures: this is inference capacity, not an online tracking benchmark.
Sampled GPU memory can miss brief peaks. Moving simulation, growing tracker
state and additional objects can increase demand; do not call the headroom ample.

The first attempt failed before simulator startup because the SAM worker created
the evidence directory before the existing stack owner claimed its output path.
The retry delays opening that store until a request exists. Both receipts are
retained; all owned workers exited. No simulator/policy dependencies changed.

Private runs: `sam31-capacity-20260922-r1` (startup failure) and
`sam31-capacity-20260922-r2` (pass). The passing run is backed up locally with
checksum-rsync verification.

## Parallel CPU Timing Audit

The earlier moving SAM 2 trace was audited while the GPU capacity run executed.
This is analysis of existing evidence, not a post-replacement speed measurement.

- Dense interval: actions 384-512, 32 capture gaps.
- Four gaps exceeded 2 s; all four immediately follow model boundaries.
- Median non-boundary gap: 1.599 s.
- Median model-boundary gap: 3.078 s; maximum: 3.270 s.
- Recorded policy inference at those boundaries: 0.197-0.200 s.

The boundary includes synchronous grounding, segmentation, serialization and
policy work. It is not defensible to assign the entire excess to any one model.
Capture also serializes native images before returning. Moving only segmentation
off-thread will not establish continuously fresh observations by itself.

## Prefix Check

The low-latency SAM 3.1 configuration was run with only the first three images
available (actions 352, 384, 416), withholding all later images. Initial prompting
and frame 0 matched the prior 14-frame run exactly. Later IDs, scores and boxes
matched, but masks differed by 3 and 4 pixels (IoU 0.99882 and 0.99831).
Thus the predeclared exact-output prefix check failed. This small boundary change
is not evidence of an identity failure or proof of future leakage. A second
three-frame run reproduced all saved arrays exactly at all three frames. The
difference is therefore reproducible and associated with clip length in this
probe, rather than explained by the measured same-prefix repeat. Its precise
upstream cause is not established. Do not advertise the offline predictor as a
qualified streaming interface; deliver only arrived frames and do not revise
already-consumed outputs with later observations.

Private prefix runs: `sam31-prefix-20260922-r1` and `sam31-prefix-20260922-r2`.
The full public suite passes 1,080 tests; 48 focused private tests and Ruff pass.

## Next Gate

Follow-up: the [incremental qualification report](SAM31_INCREMENTAL_SHADOW_20260922.md)
records the completed live level-1 encoding test, an invalidated incremental
adapter attempt, its frame-index correction, and a passing bounded moving shadow
run. Corrected warm result age is 483 ms median / 540 ms p95. This does not qualify
continuous high-rate tracking or accurate geometry.

Stationary capacity and one bounded moving shadow are established. Keep native
rendering and stepping on the simulator-owning thread. Give the tracking worker
only already-captured images, bound its queue, retain observation and availability
timestamps, and explicitly record overflow/loss rather than silently treating
skipped views as a continuous track. Results remain shadow-only for the next
policy-only approach. Do not move on to classical transit or A/B on capacity alone.
