# Matched Target-Directed Handoff

## Predeclared Protocol

Following the single successful exploratory transit, the user requested
continuation into the proposed matched short policy-handoff experiment.
One A/B pair is authorized here, not unrestricted motion or a benchmark result.
Clearance remains **unknown**. Strict default gates are unchanged.

Both conditions use the ordinary radio public-test instance 301, seed 0, the
same pinned multitask Behavior-Skill checkpoint and native 23D interface, and
the instruction `Move to the radio receiver on the table.` No GPT calls,
training, simulator poses, task-specific checkpoint selection or oracle input.

| Phase | A: zero-base control | B: target-directed intervention |
| --- | --- | --- |
| Acquisition | 768 policy actions, 32-action prefixes | Same |
| Pre-hold | Experimental stopping, at most 60 actions | Same |
| Intervention | 80 zero-base holds, fixed arm/trunk/gripper targets | Up to 80 commands at 0.03 m/s; 8 cm command/path driving bound, 10 cm measured hard-abort bound |
| Final hold | Experimental stopping, at most 60 actions | Same |
| Policy handoff | Fresh reset, 384 actions in 32-action prefixes | Same |

The same sensing, target validation, joint drift, speed, timeout and cleanup
checks apply to both interventions. Failed acquisition, target tracking,
stopping or feedback completeness prevents handoff. Failed runs are retained;
there are no automatic retries. The outer launcher stops the pair on an
operational failure rather than silently continuing.

Both policy phases retain their own action/chunk counts. Full exposure means
1,152 policy actions per condition, including acquisition. Classical action
counts and total robot duration are recorded separately; early stop or braking
can make them differ. A censored 384-action phase is not a completed pair.

The pinned backend has no action queue or temporal ensemble. Acquisition ends
at a complete chunk boundary; the post-handoff reset acknowledgement must match
the fresh observation stamp. Policy noise is indexed relative to that reset,
not by absolute native sequence, in both conditions. No inference is in flight
during the intervention. The same backend remains loaded throughout the pair.

## Interpretation

Primary question: does the frozen policy exhibit obvious disruption after this
small intervention, compared with an otherwise matched zero-base control?
Inspect the first policy actions, target visibility, visible motion toward or
away from the radio, and fresh sensor-derived target-distance proxies. Action
commands are not measured robot motion, and changing visible surfaces are not
ground-truth target displacement.

Check actual acquisition trace differences rather than assuming two seeded
resets are identical. One pair cannot establish a reliable causal improvement,
generality, task success, navigation clearance, or accurate long-range control.
Task scoring is out-of-band after the episode and unavailable to control.
The instruction is approach-only, not a request to activate the radio. A then B
is a fixed, nonrandomized order; shared runtime/model warmup can affect latency.
Latency is therefore descriptive, not a controlled policy-speed comparison.

## Native Results

The single pair completed without aborts or censored exposure. Each condition
executed 768 acquisition policy actions, six pre-holds, 80 intervention/control
actions, six final holds, and 384 fresh-reset policy actions: **1,152 policy and
92 classical actions**, or 1,244 native actions total. Both experimental stop
checks passed; both policy resets used fresh native sequence 860.

| Measurement | A: zero-base control | B: exploratory transit |
| --- | ---: | ---: |
| Classical commanded translation integral | 0 cm | 8.00 cm |
| Estimated classical path including holds | 0.570 cm | 6.182 cm |
| Handoff horizontal target-surface distance | 1.067 m | 1.223 m |
| After 32 policy actions | 1.065 m | 1.211 m |
| After 96 policy actions | 0.993 m | No accepted detection |
| After 384 policy actions | 0.693 m | 0.650 m |
| Closest EEF-to-surface distance at handoff | 0.454 m | 0.596 m |
| Closest EEF-to-surface distance at end | 0.325 m | 0.373 m |
| Accepted target at post-policy boundaries | 10/13 | 12/13 |
| Post-policy wall time | 220.9 s | 227.0 s |
| Native radio success, out-of-band | False | False |

Distances are sensor-derived visible-surface proxies, not object truth or button
locations. The missing detection is not evidence that the object disappeared.
Inspection of B's handoff and final head images shows the radio on the table
and subsequent approach with the right arm raised; it does not establish contact.

Neither condition produced an immediate strong base retreat: in the first 32
policy actions neither had a target-directed command projection below -0.01 m/s.
Mean XY command norms were 0.000833 m/s (A) and 0.000988 m/s (B). These describe
commands, not measured motion or correctness of the entire robot.

**Acquisition diverged before intervention despite the same seed.** Initial
proprioception was identical, but acquisition action arrays had a maximum
absolute difference of 0.4124 and RMS difference of 0.0763. These aggregate
differences mix native units and are descriptive, not calibrated error metrics.
B began the post-handoff phase about 15.6 cm farther from the observed surface.
Its slightly closer ending and larger distance reduction therefore do **not**
prove a benefit from the intervention. A then B was also not randomized.

The supported finding is operational: both handoffs completed and the frozen
policy resumed approach without obvious immediate base reversal. Radio activation
was not requested, and neither run solved the task. Clearance remains unknown;
strict navigation and moving-localization qualification remain incomplete.

## Verification And Artifacts

- Full offline suite: **1,049 passed**, including 49 new matched-handoff tests.
- Ruff passed. Native runner/probe sources were frozen during the pair.
- Both conditions used the same checkpoint and protocol; no GPT/API calls.
- The entire pair was downloaded locally; checksum-mode rsync found no changes.
- Native, policy and grounding workers exited; the rental was left running.
- Raw images, videos and native assets remain private.

Private run ID: `matched-target-handoff-20260922-r1`.

| Artifact | SHA-256 |
| --- | --- |
| A receipt | `efed8b09b3fdc2e014d783b929101d87a053d8a7785589613c7a8ec4a6b6f9c2` |
| B receipt | `4480eaca36fd3030bc8a3c3dcc5be07efe9af1d8faa67874325b5433e4834fdf` |
| Offline analysis script | `488fa1073df6e66bbd1580308cf18f35cfa3748237c762e923847cf67ad7a9a0` |

## Next Decision

Before spending on a longer A/B comparison, diagnose acquisition reproducibility
and define how to account for differing handoff states. Do not promote this pair
to a causal benefit claim or silently expand the motion envelope. Strict stages
remain gated; this report does not authorize another native run.
