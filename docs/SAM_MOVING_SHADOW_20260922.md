# SAM Large During a Policy-Only Approach

## Protocol

Completed private run: `sam-live-shadow-approach-20260922-r2`.
One ordinary seed-1 radio start, 768 frozen Behavior-Skill approach actions,
25 normal captures and 28 additional dense RGB-D captures in the predeclared
384..512 window. Instruction: `Move to the radio receiver on the table.`
No GPT, training, classical intervention, task-completion claim or new contact
authority. Existing strict gates remain unchanged.

SAM 2.1 Large and depth partitioning run synchronously after existing grounding
on each normal capture. A small optional observer receives a deep copy of the
capture record and returns nothing to the policy. It writes private artifacts;
it does not change policy prompts, RGB, proprioception, action chunks or reset
semantics. Synchronous execution can change wall-clock timing, so this is not
a claim of zero operational interference. Dense intermediate captures invoke
neither grounding nor SAM.

The public callback defaults to disabled and is restricted to the isolated
policy-only acquisition. Private code owns the SAM worker, bounded lifetime,
23,552 MiB sampled-memory stop threshold, lineage checks and artifact logging.

## Results

- All 768 policy actions completed; no classical actions or GPT calls.
- All 25 shadow captures completed: 52 masks/partitions, including 13 accepted
  radio masks at actions 352 through 736, every 32 actions.
- Peak sampled GPU allocation: 21,957 MiB (21.44 GiB), with 2,607 MiB remaining
  against the device's reported capacity. Workers all exited afterward.
- Warm SAM-plus-partition worker time: 82-147 ms.
- Warm observation age at shadow return: 0.959-1.895 s; all 24 warm captures
  meet the predeclared 2 s limit. Cold shadow return age: 2.419 s.

Unlike the stationary preflight, this hook runs **before** policy inference.
Its return-age metric therefore excludes subsequent policy inference and
artifact writing; it must not be described as observation-to-action latency.
The first policy call still needs warmup. Neither this timing result nor the
retained scene being paused during inference bypasses stale-decision gates.

Video inspection shows turning toward the table and reaching toward the radio.
This was an approach-only instruction, not a turning-on-radio success trial.
The final capture has no accepted radio detection despite the radio remaining
visible in the video. Detector identity/dropouts remain unresolved; geometric
partitioning cannot repair them.

## Comparison and Remaining Bottleneck

The earlier `single4090-dense-acquisition-20260922-r1` used the same seed,
instruction and action budget. Policy exposure wall time is 267.64 s now versus
261.88 s before (about 2.2% longer). However, head RGB and policy actions differ
from the first decision. This is **not a controlled causal overhead estimate**
or proof that the callback preserves trajectories across independent resets.

Within the dense window, capture-gap median is 1.623 s versus 1.618 s before.
Four of 32 gaps exceed 2 s in each run; maximum gap grows from 2.900 s to 3.270 s.
The gaps at synchronous model boundaries remain. Fast SAM inference does not
solve capture scheduling or qualify moving localization.

## Integration Failure and Fix

Attempt r1 stopped at action 320 because a detector gripper box ended at
y=720.0366 for a 720-pixel image. The SAM adapter previously rejected any
out-of-bounds box. The general adapter now intersects finite, positive-area
boxes with image bounds, retaining both raw and used coordinates. Entirely
outside, degenerate and nonfinite boxes still fail. Two prompts were clipped
in r2. No detector, policy or segmentation thresholds were tuned for this retry.
The aborted run is retained rather than counted as a completed acquisition.

## Offline Checks

All 52 saved masks and label arrays passed content-hash and source RGB/depth/stamp
checks. CPU recomputation exactly reproduced every partition and its summary,
preserving every valid masked pixel. Panels at actions 384, 416 and 512 were
visually inspected. At action 512, the 2,366 valid pixels split into 42 patches:
the main body-dominated patch contains 1,892 pixels with median optical z 1.645 m;
a separate 171-pixel deeper patch has median z 2.149 m. This supports separation
of the handle-gap region, not automatic assignment of semantic membership.
Small fragments and detector identity failures remain; no patch is selected for
control merely because it is largest or nearest.

All 1,079 public tests and 96 focused private tests pass; Ruff passes. Both
attempts are fully backed up locally, with clean checksum-rsync comparisons.
The full successful run is approximately 397 MiB on the source host. GPU workers
were reaped, allocation returned to zero, and the instance was left running.

## Next Decision

Retain SAM Large plus depth patches as a practical shadow representation;
another segmentation-model search is not the next useful step. Separate native
capture scheduling from synchronous model work, retaining immutable source
timestamps and bounded queues, then recheck capture gaps and localization.
Continue to abstain on ambiguous part/patch associations. Do not enable
classical/contact motion solely because co-residency and shadow latency pass.

The successful owner receipt SHA256 is
`335298b4911b93d40d9fe559d982b43177f6d528f2409daaf7c1fc7b7726bda1`;
native receipt SHA256 is
`8182abcd821692852f25ef6d6564381b20dc68b3c5a10122c4630b4933865376`.
