# Phase 14 Active Neural Duty

Date: 2026-09-25

## Result

Offline accounting of the frozen eight-run Phase 8 Behavior-Skill/SAM cohort now
measures learned-component duty on an actually active workload. It validates all
eight immutable run receipts and introduces no robot action, model call, or GPU
work.

| Measure | Result |
| --- | ---: |
| Runs | 8 |
| Native robot actions | 9,952 |
| Behavior-Skill actions | 9,216 |
| Classical intervention/control actions | 736 |
| Policy actuator-time fraction | 92.60% |
| Policy simulation time | 307.2 s |
| Policy DOF-time | 7,065.6 DOF-s |
| Policy inference calls | 288 |
| Policy inference time | 369.221 s |
| Policy inference / policy execution wall time | 12.43% |
| SAM invocations | 1,048 |
| Unique source-bound SAM artifacts | 1,048 |
| SAM results with a visible target | 960 |
| Unavailable/future SAM frame reads | 0 |
| SAM processing time | 210.966 s |
| SAM processing / worker-window time | 5.11% |
| SAM scheduling reduction versus every native boundary | 89.48% |

The 92.60% figure is actuator exposure, not GPU utilization. It means the frozen
policy supplied 9,216 of 9,952 native action vectors through its full 23-DoF
interface. Policy and SAM time intervals can overlap and therefore must not be
added into a utilization percentage.

Across runs, policy cold starts took 39.73--42.02 seconds. After initialization,
per-chunk inference medians were 156.6--160.2 ms and per-run p95 values were
168.1--174.6 ms. Cold starts accounted for 324.983 of the 369.221 measured policy
inference seconds. This makes persistent policy residency a materially more useful
optimization than reducing the already-short warm chunk latency.

SAM worker processing medians were 188.2--192.6 ms and per-run p95 values were
264.6--286.8 ms. Observation-to-ready medians were 378.8--388.0 ms and p95 values
were 476.6--493.9 ms. Sparse scheduling produced one source-bound artifact per
invocation while avoiding approximately nine of every ten possible
action-boundary invocations.

## Integrity Fix

The first analyzer attempt incorrectly treated `frame_accesses` as a fixed
sentinel. The receipts actually journal causal indices: every requested frame must
be strictly below the number of arrived frames. The analyzer now enforces
`requested < arrived`, rejects missing or malformed access evidence, and reports
the frame-read and unavailable-read counts. Five focused tests cover valid,
unarrived, future, missing, and malformed evidence. All 1,048 retained accesses
were legal.

## What This Does Not Establish

- All eight source runs failed the evaluation-only task-success condition. These
  measurements cannot show how much compute can be removed while preserving task
  competence.
- The cohort retained no explicit SAM internal cache-hit telemetry. Unique output
  artifacts prove fresh publications, not absence of representation reuse.
- GLM, GraspGen-X, and GPT were not scheduled in this workload. Their zero calls
  are not cache-suppression savings.
- No time-aligned device-power samples were retained, so energy remains unknown.
- `motion_qualified=false` and `clearance=unknown` remain unchanged.

## Decision

Keep Behavior-Skill resident during any later continuous rollout, and preserve the
existing sparse SAM schedule rather than running segmentation at every native
action boundary. Do not claim an efficiency/competence frontier until a workload
with at least one successful task outcome is available. Add cache-hit counters and
time-aligned power telemetry prospectively to that workload; do not reconstruct
either from these receipts.

## Evidence

- aggregate result:
  `ad1f5950b150001a4b3503bade6e049223753a0e862e3952563e1cb4f604921e`;
- analyzer:
  `db90c9781e9f68c273f7217ea60d767c38bd452db4863bce21e35da87ab74a7e`;
- focused analyzer test:
  `f2243b43f2587e446b4e5a5669c1a75d8035b40e2c77b6971899142392349e31`;
- frozen Phase 8 protocol:
  `5b16733fb1f5968da4328df503ec032e4cf34d7356416361257234f68dc572e0`;
- frozen Phase 8 aggregate result:
  `d5bbefec299d1dcc652d4665002d102e0183fd5819be44f12a57615e3fca7d43`.
