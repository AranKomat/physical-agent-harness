# Situated Long-Trace Tracking Diagnostic

Date: 2026-09-22. Retained-image GPU replay with partial hand occlusion and
explicit capacity resets. No new robot motion, policy inference or GPT calls.

## Source and Protocol

Used all 131 chronological head-camera captures from condition A of
`matched-target-handoff-20260922-r1`. This is a historical exploratory run,
not a newly qualified benchmark trajectory. Only its recorded RGB, depth,
intrinsics, proprioception and observation stamps enter the replay. Old detector
outputs and task-success fields do not guide tracking.

Visual screening found real partial hand occlusion around source action 924,
followed by clearer views. Older detection gaps at 1052 and 1180 occur while
the radio is visible: they must not be labeled object disappearance. Some early
old-detector candidates also occur before the radio is visibly in frame.
No old detector was rerun or restored to the live pipeline.

The selected SAM 3.1 adapter processes only arrived frames using the existing
weight/source pins, text prompt and current-frame raw-read guard. Its 32-frame
capacity is unchanged. The diagnostic explicitly creates new tracker state
before capture indices 32, 64, 96 and 128, corresponding to source actions
775, 807, 839 and 1180. IDs are separated by reset generation; no cross-reset
physical-identity association is inferred. This is a diagnostic reset wrapper,
not a change to the production worker.

Fresh recaptures at source sequences 768 and 860 have advancing capture times
and remain separate observations. The replay uses original capture order and
times, not a dictionary that overwrites equal control-sequence numbers.
Execution was bounded by an external 300-second timeout and completed normally.

## Results

| Measure | Result |
| --- | --- |
| Captures processed | 131/131 |
| Current-frame raw-image accesses | 262/262 |
| First radio detection | Action 416, capture index 13 |
| Positive captures thereafter | 118/118 |
| Capacity resets with immediate detection | 4/4 |
| Tracking median, excluding first frame | 170 ms |
| Reset-frame inference | 208-214 ms |
| Peak torch allocated / reserved | 6,221 / 6,648 MiB |

Eleven paired full-frame/crop panels were inspected, including reset boundaries,
partial hand occlusion at 924, the later clearer view at 956, and changed views
at 1052, 1180 and 1244. The masks remain on the radio in those inspected panels;
the crossing hand is not simply substituted for the target. This is qualitative
review, not pixel ground truth or proof that every predicted mask is correct.

All mask artifacts were downloaded and hash-checked against the report, and
each row was bound back to its original RGB/depth observation. GPU memory returned
to 0 MiB after worker exit. The instance remains running as requested.

## Limits and Decision

This supports bounded capacity-reset handling and tracking through one partial
hand occlusion. It does **not** qualify complete disappearance/reappearance,
similar-object distractors, physical identity across resets, or a continuous
unbounded tracker. Most source captures are from a near-stationary interval;
118 positives are correlated observations, not independent trials.

The earlier [25-frame reset failure](SITUATED_TRACKING_RESET_20260922.md) remains
valid: a reset there lost a radio that uninterrupted tracking retained. Four
successful resets here do not override that failure. Keep remembered semantics
separate from current geometry and treat failed reacquisition as unknown.

All 25 prior and all 131 current head-camera calibrations lack camera-to-map
extrinsics. In this trace, 128/130 wall-time gaps exceed the existing two-second
freshness bound (median 2.447 s, maximum 19.812 s). No freshness threshold was
changed, and no map pose or association proof was fabricated. GPU-only inference
timings are not live end-to-end latency measurements.

**Next priority is the native timing/localization gate**, not another SAM model
comparison: retain dense, source-bound observations and qualify legal camera-pose
estimates before attempting cross-view metric association. The existing depth,
clearance and stopping prerequisites for hybrid motion remain unchanged. A true
lost-target/distractor trace remains needed for identity qualification, but is
not a reason to block all other sensor-integration work.

## Reproduction Records

- Private run: `situated-long-replay-20260922-r1`; 131 mask archives, report,
  inference log, local audit and review sheet retained.
- Source receipt SHA-256:
  `efed8b09b3fdc2e014d783b929101d87a053d8a7785589613c7a8ec4a6b6f9c2`.
- Replay report SHA-256:
  `3edd917d23252ee972369ae84c81103a3e895925d94f3c1f244be89311a122a9`.
- Focused private replay/streaming/queue tests: 15 passed; Ruff passes.
- Public runtime code, frozen policy and motion permissions were not changed.
- Licensed sensor assets and private worker code remain outside the public repo.
